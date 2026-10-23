"""Municipal & City Intelligence Engine.

Aggregates material flows, circularity indicators, and processing capacity gap analyses
for city planners and regional municipal authorities.

Strict Privacy & Confidentiality Guarantees:
  * NEVER exposes private facility names, facility IDs, or organization identities.
  * NEVER exposes individual lot records, transaction IDs, or pricing details.
  * Enforces cohort threshold aggregation: at least 3 distinct facilities must operate
    in a zone to disclose zone-level material breakdowns; otherwise metrics are masked.
  * Explicitly labels all data provenance (real_verified, curated_public, synthetic_demo).
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from strata.domain.marketplace.models import Listing
from strata.domain.marketplace.schemas import ListingStatus
from strata.domain.materials.models import Facility, MaterialLot
from strata.domain.materials.taxonomy import get_material_type
from strata.schemas.municipal import (
    CapacityGapReport,
    DataProvenanceLabel,
    LifecycleFlowBreakdown,
    MunicipalFlowReport,
    MunicipalGeographicSummary,
    ZoneGapIndicator,
    ZoneGeographicIndicator,
)

# Minimum distinct facilities in a cohort to disclose zone-level breakdowns
MIN_COHORT_FACILITY_COUNT = 3


def _normalise(val: Optional[str]) -> str:
    return val.strip().lower() if val else ""


def _to_tonnes(quantity: float, unit: str) -> float:
    """Converts common material measurement units to metric tonnes."""
    u = _normalise(unit)
    if u in ("tonne", "ton", "t", "metric_ton"):
        return quantity
    elif u in ("kg", "kilogram"):
        return quantity / 1000.0
    elif u in ("g", "gram"):
        return quantity / 1_000_000.0
    return quantity / 1000.0


class MunicipalIntelligenceEngine:
    """Computes privacy-preserving municipal circularity intelligence and material flow metrics."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -----------------------------------------------------------------------
    # Helper Queries
    # -----------------------------------------------------------------------

    def _get_facilities_in_city(self, city_id: str, zone_id: Optional[str] = None) -> List[Facility]:
        """Retrieves facilities belonging to the requested city and optional zone."""
        stmt = select(Facility).where(Facility.city_id == city_id)
        if zone_id is not None:
            stmt = stmt.where(Facility.zone_id == zone_id)
        return list(self.db.execute(stmt).scalars().all())

    def _get_lots_for_facilities(self, facility_ids: List[str]) -> List[MaterialLot]:
        """Retrieves material lots originating from the specified facility IDs."""
        if not facility_ids:
            return []
        stmt = select(MaterialLot).where(MaterialLot.facility_id.in_(facility_ids))
        return list(self.db.execute(stmt).scalars().all())

    def _determine_provenance(self, lots: List[MaterialLot]) -> DataProvenanceLabel:
        """Evaluates data provenance classification based on constituent lots."""
        if not lots:
            return DataProvenanceLabel.REAL_VERIFIED
        labels = {lot.provenance_label for lot in lots if lot.provenance_label}
        if "synthetic_demo" in labels:
            return DataProvenanceLabel.SYNTHETIC_DEMO
        if "curated_public" in labels:
            return DataProvenanceLabel.CURATED_PUBLIC
        return DataProvenanceLabel.REAL_VERIFIED

    # -----------------------------------------------------------------------
    # 1. Aggregate Material Flows
    # -----------------------------------------------------------------------

    def get_aggregate_material_flows(
        self,
        city_id: str,
        zone_id: Optional[str] = None,
        material_category: Optional[str] = None,
    ) -> MunicipalFlowReport:
        """Aggregates material quantities across circularity lifecycle stages.

        Enforces cohort suppression when distinct facilities in the requested scope < 3.
        """
        facilities = self._get_facilities_in_city(city_id=city_id, zone_id=zone_id)
        distinct_facilities_count = len(facilities)

        # Check cohort privacy threshold
        if distinct_facilities_count < MIN_COHORT_FACILITY_COUNT:
            reason = (
                f"Cohort suppression active: fewer than {MIN_COHORT_FACILITY_COUNT} distinct reporting "
                f"facilities in this {'zone' if zone_id else 'city'} (found {distinct_facilities_count}). "
                "Metrics masked to prevent commercial re-identification."
            )
            return MunicipalFlowReport(
                city_id=city_id,
                zone_id=zone_id,
                material_category=material_category,
                facility_cohort_count=None,
                cohort_suppressed=True,
                suppression_reason=reason,
                flows=None,
                provenance=DataProvenanceLabel.REAL_VERIFIED,
            )

        facility_ids = [f.facility_id for f in facilities]
        lots = self._get_lots_for_facilities(facility_ids)

        # Filter by material category if requested
        if material_category:
            target_cat = _normalise(material_category)
            filtered_lots = []
            for lot in lots:
                taxonomy = get_material_type(lot.material_type)
                cat = _normalise(taxonomy.category) if taxonomy else "other"
                if cat == target_cat:
                    filtered_lots.append(lot)
            lots = filtered_lots

        # Query active listings for these lots to determine "offered" volume
        lot_ids = [l.lot_id for l in lots]
        active_listings: Dict[str, float] = {}
        if lot_ids:
            listing_stmt = select(Listing).where(
                Listing.material_lot_id.in_(lot_ids),
                Listing.status == ListingStatus.ACTIVE,
            )
            for row in self.db.execute(listing_stmt).scalars().all():
                active_listings[row.material_lot_id] = _to_tonnes(row.available_quantity, row.unit)

        generated_tonnage = 0.0
        offered_tonnage = 0.0
        shipped_tonnage = 0.0
        accepted_tonnage = 0.0
        processed_tonnage = 0.0
        verified_recovered_tonnage = 0.0
        by_category: Dict[str, float] = defaultdict(float)

        for lot in lots:
            t = _to_tonnes(lot.quantity, lot.unit)
            generated_tonnage += t

            # Category mapping
            tax = get_material_type(lot.material_type)
            cat_name = tax.category if tax else "other"
            by_category[cat_name] += t

            # Lifecycle status evaluation
            st = _normalise(lot.status)
            if lot.lot_id in active_listings:
                offered_tonnage += active_listings[lot.lot_id]
            elif st == "listed":
                offered_tonnage += t

            if st in ("shipped", "in_transit", "dispatched"):
                shipped_tonnage += t
            elif st in ("accepted", "received"):
                accepted_tonnage += t
            elif st in ("processed", "utilized", "converted"):
                processed_tonnage += t
            elif st in ("verified_recovered", "recovered", "recycled"):
                verified_recovered_tonnage += t

            # Also check declared attributes for recovery flags
            attrs = lot.declared_attributes or {}
            if attrs.get("verified_recovered") is True and st not in ("verified_recovered", "recovered", "recycled"):
                verified_recovered_tonnage += t

        breakdown = LifecycleFlowBreakdown(
            generated_tonnage=round(generated_tonnage, 2),
            offered_tonnage=round(offered_tonnage, 2),
            shipped_tonnage=round(shipped_tonnage, 2),
            accepted_tonnage=round(accepted_tonnage, 2),
            processed_tonnage=round(processed_tonnage, 2),
            verified_recovered_tonnage=round(verified_recovered_tonnage, 2),
            by_material_category={k: round(v, 2) for k, v in sorted(by_category.items())},
        )

        provenance = self._determine_provenance(lots)

        return MunicipalFlowReport(
            city_id=city_id,
            zone_id=zone_id,
            material_category=material_category,
            facility_cohort_count=distinct_facilities_count,
            cohort_suppressed=False,
            suppression_reason=None,
            flows=breakdown,
            provenance=provenance,
        )

    # -----------------------------------------------------------------------
    # 2. Capacity Gap Analysis
    # -----------------------------------------------------------------------

    def get_capacity_gap_analysis(self, city_id: str) -> CapacityGapReport:
        """Compares byproduct generation against aggregate verified processing capacity per zone."""
        all_facilities = self._get_facilities_in_city(city_id=city_id)
        all_lots = self._get_lots_for_facilities([f.facility_id for f in all_facilities])

        # Group facilities and lots by zone
        facilities_by_zone: Dict[str, List[Facility]] = defaultdict(list)
        for f in all_facilities:
            z_id = f.zone_id or "unassigned"
            facilities_by_zone[z_id].append(f)

        lots_by_facility: Dict[str, List[MaterialLot]] = defaultdict(list)
        for lot in all_lots:
            lots_by_facility[lot.facility_id].append(lot)

        total_city_generation = 0.0
        total_city_capacity = 0.0
        zone_indicators: List[ZoneGapIndicator] = []

        for z_id in sorted(facilities_by_zone.keys()):
            zone_facs = facilities_by_zone[z_id]
            fac_count = len(zone_facs)

            # Calculate zone generation and capacity
            zone_gen = 0.0
            zone_cat_gen: Dict[str, float] = defaultdict(float)
            for f in zone_facs:
                f_lots = lots_by_facility.get(f.facility_id, [])
                for lot in f_lots:
                    t = _to_tonnes(lot.quantity, lot.unit)
                    zone_gen += t
                    tax = get_material_type(lot.material_type)
                    cat = tax.category if tax else "other"
                    zone_cat_gen[cat] += t

            zone_cap = sum(float(f.processing_capacity_tpa or 0.0) for f in zone_facs)

            total_city_generation += zone_gen
            total_city_capacity += zone_cap

            # Apply cohort suppression to zone-level reporting if < 3 facilities
            if fac_count < MIN_COHORT_FACILITY_COUNT:
                zone_indicators.append(
                    ZoneGapIndicator(
                        zone_id=z_id,
                        cohort_suppressed=True,
                        facility_count=None,
                        generation_tonnage=None,
                        processing_capacity_tonnage=None,
                        net_balance_tonnage=None,
                        gap_status="SUPPRESSED",
                        top_deficit_categories=[],
                    )
                )
            else:
                net_balance = round(zone_cap - zone_gen, 2)

                # Classify zone status
                if net_balance < -0.05 * max(zone_gen, 1.0):
                    status = "DEFICIT_HOTSPOT"
                elif net_balance > 0.05 * max(zone_cap, 1.0):
                    status = "SURPLUS_CAPACITY"
                else:
                    status = "BALANCED"

                # Sort deficit categories by generation volume
                top_deficits = sorted(zone_cat_gen.keys(), key=lambda c: zone_cat_gen[c], reverse=True)[:3]

                zone_indicators.append(
                    ZoneGapIndicator(
                        zone_id=z_id,
                        cohort_suppressed=False,
                        facility_count=fac_count,
                        generation_tonnage=round(zone_gen, 2),
                        processing_capacity_tonnage=round(zone_cap, 2),
                        net_balance_tonnage=net_balance,
                        gap_status=status,
                        top_deficit_categories=top_deficits,
                    )
                )

        net_city = round(total_city_capacity - total_city_generation, 2)
        if net_city < -0.05 * max(total_city_generation, 1.0):
            overall_status = "DEFICIT_HOTSPOT"
        elif net_city > 0.05 * max(total_city_capacity, 1.0):
            overall_status = "SURPLUS_CAPACITY"
        else:
            overall_status = "BALANCED"

        provenance = self._determine_provenance(all_lots)

        return CapacityGapReport(
            city_id=city_id,
            total_city_generation=round(total_city_generation, 2),
            total_city_capacity=round(total_city_capacity, 2),
            net_city_balance=net_city,
            overall_status=overall_status,
            zones=zone_indicators,
            provenance=provenance,
        )

    # -----------------------------------------------------------------------
    # 3. Geographic Indicators
    # -----------------------------------------------------------------------

    def get_geographic_indicators(self, city_id: str) -> MunicipalGeographicSummary:
        """Provides zone-level and city-wide material density indicators with cohort privacy masking."""
        all_facilities = self._get_facilities_in_city(city_id=city_id)
        all_lots = self._get_lots_for_facilities([f.facility_id for f in all_facilities])

        facilities_by_zone: Dict[str, List[Facility]] = defaultdict(list)
        for f in all_facilities:
            z_id = f.zone_id or "unassigned"
            facilities_by_zone[z_id].append(f)

        lots_by_facility: Dict[str, List[MaterialLot]] = defaultdict(list)
        for lot in all_lots:
            lots_by_facility[lot.facility_id].append(lot)

        total_city_tonnage = 0.0
        city_cat_tonnage: Dict[str, float] = defaultdict(float)
        zone_indicators: List[ZoneGeographicIndicator] = []

        for z_id in sorted(facilities_by_zone.keys()):
            zone_facs = facilities_by_zone[z_id]
            fac_count = len(zone_facs)

            zone_tonnage = 0.0
            zone_cat_tonnage: Dict[str, float] = defaultdict(float)

            for f in zone_facs:
                for lot in lots_by_facility.get(f.facility_id, []):
                    t = _to_tonnes(lot.quantity, lot.unit)
                    zone_tonnage += t
                    tax = get_material_type(lot.material_type)
                    cat = tax.category if tax else "other"
                    zone_cat_tonnage[cat] += t

            total_city_tonnage += zone_tonnage
            for cat, t_val in zone_cat_tonnage.items():
                city_cat_tonnage[cat] += t_val

            if fac_count < MIN_COHORT_FACILITY_COUNT:
                zone_indicators.append(
                    ZoneGeographicIndicator(
                        zone_id=z_id,
                        cohort_suppressed=True,
                        active_facility_count=None,
                        total_tonnage=None,
                        top_categories=[],
                        tonnage_by_category={},
                    )
                )
            else:
                sorted_cats = sorted(zone_cat_tonnage.keys(), key=lambda c: zone_cat_tonnage[c], reverse=True)
                zone_indicators.append(
                    ZoneGeographicIndicator(
                        zone_id=z_id,
                        cohort_suppressed=False,
                        active_facility_count=fac_count,
                        total_tonnage=round(zone_tonnage, 2),
                        top_categories=sorted_cats[:5],
                        tonnage_by_category={k: round(v, 2) for k, v in sorted(zone_cat_tonnage.items())},
                    )
                )

        provenance = self._determine_provenance(all_lots)

        return MunicipalGeographicSummary(
            city_id=city_id,
            total_active_zones=len(facilities_by_zone),
            total_city_facilities=len(all_facilities),
            total_city_tonnage=round(total_city_tonnage, 2),
            city_tonnage_by_category={k: round(v, 2) for k, v in sorted(city_cat_tonnage.items())},
            zones=zone_indicators,
            provenance=provenance,
        )
