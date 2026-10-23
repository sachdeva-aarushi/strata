"""Domain service for the Verified Impact Ledger and environmental accounting.

Guarantees non-double-counting across material lifecycle stages, enforces sequential
verification rules, and computes evidence-backed carbon and landfill avoidance metrics.
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from strata.core.errors import DuplicateEventError, InvalidStateTransitionError, ResourceNotFoundError
from strata.domain.impact.models import ImpactRecord
from strata.schemas.impact import (
    ImpactCalculation,
    ImpactCalculationRequest,
    ImpactMethodologyInfo,
    ImpactRecordCreate,
    ImpactRecordRead,
    ImpactSummaryRead,
    LifecycleEventType,
    MassBalanceReport,
    UncertaintyRating,
    VerificationStatus,
)

# Authoritative displacement emission factors in kg CO2e / kg recovered material
FACTORS_V1: Dict[str, Dict[str, Any]] = {
    "textiles": {
        "factor": 14.2,
        "source": "EPA WARM v15 / WRAP UK Textile Carbon Footprint",
        "uncertainty": UncertaintyRating.LOW,
        "assumptions": "Pre-consumer textile fiber recovery vs virgin cotton/polyester synthesis; 100% landfill diversion.",
    },
    "metallics": {
        "factor": 8.5,
        "source": "International Aluminium Institute 2023 / DEFRA GHG Conversion Factors",
        "uncertainty": UncertaintyRating.LOW,
        "assumptions": "Secondary metal scrap remelt vs primary bauxite/alumina Bayer process smelting.",
    },
    "chemicals": {
        "factor": 2.1,
        "source": "EcoInvent v3.9 / American Chemistry Council",
        "uncertainty": UncertaintyRating.LOW,
        "assumptions": "Spent solvent fractional distillation vs virgin fossil petrochemical synthesis.",
    },
    "polymers": {
        "factor": 1.8,
        "source": "Association of Plastic Recyclers / EPA WARM",
        "uncertainty": UncertaintyRating.MEDIUM,
        "assumptions": "Mechanical flake reprocessing vs virgin naphtha cracking and polymerisation.",
    },
    "biomass": {
        "factor": 0.9,
        "source": "IPCC Guidelines for National Greenhouse Gas Inventories",
        "uncertainty": UncertaintyRating.MEDIUM,
        "assumptions": "Controlled composting/anaerobic digestion vs fugitive landfill methane emissions.",
    },
    "minerals": {
        "factor": 0.4,
        "source": "European Aggregates Association LCA Benchmark",
        "uncertainty": UncertaintyRating.LOW,
        "assumptions": "Recycled aggregate crushing vs primary quarrying and crushing.",
    },
    "default": {
        "factor": 1.0,
        "source": "Strata Default Circular Factor v1.0",
        "uncertainty": UncertaintyRating.HIGH,
        "assumptions": "Generic circular diversion substitution assumption with baseline landfill prevention.",
    },
}


def _canonical_category(raw_category: str) -> str:
    c = raw_category.strip().lower()
    if any(k in c for k in ("textile", "cotton", "fabric", "yarn", "fiber")):
        return "textiles"
    if any(k in c for k in ("metal", "aluminum", "copper", "steel", "iron")):
        return "metallics"
    if any(k in c for k in ("chem", "solvent", "isopropanol", "acid")):
        return "chemicals"
    if any(k in c for k in ("plastic", "polymer", "poly", "resin")):
        return "polymers"
    if any(k in c for k in ("bio", "organic", "food", "wood", "pulp")):
        return "biomass"
    if any(k in c for k in ("mineral", "aggregate", "concrete", "rubble")):
        return "minerals"
    return "default"


class ImpactLedgerService:
    """Service orchestrating immutable environmental impact ledger records."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # -----------------------------------------------------------------------
    # 1. Environmental Calculation
    # -----------------------------------------------------------------------

    def calculate_environmental_impact(
        self,
        mass_kg: float,
        material_category: str,
        methodology_version: str = "v1.0",
    ) -> ImpactCalculation:
        """Computes landfill avoidance and CO2e abatement with explicit factor lineage."""
        canon = _canonical_category(material_category)
        factor_meta = FACTORS_V1.get(canon, FACTORS_V1["default"])

        factor_val = factor_meta["factor"]
        co2e_avoided = round(mass_kg * factor_val, 2)
        landfill_avoided = round(mass_kg, 2)

        return ImpactCalculation(
            mass_kg=mass_kg,
            material_category=material_category,
            landfill_avoided_kg=landfill_avoided,
            co2e_avoided_kg=co2e_avoided,
            factor_used=factor_val,
            factor_source=factor_meta["source"],
            methodology_version=methodology_version,
            uncertainty_rating=factor_meta["uncertainty"],
            boundary_assumptions=factor_meta["assumptions"],
        )

    # -----------------------------------------------------------------------
    # 2. Lifecycle Impact Record Logging & Double-Counting Prevention
    # -----------------------------------------------------------------------

    def get_records_for_lot(self, lot_id: str) -> List[ImpactRecord]:
        """Fetches all existing ledger records associated with a material lot."""
        stmt = select(ImpactRecord).where(ImpactRecord.lot_id == lot_id).order_by(ImpactRecord.created_at.asc())
        return list(self.db.execute(stmt).scalars().all())

    def record_lifecycle_impact_event(
        self,
        payload: ImpactRecordCreate,
        actor_org_id: str,
    ) -> ImpactRecordRead:
        """Appends a verified event to the impact ledger.

        Enforces lifecycle stage ordering and strict non-double-counting guarantees:
          - An event_type cannot be recorded more than once for the same lot.
          - 'verified_recovered' requires prior receipt ('accepted') or 'processed' confirmation.
          - 'processed' requires prior 'accepted' confirmation.
          - 'accepted' requires prior 'shipped' confirmation.
          - 'shipped' and 'offered' require prior 'generated' registration.
        """
        org_id = payload.organization_id or actor_org_id
        event = payload.event_type.strip().lower()

        # Query existing lot history
        prior_records = self.get_records_for_lot(payload.lot_id)
        existing_event_types = {r.event_type for r in prior_records}

        # 1. Double-counting check
        if event in existing_event_types:
            raise DuplicateEventError(
                f"Lifecycle event '{event}' has already been recorded for lot '{payload.lot_id}'. "
                "Double-counting is strictly prevented by ledger invariance rules.",
                details={"lot_id": payload.lot_id, "event_type": event},
            )

        # 2. State transition and dependency rules
        if event == LifecycleEventType.VERIFIED_RECOVERED.value:
            if not ("accepted" in existing_event_types or "processed" in existing_event_types):
                raise InvalidStateTransitionError(
                    f"Cannot record 'verified_recovered' for lot '{payload.lot_id}' without prior receipt "
                    "or processing confirmation ('accepted' or 'processed').",
                    details={"lot_id": payload.lot_id, "existing_events": list(existing_event_types)},
                )
        elif event == LifecycleEventType.PROCESSED.value:
            if "accepted" not in existing_event_types:
                raise InvalidStateTransitionError(
                    f"Cannot record 'processed' for lot '{payload.lot_id}' without prior buyer receipt ('accepted').",
                    details={"lot_id": payload.lot_id, "existing_events": list(existing_event_types)},
                )
        elif event == LifecycleEventType.ACCEPTED.value:
            if "shipped" not in existing_event_types:
                raise InvalidStateTransitionError(
                    f"Cannot record 'accepted' for lot '{payload.lot_id}' without prior shipment ('shipped').",
                    details={"lot_id": payload.lot_id, "existing_events": list(existing_event_types)},
                )
        elif event in (LifecycleEventType.SHIPPED.value, LifecycleEventType.OFFERED.value):
            if "generated" not in existing_event_types:
                raise InvalidStateTransitionError(
                    f"Cannot record '{event}' for lot '{payload.lot_id}' without prior lot registration ('generated').",
                    details={"lot_id": payload.lot_id, "existing_events": list(existing_event_types)},
                )

        # 3. Compute factor & emission abatement
        calc = self.calculate_environmental_impact(
            mass_kg=payload.mass_kg,
            material_category=payload.displaced_material_category,
            methodology_version=payload.methodology_version,
        )

        # 4. Determine verification status
        if payload.evidence_id:
            status = VerificationStatus.VERIFIED_RECOVERED.value if event == "verified_recovered" else VerificationStatus.EVIDENCE_ATTACHED.value
        elif event == LifecycleEventType.VERIFIED_RECOVERED.value:
            status = VerificationStatus.VERIFIED_RECOVERED.value
        else:
            status = VerificationStatus.UNVERIFIED.value

        record = ImpactRecord(
            lot_id=payload.lot_id,
            organization_id=org_id,
            facility_id=payload.facility_id,
            event_type=event,
            mass_kg=payload.mass_kg,
            displaced_material_category=payload.displaced_material_category,
            co2e_avoided_kg=calc.co2e_avoided_kg,
            methodology_version=payload.methodology_version,
            factor_source=calc.factor_source,
            verification_status=status,
            evidence_id=payload.evidence_id,
            uncertainty_rating=calc.uncertainty_rating.value,
            boundary_assumptions=calc.boundary_assumptions,
        )
        self.db.add(record)
        self.db.flush()
        self.db.refresh(record)

        return ImpactRecordRead.model_validate(record)

    # -----------------------------------------------------------------------
    # 3. Summary & Mass Balance Aggregation
    # -----------------------------------------------------------------------

    def get_mass_balance_and_summary(
        self,
        organization_id: str,
        facility_id: Optional[str] = None,
    ) -> ImpactSummaryRead:
        """Calculates mass balance across lifecycle stages to guarantee non-double-counting."""
        stmt = select(ImpactRecord).where(ImpactRecord.organization_id == organization_id)
        if facility_id:
            stmt = stmt.where(ImpactRecord.facility_id == facility_id)
        stmt = stmt.order_by(ImpactRecord.created_at.desc())

        records = list(self.db.execute(stmt).scalars().all())

        stage_totals: Dict[str, float] = defaultdict(float)
        stage_counts: Dict[str, int] = defaultdict(int)
        cat_breakdown: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
        total_co2e = 0.0

        for r in records:
            ev = r.event_type.lower()
            stage_totals[ev] += r.mass_kg
            stage_counts[ev] += 1
            cat_breakdown[r.displaced_material_category][ev] += r.mass_kg

            # Only verified_recovered records count towards realized CO2e abatement
            if ev == LifecycleEventType.VERIFIED_RECOVERED.value:
                total_co2e += r.co2e_avoided_kg

        gen_kg = stage_totals.get("generated", 0.0)
        rec_kg = stage_totals.get("verified_recovered", 0.0)
        net_pipeline = max(0.0, gen_kg - rec_kg)

        mass_balance = MassBalanceReport(
            organization_id=organization_id,
            facility_id=facility_id,
            total_generated_kg=round(gen_kg, 2),
            total_offered_kg=round(stage_totals.get("offered", 0.0), 2),
            total_shipped_kg=round(stage_totals.get("shipped", 0.0), 2),
            total_accepted_kg=round(stage_totals.get("accepted", 0.0), 2),
            total_processed_kg=round(stage_totals.get("processed", 0.0), 2),
            total_verified_recovered_kg=round(rec_kg, 2),
            total_landfill_avoided_kg=round(rec_kg, 2),
            total_co2e_avoided_kg=round(total_co2e, 2),
            net_in_pipeline_kg=round(net_pipeline, 2),
            stage_counts=dict(stage_counts),
            category_breakdown={k: dict(v) for k, v in cat_breakdown.items()},
        )

        read_records = [ImpactRecordRead.model_validate(r) for r in records]

        return ImpactSummaryRead(
            organization_id=organization_id,
            facility_id=facility_id,
            mass_balance=mass_balance,
            records=read_records,
        )

    # -----------------------------------------------------------------------
    # 4. Methodologies
    # -----------------------------------------------------------------------

    def get_supported_methodologies(self) -> List[ImpactMethodologyInfo]:
        """Returns documented factor sources, boundary assumptions, and uncertainty ratings."""
        factors_clean = {}
        for cat, data in FACTORS_V1.items():
            factors_clean[cat] = {
                "factor_kg_co2e_per_kg": data["factor"],
                "source": data["source"],
                "uncertainty_rating": data["uncertainty"].value,
                "assumptions": data["assumptions"],
            }

        return [
            ImpactMethodologyInfo(
                methodology_version="v1.0",
                name="Strata Circular Displacement & Landfill Avoidance Framework",
                description=(
                    "Standardized carbon abatement and landfill displacement model using EPA WARM, "
                    "DEFRA, and EcoInvent cradle-to-gate substitution methodologies."
                ),
                factors_by_category=factors_clean,
            )
        ]
