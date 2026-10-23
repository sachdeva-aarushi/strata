"""Cluster Synergy Engine and Batch Aggregation.

Identifies compatible material lots across facilities in an industrial cluster,
computes batch aggregation proposals with weighted composite attributes and quality
variance warnings, calculates indicative logistics metrics, and generates cluster
circularity indicators.

Pure calculations only: NEVER alters underlying physical MaterialLot database records.
"""

from datetime import datetime, timezone
import itertools
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple
import uuid

from sqlalchemy.orm import Session

from strata.core.errors import ResourceNotFoundError
from strata.domain.marketplace.models import BuyerRequirement, Listing
from strata.domain.marketplace.repository import MarketplaceRepository
from strata.domain.marketplace.schemas import (
    AggregationProposal,
    ClusterSummary,
    LogisticsEstimate,
    LotContribution,
)
from strata.domain.materials.models import Facility, MaterialLot
from strata.domain.materials.taxonomy import get_material_type
from strata.schemas.materials import MaterialLotRead


def _normalise(value: str) -> str:
    return value.strip().lower()


class ClusterSynergyEngine:
    """Computes cluster synergies, batch aggregations, and logistics metrics."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = MarketplaceRepository(db)

    # -----------------------------------------------------------------------
    # 1. Compatible Lot Discovery
    # -----------------------------------------------------------------------

    def find_compatible_lots(
        self,
        requirement_id: str,
        cluster_id: str,
    ) -> List[MaterialLotRead]:
        """Queries active listings/lots within a cluster compatible with the buyer requirement.

        Filters:
          * Belongs to the specified cluster (or unassigned in open cluster queries)
          * Excludes lots from the buyer's own organization
          * Material category matches requirement.material_category (case-insensitive)
          * Measurement unit matches requirement.unit (case-insensitive)
          * Lot does not contain any prohibited conditions specified by the buyer
        """
        requirement = self.repository.get_requirement(requirement_id)
        if not requirement:
            raise ResourceNotFoundError(
                f"Buyer requirement '{requirement_id}' not found.",
                details={"requirement_id": requirement_id},
            )

        cluster_rows = self.repository.get_cluster_listings(cluster_id)
        compatible_lots: List[MaterialLotRead] = []

        for listing, lot, facility in cluster_rows:
            # Multi-tenant boundary: buyer cannot aggregate from its own inventory
            if lot.org_id == requirement.organization_id:
                continue

            taxonomy = get_material_type(lot.material_type)
            if not taxonomy:
                continue

            # Category filter
            if _normalise(taxonomy.category) != _normalise(requirement.material_category):
                continue

            # Unit filter
            if _normalise(listing.unit) != _normalise(requirement.unit):
                continue

            # Prohibited conditions filter
            if self._has_prohibited_condition(lot, taxonomy, requirement.prohibited_conditions):
                continue

            compatible_lots.append(MaterialLotRead.model_validate(lot))

        return compatible_lots

    def _has_prohibited_condition(
        self,
        lot: MaterialLot,
        taxonomy: Any,
        prohibited_conditions: List[str],
    ) -> bool:
        """Determines if a material lot violates any buyer prohibited conditions."""
        if not prohibited_conditions:
            return False

        declared = lot.declared_attributes or {}

        for cond in prohibited_conditions:
            c_norm = cond.strip().lower()
            if not c_norm:
                continue

            # Check hazardous gate
            if c_norm == "hazardous" and getattr(taxonomy, "is_hazardous", False):
                return True

            # Direct attribute key check with truthy value
            if c_norm in declared:
                val = declared[c_norm]
                if isinstance(val, bool) and val:
                    return True
                if isinstance(val, (int, float)) and val > 0:
                    return True
                if isinstance(val, str) and val.strip().lower() not in {"none", "false", "0", "no"}:
                    return True

            # Textual notes or contamination inspection
            for k in ("contamination", "contaminants", "notes", "description", "physical_form"):
                if k in declared and c_norm in str(declared[k]).lower():
                    return True

            # Numeric condition evaluation (e.g. "moisture_gt_15" or "moisture > 15")
            if "moisture" in c_norm and ("gt" in c_norm or ">" in c_norm):
                nums = re.findall(r"\d+(?:\.\d+)?", c_norm)
                if nums:
                    threshold = float(nums[0])
                    moisture_val = declared.get("moisture_pct") or declared.get("moisture")
                    if moisture_val is not None:
                        try:
                            if float(moisture_val) > threshold:
                                return True
                        except (ValueError, TypeError):
                            pass

        return False

    # -----------------------------------------------------------------------
    # 2. Batch Aggregation Proposal Generation
    # -----------------------------------------------------------------------

    def generate_aggregation_proposals(
        self,
        requirement_id: str,
        cluster_id: str,
        max_lots_per_batch: int = 5,
    ) -> List[AggregationProposal]:
        """Identifies combinations of compatible lots meeting buyer volume thresholds.

        Computes weighted composite material attributes and flags quality variance
        warnings without making physical database mutations.
        """
        requirement = self.repository.get_requirement(requirement_id)
        if not requirement:
            raise ResourceNotFoundError(
                f"Buyer requirement '{requirement_id}' not found.",
                details={"requirement_id": requirement_id},
            )

        compatible_lots = self.find_compatible_lots(requirement_id, cluster_id)
        if not compatible_lots:
            return []

        # Map lot_id to its active listing ID
        cluster_rows = self.repository.get_cluster_listings(cluster_id)
        listing_map = {lot.lot_id: listing.id for listing, lot, fac in cluster_rows}

        contributions: List[LotContribution] = [
            LotContribution(
                lot_id=l.lot_id,
                listing_id=listing_map.get(l.lot_id),
                organization_id=l.org_id,
                facility_id=l.facility_id,
                quantity=l.quantity,
                unit=l.unit,
                material_type=l.material_type,
                material_category=requirement.material_category,
                declared_attributes=l.declared_attributes or {},
            )
            for l in compatible_lots
        ]

        proposals: List[AggregationProposal] = []
        max_k = min(max_lots_per_batch, len(contributions))

        # Evaluate candidate combinations from size 1 up to max_k
        for k in range(1, max_k + 1):
            for combo in itertools.combinations(contributions, k):
                total_qty = sum(c.quantity for c in combo)

                # Check minimum volume threshold
                if total_qty < requirement.min_quantity:
                    continue

                # Respect upper limit if specified (allow up to 25% surplus over max_quantity)
                if requirement.max_quantity is not None and total_qty > (requirement.max_quantity * 1.25):
                    continue

                # Calculate composite attributes & quality variance warnings
                composite_attrs, warnings = self._compute_composite_attributes_and_warnings(combo, total_qty)

                proposals.append(
                    AggregationProposal(
                        requirement_id=requirement.id,
                        cluster_id=cluster_id,
                        lots=list(combo),
                        total_quantity=round(total_qty, 2),
                        unit=requirement.unit,
                        target_min_quantity=requirement.min_quantity,
                        composite_attributes=composite_attrs,
                        quality_variance_warnings=warnings,
                    )
                )

        # Sort proposals: fewest variance warnings first, then closest volume match to min_quantity
        proposals.sort(
            key=lambda p: (
                len(p.quality_variance_warnings),
                abs(p.total_quantity - requirement.min_quantity),
                len(p.lots),
            )
        )

        return proposals[:15]

    def _compute_composite_attributes_and_warnings(
        self,
        combo: Tuple[LotContribution, ...],
        total_quantity: float,
    ) -> Tuple[Dict[str, Any], List[str]]:
        """Calculates weighted averages for numeric properties and detects quality variances."""
        composite: Dict[str, Any] = {}
        warnings: List[str] = []

        # 1. Calculate weighted averages of scalar numeric attributes
        all_numeric_keys: Set[str] = set()
        for c in combo:
            for k, v in c.declared_attributes.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    all_numeric_keys.add(k)

        for key in sorted(all_numeric_keys):
            applicable_lots = [c for c in combo if key in c.declared_attributes and isinstance(c.declared_attributes[key], (int, float))]
            if applicable_lots:
                weighted_sum = sum(c.quantity * float(c.declared_attributes[key]) for c in applicable_lots)
                applicable_qty = sum(c.quantity for c in applicable_lots)
                mean_val = weighted_sum / applicable_qty
                composite[key] = round(mean_val, 2)

                # Check variance threshold
                values = [float(c.declared_attributes[key]) for c in applicable_lots]
                spread = max(values) - min(values)

                # Flag variance if spread exceeds 5% for moisture, or 10% for other properties
                threshold = 5.0 if "moisture" in key.lower() else 10.0
                if spread > threshold:
                    warnings.append(
                        f"Quality variance warning: '{key}' varies by {spread:.1f} across lots in this batch (min: {min(values):.1f}, max: {max(values):.1f})."
                    )

        # 2. Composite fiber blend breakdown
        fiber_keys: Set[str] = set()
        for c in combo:
            blend = c.declared_attributes.get("fibre_blend")
            if isinstance(blend, dict):
                for f_name in blend.keys():
                    fiber_keys.add(f_name)

        if fiber_keys:
            composite_blend: Dict[str, float] = {}
            for fiber in sorted(fiber_keys):
                fiber_weighted = sum(
                    c.quantity * float(c.declared_attributes.get("fibre_blend", {}).get(fiber, 0))
                    for c in combo
                )
                mean_fiber_pct = fiber_weighted / total_quantity
                composite_blend[fiber] = round(mean_fiber_pct, 2)

                # Fiber spread check
                fiber_vals = [
                    float(c.declared_attributes.get("fibre_blend", {}).get(fiber, 0))
                    for c in combo
                ]
                f_spread = max(fiber_vals) - min(fiber_vals)
                if f_spread > 15.0:
                    warnings.append(
                        f"Composition variance: '{fiber}' proportion differs by {f_spread:.1f}% across lots."
                    )
            composite["fibre_blend"] = composite_blend

        # 3. Physical form consistency
        physical_forms = {
            c.declared_attributes.get("physical_form")
            for c in combo
            if c.declared_attributes.get("physical_form")
        }
        if len(physical_forms) > 1:
            forms_str = ", ".join(sorted(str(f) for f in physical_forms))
            warnings.append(
                f"Physical form divergence: batch contains mixed forms ({forms_str}). Pre-processing may be required."
            )

        # 4. Multi-facility collection complexity
        unique_facilities = {c.facility_id for c in combo}
        if len(unique_facilities) >= 3:
            warnings.append(
                f"Logistics notice: batch requires pickup from {len(unique_facilities)} distinct facility locations."
            )

        return composite, warnings

    # -----------------------------------------------------------------------
    # 3. Indicative Logistics and Emissions Calculations
    # -----------------------------------------------------------------------

    def calculate_indicative_logistics(
        self,
        lot_ids: List[str],
        destination_facility_id: str,
        rate_per_km_tonne: float = 12.5,
    ) -> LogisticsEstimate:
        """Calculates route distance, transportation tariff in INR, and freight CO2 emissions.

        Uses the standard milk-run logistics consolidation model:
        - Collection legs between N pickup facilities: (N - 1) * 30.0 km
        - Consolidated delivery trunk haul to destination: 45.0 km
        - Heavy road freight emissions factor: 0.105 kg CO2e per tonne-km
        """
        lots_dict = self.repository.get_lots_by_ids(lot_ids)
        missing_ids = [lid for lid in lot_ids if lid not in lots_dict]
        if missing_ids:
            raise ResourceNotFoundError(
                f"Material lot(s) not found: {', '.join(missing_ids)}",
                details={"missing_lot_ids": missing_ids},
            )

        # Calculate total mass in metric tonnes
        total_tonnage = 0.0
        for lid in lot_ids:
            lot = lots_dict[lid]
            unit_norm = _normalise(lot.unit)
            if unit_norm in ("tonne", "ton", "t", "metric_ton"):
                tonnes = lot.quantity
            elif unit_norm in ("kg", "kilogram"):
                tonnes = lot.quantity / 1000.0
            elif unit_norm in ("g", "gram"):
                tonnes = lot.quantity / 1_000_000.0
            else:
                tonnes = lot.quantity / 1000.0
            total_tonnage += tonnes

        total_tonnage = round(total_tonnage, 3)

        # Multi-stop milk-run distance model
        pickup_facility_ids = list({lots_dict[lid].facility_id for lid in lot_ids})
        num_facilities = len(pickup_facility_ids)

        # Collection inter-facility legs + final trunk haul
        total_distance_km = round((num_facilities - 1) * 30.0 + 45.0, 1)

        # Freight calculations
        estimated_cost_inr = round(total_tonnage * total_distance_km * rate_per_km_tonne, 2)
        emissions_kg_co2e = round(total_tonnage * total_distance_km * 0.105, 2)

        return LogisticsEstimate(
            lot_ids=lot_ids,
            destination_facility_id=destination_facility_id,
            total_tonnage=total_tonnage,
            total_distance_km=total_distance_km,
            rate_per_km_tonne=rate_per_km_tonne,
            estimated_transport_cost_inr=estimated_cost_inr,
            estimated_transport_emissions_kg_co2e=emissions_kg_co2e,
            currency="INR",
            methodology="indicative_milk_run_v1",
        )

    # -----------------------------------------------------------------------
    # 4. Cluster Circularity Indicators
    # -----------------------------------------------------------------------

    def get_cluster_indicators(self, cluster_id: str) -> ClusterSummary:
        """Aggregates cluster metrics: total tonnage, material breakdown, and aggregation opportunities."""
        cluster_rows = self.repository.get_cluster_listings(cluster_id)
        active_listings_count = len(cluster_rows)

        total_tonnage = 0.0
        tonnage_by_category: Dict[str, float] = {}
        category_lot_counts: Dict[str, int] = {}

        for listing, lot, facility in cluster_rows:
            taxonomy = get_material_type(lot.material_type)
            cat = taxonomy.category if taxonomy else "other"

            u = _normalise(listing.unit)
            q = listing.available_quantity
            t = q if u in ("tonne", "ton", "t") else (q / 1000.0)

            total_tonnage += t
            tonnage_by_category[cat] = round(tonnage_by_category.get(cat, 0.0) + t, 2)
            category_lot_counts[cat] = category_lot_counts.get(cat, 0) + 1

        total_tonnage = round(total_tonnage, 2)

        # Count categories with multiple lots representing viable aggregation opportunities
        aggregation_opportunities = sum(1 for count in category_lot_counts.values() if count >= 2)

        return ClusterSummary(
            cluster_id=cluster_id,
            active_listings_count=active_listings_count,
            total_available_tonnage=total_tonnage,
            tonnage_by_category=tonnage_by_category,
            potential_aggregation_opportunities=aggregation_opportunities,
        )
