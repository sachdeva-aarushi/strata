from typing import Dict, List, Optional
from strata.schemas.materials import MaterialTypeInfo

MATERIAL_TAXONOMY: Dict[str, MaterialTypeInfo] = {
    "aluminum-scrap": MaterialTypeInfo(
        type_id="aluminum-scrap",
        name="Aluminum Scrap / Offcuts",
        category="metallics",
        standard_units=["kg", "tonne"],
        is_hazardous=False,
        description="Clean secondary aluminum stamping offcuts, extrusions, and swarf with known alloy designation.",
    ),
    "copper-swarf": MaterialTypeInfo(
        type_id="copper-swarf",
        name="Copper Swarf & Turnings",
        category="metallics",
        standard_units=["kg", "tonne"],
        is_hazardous=False,
        description="High-purity machining turnings and swarf from copper busbars and component manufacturing.",
    ),
    "steel-slag": MaterialTypeInfo(
        type_id="steel-slag",
        name="Electric Arc Furnace Steel Slag",
        category="metallics",
        standard_units=["tonne"],
        is_hazardous=False,
        description="Non-metallic co-product produced during electric arc furnace steelmaking, suitable for aggregate substitution.",
    ),
    "post-industrial-polypropylene": MaterialTypeInfo(
        type_id="post-industrial-polypropylene",
        name="Post-Industrial Polypropylene (PP)",
        category="polymers",
        standard_units=["kg", "tonne"],
        is_hazardous=False,
        description="Injection-molding sprues, runners, and scrap parts in unpigmented or single-pigment PP resin.",
    ),
    "regrind-hdpe": MaterialTypeInfo(
        type_id="regrind-hdpe",
        name="Regrind High-Density Polyethylene (HDPE)",
        category="polymers",
        standard_units=["kg", "tonne"],
        is_hazardous=False,
        description="Granulated blow-molding and extrusion scrap with verified melt flow index.",
    ),
    "spent-isopropanol": MaterialTypeInfo(
        type_id="spent-isopropanol",
        name="Spent Isopropanol (IPA)",
        category="chemicals",
        standard_units=["litre", "m3"],
        is_hazardous=True,
        description="Used industrial solvent from electronics or optical cleaning baths, >70% IPA purity.",
    ),
    "glycol-purge": MaterialTypeInfo(
        type_id="glycol-purge",
        name="Technical Glycol Purge",
        category="chemicals",
        standard_units=["litre", "m3"],
        is_hazardous=True,
        description="Chiller and heat transfer loop purge fluids containing ethylene or propylene glycol.",
    ),
    "wood-chips-biomass": MaterialTypeInfo(
        type_id="wood-chips-biomass",
        name="Untreated Wood Chips & Shavings",
        category="biomass",
        standard_units=["tonne", "m3"],
        is_hazardous=False,
        description="Secondary untreated timber offcuts and planar shavings from furniture and millwork fabrication.",
    ),
    "foundry-sand": MaterialTypeInfo(
        type_id="foundry-sand",
        name="Spent Foundry Sand",
        category="minerals",
        standard_units=["tonne"],
        is_hazardous=False,
        description="High-silica casting sand from ferrous casting molds with depleted bentonite/binder content.",
    ),
    "cotton-blend-offcuts": MaterialTypeInfo(
        type_id="cotton-blend-offcuts",
        name="Post-Industrial Cotton Blend Offcuts",
        category="textiles",
        standard_units=["kg", "tonne"],
        is_hazardous=False,
        description="Clean garment cutting table salvage with defined cotton/polyester blend ratio.",
    ),
    "corrugated-cardboard-bales": MaterialTypeInfo(
        type_id="corrugated-cardboard-bales",
        name="Baled OCC (Old Corrugated Containers)",
        category="packaging",
        standard_units=["tonne", "unit"],
        is_hazardous=False,
        description="Mill-spec baled corrugated cardboard packaging from incoming component deliveries.",
    ),
}


def get_all_material_types() -> List[MaterialTypeInfo]:
    """Returns the complete list of recognized material taxonomy types."""
    return list(MATERIAL_TAXONOMY.values())


def get_material_type(type_id: str) -> Optional[MaterialTypeInfo]:
    """Looks up a single material type by its unique slug."""
    return MATERIAL_TAXONOMY.get(type_id.strip().lower())
