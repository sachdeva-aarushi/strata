"""
================================================================================
STRATA DATABASE SCHEMA SUMMARY (Verified against SQLAlchemy Models & Alembic Migrations)
================================================================================
Inspection completed on 2026-10-24 across:
  - Alembic Migrations:
      * 86db0305b294_initial_materials_and_evidence_schema.py
      * 176974e49e35_expand_id_column_lengths.py
      * 763cd0eb4a1b_add_marketplace_tables.py
  - SQLAlchemy Models:
      * strata.domain.materials.models (Organization, Facility, MaterialLot)
      * strata.domain.marketplace.models (Listing, BuyerRequirement, RFQModel, OfferModel, WorkflowEventModel)
      * strata.domain.impact.models (ImpactRecord)
      * strata.domain.qualification.models (EvidenceRecord, Investigation, QualificationAssessment)

TABLES, EXACT COLUMNS, AND DATA_PROVENANCE PRESENCE:

1. organizations
   - Table name: organizations
   - Columns: org_id (PK, String 64), name (String 255), org_type (String 50),
              created_at (DateTime TZ), updated_at (DateTime TZ)
   - data_provenance column: NO

2. facilities
   - Table name: facilities
   - Columns: facility_id (PK, String 64), org_id (FK, String 64), name (String 255),
              location_country (String 2), location_postal_code (String 20),
              cluster_id (String 36), city_id (String 64), zone_id (String 64),
              processing_capacity_tpa (Float), facility_type (String 50),
              created_at (DateTime TZ), updated_at (DateTime TZ)
   - data_provenance column: NO

3. material_lots
   - Table name: material_lots
   - Columns: lot_id (PK, String 64), org_id (FK, String 64), facility_id (FK, String 64),
              material_type (String 100), quantity (Float), unit (String 20),
              status (String 50), availability_from (Date), availability_to (Date),
              declared_attributes (JSON), provenance_label (String 50),
              created_at (DateTime TZ), updated_at (DateTime TZ)
   - data_provenance column: NO (uses 'provenance_label' which receives 'synthetic_demo')

4. marketplace_listings
   - Table name: marketplace_listings
   - Columns: id (PK, String 36), material_lot_id (String 36), organization_id (String 36),
              facility_id (String 36), visibility (Enum: private, cluster_only, public),
              asking_price_per_unit (Float), currency (String 3), available_quantity (Float),
              unit (String 20), status (Enum: draft, active, paused, sold_out, withdrawn),
              created_at (DateTime TZ), updated_at (DateTime TZ)
   - data_provenance column: NO

5. marketplace_buyer_requirements
   - Table name: marketplace_buyer_requirements
   - Columns: id (PK, String 36), organization_id (String 36), facility_id (String 36),
              material_category (String 100), min_quantity (Float), max_quantity (Float),
              unit (String 20), target_price_per_unit (Float), required_properties (JSON),
              prohibited_conditions (JSON), visibility (Enum), location (String 255),
              delivery_requirements (JSON), constraints (JSON),
              created_at (DateTime TZ), updated_at (DateTime TZ)
   - data_provenance column: NO

6. marketplace_rfqs
   - Table name: marketplace_rfqs
   - Columns: id (PK, String 36), listing_id (String 36), buyer_requirement_id (String 36),
              buyer_organization_id (String 36), buyer_facility_id (String 36),
              seller_organization_id (String 36), seller_facility_id (String 36),
              requested_quantity (Float), unit (String 20), target_price_per_unit (Float),
              currency (String 3), status (Enum: draft, pending_approval, open, closed, cancelled),
              notes (String 500), created_by (String 36), approved_by (String 36),
              approved_at (DateTime TZ), created_at (DateTime TZ), updated_at (DateTime TZ)
   - data_provenance column: NO

7. marketplace_offers
   - Table name: marketplace_offers
   - Columns: id (PK, String 36), rfq_id (String 36), listing_id (String 36),
              seller_organization_id (String 36), seller_facility_id (String 36),
              offered_quantity (Float), unit (String 20), price_per_unit (Float),
              currency (String 3), status (Enum: submitted, under_review, revised, accepted, rejected, withdrawn),
              terms (String 500), valid_until (DateTime TZ), created_by (String 36),
              reviewed_by (String 36), reviewed_at (DateTime TZ),
              created_at (DateTime TZ), updated_at (DateTime TZ)
   - data_provenance column: NO

8. marketplace_workflow_events
   - Table name: marketplace_workflow_events
   - Columns: id (PK, String 36), entity_type (String 50), entity_id (String 36),
              event_type (String 50), from_state (String 50), to_state (String 50),
              actor_id (String 36), actor_role (String 50), actor_org_id (String 36),
              notes (String 500), metadata (JSON), created_at (DateTime TZ)
   - data_provenance column: NO (stored inside metadata JSON payload)

9. impact_records
   - Table name: impact_records
   - Columns: id (PK, String 36), lot_id (String 64), organization_id (String 64),
              facility_id (String 64), event_type (String 50), mass_kg (Float),
              displaced_material_category (String 100), co2e_avoided_kg (Float),
              methodology_version (String 20), factor_source (String 255),
              verification_status (String 50), evidence_id (String 64),
              uncertainty_rating (String 20), boundary_assumptions (String 500),
              created_at (DateTime TZ), updated_at (DateTime TZ)
   - data_provenance column: NO

10. evidence_records
    - Table name: evidence_records
    - Columns: evidence_id (PK, String 64), org_id (String 64), lot_id (String 64),
               claim_subject (String 100), claim_text (Text), source_url (String 1000),
               source_title (String 255), source_type (String 50), retrieved_at (DateTime TZ),
               extraction_method (String 50), provenance (String 50), verification_state (String 50),
               supporting_passage (Text), content_hash (String 64), document_ref (String 500),
               verified_by (String 100), contradicted_by (JSON),
               created_at (DateTime TZ), updated_at (DateTime TZ)
    - data_provenance column: NO (uses 'provenance' column)

11. investigations
    - Table name: investigations
    - Columns: investigation_id (PK, String 64), org_id (String 64), lot_id (String 64),
               status (String 50), error_message (Text), notes (Text), completed_at (DateTime TZ),
               created_at (DateTime TZ), updated_at (DateTime TZ)
    - data_provenance column: NO

12. qualification_assessments
    - Table name: qualification_assessments
    - Columns: assessment_id (PK, String 64), investigation_id (String 64), lot_id (String 64),
               candidate_route_id (String 100), status (String 50), hard_gate_results (JSON),
               blocking_conditions (JSON), missing_facts (JSON), rationale (Text),
               next_action (Text), evidence_refs (JSON), rule_version (String 50),
               assessed_at (DateTime TZ), created_at (DateTime TZ), updated_at (DateTime TZ)
    - data_provenance column: NO

RULE ENFORCEMENT SUMMARY:
- Every synthetic record explicitly includes data_provenance = "synthetic_demo" for tables that have that column.
- For tables without data_provenance, the column is skipped to preserve schema integrity without ALTER operations.
- Material lots populate provenance_label = "synthetic_demo".
================================================================================
"""

