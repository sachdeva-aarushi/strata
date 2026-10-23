from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RouteGateSpec(BaseModel):
    """Specification of a hard constraint that must be deterministically evaluated."""
    gate_id: str
    name: str
    description: str
    rule_type: str  # "max_threshold", "min_threshold", "prohibited_values", "boolean_check"
    field_name: str
    threshold_value: Any


class RequiredFactSpec(BaseModel):
    """Specification of an essential factual item needed for supported status."""
    fact_id: str
    name: str
    description: str
    acquisition_method: str = "document"  # lab_test, document, user_confirmation, external_source
    is_critical: bool = True


class CandidateRoute(BaseModel):
    """Candidate circularity pathway / receiver processing route."""
    route_id: str
    name: str
    target_material_type: str
    processor_facility_name: str
    recovery_tier: str  # reuse, direct_recycling, upcycling, solvent_recovery, downcycling
    hard_gates: List[RouteGateSpec]
    required_facts: List[RequiredFactSpec]


# Explicit candidate route catalog with deterministic requirements
CANDIDATE_ROUTES: Dict[str, CandidateRoute] = {
    "route-secondary-aluminum-smelter": CandidateRoute(
        route_id="route-secondary-aluminum-smelter",
        name="Secondary Aluminum Ingot Re-Melter",
        target_material_type="aluminum-scrap",
        processor_facility_name="Midwest Secondary Smelting Corp",
        recovery_tier="direct_recycling",
        hard_gates=[
            RouteGateSpec(
                gate_id="gate-hazardous-exclusion",
                name="Hazardous Waste Exclusion",
                description="Receiving permit strictly prohibits materials classified as hazardous.",
                rule_type="boolean_check",
                field_name="is_hazardous",
                threshold_value=False,
            ),
            RouteGateSpec(
                gate_id="gate-oil-contamination",
                name="Max Machining Oil Contamination",
                description="Baghouse filter permit limits oil/lubricant residue to 1.5% by weight.",
                rule_type="max_threshold",
                field_name="oil_contamination_pct",
                threshold_value=1.5,
            ),
            RouteGateSpec(
                gate_id="gate-prohibited-metals",
                name="Prohibited Heavy Metal Inclusions",
                description="Feedstock cannot contain lead, cadmium, or radioactive trace elements.",
                rule_type="prohibited_values",
                field_name="contaminants",
                threshold_value=["lead", "cadmium", "radioactive"],
            ),
            RouteGateSpec(
                gate_id="gate-min-lot-quantity",
                name="Minimum Furnace Melt Batch Size",
                description="Commercial receivers require at least 500 kg per melt campaign.",
                rule_type="min_threshold",
                field_name="quantity",
                threshold_value=500.0,
            ),
        ],
        required_facts=[
            RequiredFactSpec(
                fact_id="fact-alloy-series",
                name="Alloy Series Verification",
                description="Specific aluminum alloy grade (e.g. 6061, 5052, 3003) must be established.",
                acquisition_method="document",
                is_critical=True,
            ),
            RequiredFactSpec(
                fact_id="fact-moisture-level",
                name="Moisture Assay",
                description="Explosion prevention requires verified dry or moisture-tested material.",
                acquisition_method="lab_test",
                is_critical=True,
            ),
        ],
    ),
    "route-solvent-distillation-plant": CandidateRoute(
        route_id="route-solvent-distillation-plant",
        name="Fractional Solvent Re-Distillation Facility",
        target_material_type="spent-isopropanol",
        processor_facility_name="Apex Chemical Purification Works",
        recovery_tier="solvent_recovery",
        hard_gates=[
            RouteGateSpec(
                gate_id="gate-min-solvent-purity",
                name="Minimum Initial Solvent Purity",
                description="Thermal re-boiler requires minimum 65% initial alcohol concentration.",
                rule_type="min_threshold",
                field_name="purity_pct",
                threshold_value=65.0,
            ),
            RouteGateSpec(
                gate_id="gate-prohibited-halogens",
                name="Chlorinated Solvent Exclusion",
                description="Distillation column metallurgy cannot accept chlorinated solvents (DCM, TCE).",
                rule_type="prohibited_values",
                field_name="contaminants",
                threshold_value=["chlorinated_solvents", "pcb", "tce"],
            ),
        ],
        required_facts=[
            RequiredFactSpec(
                fact_id="fact-safety-data-sheet",
                name="Safety Data Sheet (SDS)",
                description="Current manufacturer Safety Data Sheet detailing solvent composition.",
                acquisition_method="document",
                is_critical=True,
            ),
            RequiredFactSpec(
                fact_id="fact-water-content-assay",
                name="Karl Fischer Water Titration Assay",
                description="Certified water content lab analysis to program reflux ratios.",
                acquisition_method="lab_test",
                is_critical=True,
            ),
        ],
    ),
    "route-pp-injection-regrind": CandidateRoute(
        route_id="route-pp-injection-regrind",
        name="Closed-Loop PP Compounding & Regrind",
        target_material_type="post-industrial-polypropylene",
        processor_facility_name="Polymer Circular Solutions LLC",
        recovery_tier="upcycling",
        hard_gates=[
            RouteGateSpec(
                gate_id="gate-hazardous-exclusion",
                name="Hazardous Material Exclusion",
                description="Plastic food-contact / automotive extrusion lines prohibit toxic residues.",
                rule_type="boolean_check",
                field_name="is_hazardous",
                threshold_value=False,
            ),
            RouteGateSpec(
                gate_id="gate-cross-polymer-contamination",
                name="Cross-Polymer Contamination Limit",
                description="Melt incompatibility limits non-PP polymer contamination to under 2.0%.",
                rule_type="max_threshold",
                field_name="cross_polymer_pct",
                threshold_value=2.0,
            ),
        ],
        required_facts=[
            RequiredFactSpec(
                fact_id="fact-melt-flow-index",
                name="Melt Flow Index (MFI) Test",
                description="Laboratory MFI determination (g/10 min at 230°C/2.16kg).",
                acquisition_method="lab_test",
                is_critical=True,
            ),
            RequiredFactSpec(
                fact_id="fact-color-consistency",
                name="Color Consistency Declaration",
                description="Single color declaration or sorted fraction confirmation.",
                acquisition_method="user_confirmation",
                is_critical=False,
            ),
        ],
    ),
}


def get_candidate_routes_for_material(material_type: str) -> List[CandidateRoute]:
    """Retrieves all pre-configured candidate recovery routes for a material type."""
    normalized = material_type.strip().lower()
    return [route for route in CANDIDATE_ROUTES.values() if route.target_material_type == normalized]


def get_candidate_route_by_id(route_id: str) -> Optional[CandidateRoute]:
    """Retrieves a single candidate route definition by ID."""
    return CANDIDATE_ROUTES.get(route_id)