from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import traceback
import uuid

# ------------------------------------------------------------------------------
# 1. Environment and Path Bootstrapping
# ------------------------------------------------------------------------------
print("STRATA Demo Seed — DEVELOPMENT ONLY")

ROOT_DIR = Path(__file__).resolve().parent.parent
API_SRC = ROOT_DIR / "apps" / "api" / "src"
if str(API_SRC) not in sys.path:
    sys.path.insert(0, str(API_SRC))

# ------------------------------------------------------------------------------
# 2. Safety Guard: Development Environment Only
# ------------------------------------------------------------------------------
db_url = os.getenv("DATABASE_URL", "sqlite:///./strata.db")
db_url_lower = db_url.lower()
if "prod" in db_url_lower or "production" in db_url_lower:
    print(
        f"ERROR: Target database URL '{db_url}' points to a production host. "
        "Demo seed data can only be run against development or local databases.",
        file=sys.stderr,
    )
    sys.exit(1)

# ------------------------------------------------------------------------------
# 3. Imports from STRATA Core & Database
# ------------------------------------------------------------------------------
from sqlalchemy import MetaData, Table, inspect, select, text
from strata.db.base import Base
from strata.db.session import create_app_engine
import strata.domain.impact.models  # noqa: F401
import strata.domain.marketplace.models  # noqa: F401
import strata.domain.materials.models  # noqa: F401
import strata.domain.qualification.models  # noqa: F401

# ------------------------------------------------------------------------------
# 4. Deterministic UUID Generator (RFC 4122 v5)
# ------------------------------------------------------------------------------
STRATA_NAMESPACE = uuid.UUID("a9b8c7d6-e5f4-4321-ba98-0123456789ab")


def demo_id(seed_key: str) -> str:
    """Generates a stable, reproducible UUID string from a seed key."""
    return str(uuid.uuid5(STRATA_NAMESPACE, f"strata-seed-{seed_key}"))


# ------------------------------------------------------------------------------
# 5. Helper Functions for Idempotent Core Inserts
# ------------------------------------------------------------------------------
def insert_idempotent(conn, table: Table, row: dict, pk_col_name: str) -> bool:
    """Inserts a row if the primary key does not already exist.

    Dynamically filters the dictionary to only columns existing on the table,
    automatically honoring constraint rule 7 (skipping absent columns like data_provenance).
    """
    pk_val = row[pk_col_name]
    check_stmt = select(table.c[pk_col_name]).where(table.c[pk_col_name] == pk_val)
    existing = conn.execute(check_stmt).scalar()
    filtered_row = {k: v for k, v in row.items() if k in table.c}
    if existing is not None:
        conn.execute(table.update().where(table.c[pk_col_name] == pk_val).values(**filtered_row))
        return False  # Record already existed, updated with current fields

    conn.execute(table.insert().values(**filtered_row))
    return True


# ------------------------------------------------------------------------------
# 6. Cluster Seed Data Specifications
# ------------------------------------------------------------------------------
CLUSTERS = [
    {
        "id": "panipat",
        "name": "Panipat",
        "tag": "PNP",
        "city": "Panipat",
        "state": "Haryana",
        "pincode": "132103",
        "lat": 29.3909,
        "lon": 76.9635,
        "seller_name": "Panipat Shoddy Works Pvt Ltd [DEMO]",
        "buyer_name": "Northern Wool Recyclers Corp [DEMO]",
        "seller_fac_name": "Panipat Model Shoddy Mill [DEMO]",
        "buyer_fac_name": "Northern Insulation Processing Plant [DEMO]",
        "material_type": "post_consumer_cotton_blend",
        "form": "bale",
        "price_per_kg": 8.0,
        "co2e_factor": 14.2,
        "factor_source": "EPA WARM v15",
        "uncertainty": "HIGH",
        "displaced_cat": "pre-consumer cotton",
        "boundary_assumptions": "Post-consumer cotton and blended textile waste conversion to shoddy wool",
        "lot1_qty": 12000.0,
        "lot2_qty": 8000.0,
        "comp1": {"cotton": 0.75, "wool_shoddy": 0.20, "synthetic_blend": 0.05},
        "comp2": {"cotton": 0.60, "synthetic_blend": 0.40},
        "lot1_contam": 1.5,
        "lot1_moist": 4.0,
        "lot2_contam": 4.5,
        "lot2_moist": 7.0,
        "rfq_qty": 6000.0,
    },
    {
        "id": "tiruppur",
        "name": "Tiruppur",
        "tag": "TPR",
        "city": "Tiruppur",
        "state": "Tamil Nadu",
        "pincode": "641604",
        "lat": 11.1085,
        "lon": 77.3411,
        "seller_name": "Tiruppur Knitwear Discards Ltd [DEMO]",
        "buyer_name": "Kongu Eco-Spinning Mills Pvt Ltd [DEMO]",
        "seller_fac_name": "Tiruppur Knitting & Cutting Unit [DEMO]",
        "buyer_fac_name": "Kongu Open-End Spinning Facility [DEMO]",
        "material_type": "cotton_yarn_offcuts",
        "form": "loose_cuttings",
        "price_per_kg": 45.0,
        "co2e_factor": 3.5,
        "factor_source": "DEFRA 2023",
        "uncertainty": "MEDIUM",
        "displaced_cat": "virgin combed cotton yarn",
        "boundary_assumptions": "Mechanical yarn offcut re-spinning displacing virgin ring-spun yarn",
        "lot1_qty": 15000.0,
        "lot2_qty": 5000.0,
        "comp1": {"cotton_combed_yarn": 0.98, "trace_fibers": 0.02},
        "comp2": {"moisture": 0.70, "inorganic_salts": 0.20, "organic_dye_sludge": 0.10},
        "lot1_contam": 0.5,
        "lot1_moist": 3.0,
        "lot2_contam": 15.0,
        "lot2_moist": 70.0,
        "rfq_qty": 7500.0,
    },
    {
        "id": "surat",
        "name": "Surat",
        "tag": "SRT",
        "city": "Surat",
        "state": "Gujarat",
        "pincode": "395003",
        "lat": 21.1702,
        "lon": 72.8311,
        "seller_name": "Surat Poly-Tex Fabrics Ltd [DEMO]",
        "buyer_name": "Navsari PET Reclamation Systems [DEMO]",
        "seller_fac_name": "Surat Weaving & Finishing Hub [DEMO]",
        "buyer_fac_name": "Navsari Re-Granulation Mill [DEMO]",
        "material_type": "polyester_fabric_offcuts",
        "form": "shredded_chips",
        "price_per_kg": 22.0,
        "co2e_factor": 2.9,
        "factor_source": "DEFRA 2023",
        "uncertainty": "MEDIUM",
        "displaced_cat": "virgin polyester staple fiber",
        "boundary_assumptions": "Mechanical re-granulation of polyester scrap to rPET chip",
        "lot1_qty": 10000.0,
        "lot2_qty": 6000.0,
        "comp1": {"polyethylene_terephthalate": 0.95, "elastane": 0.05},
        "comp2": {"recycled_pet": 0.90, "fines": 0.10},
        "lot1_contam": 1.0,
        "lot1_moist": 1.0,
        "lot2_contam": 2.0,
        "lot2_moist": 1.5,
        "rfq_qty": 5000.0,
    },
]


def run_seed() -> None:
    """Executes the complete demo seed pipeline idempotently."""
    engine = create_app_engine()

    # Ensure schema tables exist on the development engine
    Base.metadata.create_all(bind=engine)

    # Reflect metadata to obtain SQLAlchemy Core Table objects
    metadata = MetaData()
    metadata.reflect(bind=engine)

    t_orgs = metadata.tables["organizations"]
    t_facs = metadata.tables["facilities"]
    t_lots = metadata.tables["material_lots"]
    t_listings = metadata.tables["marketplace_listings"]
    t_buyer_reqs = metadata.tables["marketplace_buyer_requirements"]
    t_rfqs = metadata.tables["marketplace_rfqs"]
    t_offers = metadata.tables["marketplace_offers"]
    t_events = metadata.tables["marketplace_workflow_events"]
    t_impact = metadata.tables["impact_records"]

    now = datetime.now(timezone.utc)
    today = date.today()

    summary_counts = {c["id"]: {"orgs": 0, "lots": 0, "listings": 0, "rfqs": 0, "offers": 0, "impact": 0} for c in CLUSTERS}

    with engine.begin() as conn:
        for c in CLUSTERS:
            cid = c["id"]

            # 1. ORGANIZATIONS (2 per cluster: Seller & Buyer)
            seller_org_id = demo_id(f"{cid}-seller-org")
            buyer_org_id = demo_id(f"{cid}-buyer-org")

            insert_idempotent(
                conn,
                t_orgs,
                {
                    "org_id": seller_org_id,
                    "name": c["seller_name"],
                    "org_type": "generator",
                    "data_provenance": "synthetic_demo",
                    "created_at": now,
                    "updated_at": now,
                },
                "org_id",
            )
            insert_idempotent(
                conn,
                t_orgs,
                {
                    "org_id": buyer_org_id,
                    "name": c["buyer_name"],
                    "org_type": "processor",
                    "data_provenance": "synthetic_demo",
                    "created_at": now,
                    "updated_at": now,
                },
                "org_id",
            )
            summary_counts[cid]["orgs"] = 2

            # 2. FACILITIES (Seller and Buyer facilities)
            seller_fac_id = demo_id(f"{cid}-seller-facility")
            buyer_fac_id = demo_id(f"{cid}-buyer-facility")

            insert_idempotent(
                conn,
                t_facs,
                {
                    "facility_id": seller_fac_id,
                    "org_id": seller_org_id,
                    "name": c["seller_fac_name"],
                    "location_country": "IN",
                    "location_postal_code": c["pincode"],
                    "cluster_id": cid,
                    "city_id": c["city"],
                    "zone_id": f"{cid}-industrial-zone-1",
                    "processing_capacity_tpa": 25000.0,
                    "facility_type": "generator",
                    "city": c["city"],
                    "state": c["state"],
                    "pincode": c["pincode"],
                    "latitude": c["lat"],
                    "longitude": c["lon"],
                    "data_provenance": "synthetic_demo",
                    "created_at": now,
                    "updated_at": now,
                },
                "facility_id",
            )
            insert_idempotent(
                conn,
                t_facs,
                {
                    "facility_id": buyer_fac_id,
                    "org_id": buyer_org_id,
                    "name": c["buyer_fac_name"],
                    "location_country": "IN",
                    "location_postal_code": c["pincode"],
                    "cluster_id": cid,
                    "city_id": c["city"],
                    "zone_id": f"{cid}-industrial-zone-1",
                    "processing_capacity_tpa": 50000.0,
                    "facility_type": "processor",
                    "city": c["city"],
                    "state": c["state"],
                    "pincode": c["pincode"],
                    "latitude": c["lat"] + 0.01,
                    "longitude": c["lon"] + 0.01,
                    "data_provenance": "synthetic_demo",
                    "created_at": now,
                    "updated_at": now,
                },
                "facility_id",
            )

            # 3. MATERIAL LOTS (2 per facility: 1 listable, 1 pending_qualification)
            lot1_id = demo_id(f"{cid}-lot-1-listable")
            lot2_id = demo_id(f"{cid}-lot-2-pending")

            insert_idempotent(
                conn,
                t_lots,
                {
                    "lot_id": lot1_id,
                    "org_id": seller_org_id,
                    "facility_id": seller_fac_id,
                    "material_type": c["material_type"],
                    "quantity": c["lot1_qty"],
                    "unit": "kg",
                    "status": "listable",
                    "availability_from": today,
                    "availability_to": today + timedelta(days=90),
                    "declared_attributes": {
                        "physical_form": c["form"],
                        "composition_json": c["comp1"],
                        "contamination_pct": c["lot1_contam"],
                        "moisture_pct": c["lot1_moist"],
                        "batch_reference": f"BATCH-{c['tag']}-2026-001",
                    },
                    "provenance_label": "synthetic_demo",
                    "data_provenance": "synthetic_demo",
                    "created_at": now,
                    "updated_at": now,
                },
                "lot_id",
            )
            insert_idempotent(
                conn,
                t_lots,
                {
                    "lot_id": lot2_id,
                    "org_id": seller_org_id,
                    "facility_id": seller_fac_id,
                    "material_type": c["material_type"],
                    "quantity": c["lot2_qty"],
                    "unit": "kg",
                    "status": "pending_qualification",
                    "availability_from": today + timedelta(days=15),
                    "availability_to": today + timedelta(days=105),
                    "declared_attributes": {
                        "physical_form": c["form"],
                        "composition_json": c["comp2"],
                        "contamination_pct": c["lot2_contam"],
                        "moisture_pct": c["lot2_moist"],
                        "batch_reference": f"BATCH-{c['tag']}-2026-002",
                    },
                    "provenance_label": "synthetic_demo",
                    "data_provenance": "synthetic_demo",
                    "created_at": now,
                    "updated_at": now,
                },
                "lot_id",
            )
            summary_counts[cid]["lots"] = 2

            # 4. MARKETPLACE LISTING (1 per listable lot)
            listing_id = demo_id(f"{cid}-listing-1")
            insert_idempotent(
                conn,
                t_listings,
                {
                    "id": listing_id,
                    "material_lot_id": lot1_id,
                    "organization_id": seller_org_id,
                    "facility_id": seller_fac_id,
                    "visibility": "cluster_only",
                    "asking_price_per_unit": c["price_per_kg"],
                    "currency": "INR",
                    "available_quantity": c["lot1_qty"],
                    "unit": "kg",
                    "status": "active",
                    "data_provenance": "synthetic_demo",
                    "created_at": now,
                    "updated_at": now,
                },
                "id",
            )
            summary_counts[cid]["listings"] = 1

            # 5. BUYER REQUIREMENT (1 per buyer org)
            req_id = demo_id(f"{cid}-buyer-req-1")
            insert_idempotent(
                conn,
                t_buyer_reqs,
                {
                    "id": req_id,
                    "organization_id": buyer_org_id,
                    "facility_id": buyer_fac_id,
                    "material_category": c["material_type"],
                    "min_quantity": 2000.0,
                    "max_quantity": 30000.0,
                    "unit": "kg",
                    "target_price_per_unit": c["price_per_kg"] + 0.5,
                    "required_properties": {"cleanliness": "high", "max_moisture_pct": 5.0},
                    "prohibited_conditions": ["hazardous_chemicals", "metal_shards"],
                    "visibility": "cluster_only",
                    "location": f"{c['city']}, {c['state']}",
                    "delivery_requirements": {"max_lead_time_days": 14},
                    "constraints": {"require_certificate_of_origin": True},
                    "data_provenance": "synthetic_demo",
                    "created_at": now,
                    "updated_at": now,
                },
                "id",
            )

            # 6. RFQ (1 per cluster, status = "open")
            rfq_id = demo_id(f"{cid}-rfq-1")
            buyer_admin_id = demo_id(f"{cid}-buyer-admin-user")
            seller_admin_id = demo_id(f"{cid}-seller-admin-user")

            insert_idempotent(
                conn,
                t_rfqs,
                {
                    "id": rfq_id,
                    "listing_id": listing_id,
                    "buyer_requirement_id": req_id,
                    "buyer_organization_id": buyer_org_id,
                    "buyer_facility_id": buyer_fac_id,
                    "seller_organization_id": seller_org_id,
                    "seller_facility_id": seller_fac_id,
                    "requested_quantity": c["rfq_qty"],
                    "unit": "kg",
                    "target_price_per_unit": c["price_per_kg"] + 0.5,
                    "currency": "INR",
                    "status": "open",
                    "notes": f"Commercial RFQ for {c['name']} industrial circularity flow [DEMO]",
                    "created_by": buyer_admin_id,
                    "approved_by": buyer_admin_id,
                    "approved_at": now,
                    "data_provenance": "synthetic_demo",
                    "created_at": now - timedelta(days=2),
                    "updated_at": now,
                },
                "id",
            )
            summary_counts[cid]["rfqs"] = 1

            # 7. OFFER (1 per RFQ, status = "under_review")
            offer_id = demo_id(f"{cid}-offer-1")
            insert_idempotent(
                conn,
                t_offers,
                {
                    "id": offer_id,
                    "rfq_id": rfq_id,
                    "listing_id": listing_id,
                    "seller_organization_id": seller_org_id,
                    "seller_facility_id": seller_fac_id,
                    "offered_quantity": c["rfq_qty"],
                    "unit": "kg",
                    "price_per_unit": c["price_per_kg"],
                    "currency": "INR",
                    "status": "under_review",
                    "terms": f"Net 30 payment terms, ex-works {c['city']} facility [DEMO]",
                    "valid_until": now + timedelta(days=30),
                    "created_by": seller_admin_id,
                    "data_provenance": "synthetic_demo",
                    "created_at": now - timedelta(days=1),
                    "updated_at": now,
                },
                "id",
            )
            summary_counts[cid]["offers"] = 1

            # 8. IMPACT RECORDS (2 per cluster: verified_recovered and offered)
            # Sentinel blockchain tx hash: "0xSEED" + tag + "0"*54 truncated to 66 chars
            raw_tx = "0xSEED" + c["tag"] + ("0" * 54)
            blockchain_tx = raw_tx[:66]

            impact_verified_id = demo_id(f"{cid}-impact-verified")
            impact_offered_id = demo_id(f"{cid}-impact-offered")

            insert_idempotent(
                conn,
                t_impact,
                {
                    "id": impact_verified_id,
                    "lot_id": lot1_id,
                    "organization_id": seller_org_id,
                    "facility_id": seller_fac_id,
                    "event_type": "verified_recovered",
                    "mass_kg": c["rfq_qty"],
                    "displaced_material_category": c["displaced_cat"],
                    "co2e_avoided_kg": round(c["rfq_qty"] * c["co2e_factor"], 2),
                    "methodology_version": "v1.0",
                    "factor_source": c["factor_source"],
                    "verification_status": "verified",
                    "evidence_id": demo_id(f"{cid}-evidence-anchor-1"),
                    "uncertainty_rating": c["uncertainty"],
                    "boundary_assumptions": c["boundary_assumptions"],
                    "blockchain_tx_hash": blockchain_tx,
                    "block_number": 19500000,
                    "data_provenance": "synthetic_demo",
                    "created_at": now - timedelta(hours=4),
                    "updated_at": now - timedelta(hours=4),
                },
                "id",
            )
            insert_idempotent(
                conn,
                t_impact,
                {
                    "id": impact_offered_id,
                    "lot_id": lot1_id,
                    "organization_id": seller_org_id,
                    "facility_id": seller_fac_id,
                    "event_type": "offered",
                    "mass_kg": c["lot1_qty"],
                    "displaced_material_category": c["displaced_cat"],
                    "co2e_avoided_kg": round(c["lot1_qty"] * c["co2e_factor"], 2),
                    "methodology_version": "v1.0",
                    "factor_source": c["factor_source"],
                    "verification_status": "unverified",
                    "evidence_id": None,
                    "uncertainty_rating": c["uncertainty"],
                    "boundary_assumptions": c["boundary_assumptions"],
                    "blockchain_tx_hash": None,
                    "block_number": None,
                    "data_provenance": "synthetic_demo",
                    "created_at": now - timedelta(days=2),
                    "updated_at": now - timedelta(days=2),
                },
                "id",
            )
            summary_counts[cid]["impact"] = 2

            # 9. WORKFLOW EVENT RECORDS (DRAFT -> PENDING_APPROVAL -> OPEN audit trail)
            transitions = [
                (demo_id(f"{cid}-evt-draft"), "created", None, "draft", now - timedelta(days=3)),
                (demo_id(f"{cid}-evt-pending"), "submitted_for_approval", "draft", "pending_approval", now - timedelta(days=2)),
                (demo_id(f"{cid}-evt-open"), "approved", "pending_approval", "open", now - timedelta(days=1)),
            ]
            for evt_id, ev_type, f_state, t_state, ev_time in transitions:
                insert_idempotent(
                    conn,
                    t_events,
                    {
                        "id": evt_id,
                        "entity_type": "rfq",
                        "entity_id": rfq_id,
                        "event_type": ev_type,
                        "from_state": f_state,
                        "to_state": t_state,
                        "actor_id": buyer_admin_id,
                        "actor_role": "buyer_procurement_lead",
                        "actor_org_id": buyer_org_id,
                        "notes": f"RFQ transition to {t_state} [DEMO]",
                        "metadata": {"data_provenance": "synthetic_demo", "cluster": cid},
                        "data_provenance": "synthetic_demo",
                        "created_at": ev_time,
                    },
                    "id",
                )

    # --------------------------------------------------------------------------
    # 7. Acceptance Test Assertions
    # --------------------------------------------------------------------------
    inspector = inspect(engine)
    listing_cols = {col["name"] for col in inspector.get_columns("marketplace_listings")}
    rfq_cols = {col["name"] for col in inspector.get_columns("marketplace_rfqs")}
    impact_cols = {col["name"] for col in inspector.get_columns("impact_records")}

    with engine.connect() as conn:
        # Assertion 1: Marketplace Listings
        if "data_provenance" in listing_cols:
            q_listings = "SELECT COUNT(*) FROM marketplace_listings WHERE data_provenance = 'synthetic_demo' AND status = 'active'"
        else:
            q_listings = "SELECT COUNT(*) FROM marketplace_listings WHERE status = 'active'"
        res_listings = conn.execute(text(q_listings)).scalar()
        assert res_listings >= 3, f"Acceptance check failed: expected >= 3 active listings, got {res_listings}"

        # Assertion 2: Marketplace RFQs
        if "data_provenance" in rfq_cols:
            q_rfqs = "SELECT COUNT(*) FROM marketplace_rfqs WHERE data_provenance = 'synthetic_demo' AND status = 'open'"
        else:
            q_rfqs = "SELECT COUNT(*) FROM marketplace_rfqs WHERE status = 'open'"
        res_rfqs = conn.execute(text(q_rfqs)).scalar()
        assert res_rfqs >= 3, f"Acceptance check failed: expected >= 3 open RFQs, got {res_rfqs}"

        # Assertion 3: Impact Records (verified_recovered)
        if "data_provenance" in impact_cols:
            q_impact = "SELECT COUNT(*) FROM impact_records WHERE data_provenance = 'synthetic_demo' AND event_type = 'verified_recovered'"
        else:
            q_impact = "SELECT COUNT(*) FROM impact_records WHERE event_type = 'verified_recovered'"
        res_impact = conn.execute(text(q_impact)).scalar()
        assert res_impact >= 3, f"Acceptance check failed: expected >= 3 verified_recovered impact records, got {res_impact}"

        # Assertion 4: Multi-tenant distinct organization isolation
        if "data_provenance" in listing_cols:
            q_orgs = "SELECT COUNT(DISTINCT organization_id) FROM marketplace_listings WHERE data_provenance = 'synthetic_demo'"
        else:
            q_orgs = "SELECT COUNT(DISTINCT organization_id) FROM marketplace_listings"
        res_orgs = conn.execute(text(q_orgs)).scalar()
        assert res_orgs >= 3, f"Acceptance check failed: expected >= 3 distinct listing orgs, got {res_orgs}"

    # --------------------------------------------------------------------------
    # 8. Structured Completion Summary Table
    # --------------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("STRATA DEMO SEED DATA SUMMARY")
    print("=" * 78)
    header = f"{'Cluster':<13} | {'Organizations':<13} | {'Lots':<4} | {'Listings':<8} | {'RFQs':<4} | {'Offers':<6} | {'Impact Records':<14}"
    print(header)
    print("-" * len(header))
    for c in CLUSTERS:
        cid = c["id"]
        counts = summary_counts[cid]
        print(
            f"{c['name']:<13} | {counts['orgs']:<13} | {counts['lots']:<4} | {counts['listings']:<8} | {counts['rfqs']:<4} | {counts['offers']:<6} | {counts['impact']:<14}"
        )
    print("=" * 78)
    print("Seed completed successfully. All 4 acceptance tests PASSED.\n")


if __name__ == "__main__":
    try:
        run_seed()
        sys.exit(0)
    except Exception as exc:
        print(f"\nSEED FAILED: {exc}\n", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)
