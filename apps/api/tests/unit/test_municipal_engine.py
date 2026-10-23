from datetime import date
import uuid
import pytest

from strata.domain.marketplace.models import Listing
from strata.domain.marketplace.municipal import MunicipalIntelligenceEngine
from strata.domain.marketplace.schemas import ListingStatus, ListingVisibility
from strata.domain.materials.models import Facility, MaterialLot, Organization
from strata.schemas.municipal import DataProvenanceLabel


@pytest.fixture
def municipal_test_data(db_session):
    city_id = f"city-{uuid.uuid4()}"
    org_id = str(uuid.uuid4())
    db_session.add(Organization(org_id=org_id, name="Test Eco Org", org_type="processor"))
    db_session.flush()

    # Zone A: Only 2 facilities (< 3 -> cohort suppressed)
    fac_a1 = Facility(
        facility_id=str(uuid.uuid4()),
        org_id=org_id,
        name="Confidential Plant Alpha",
        city_id=city_id,
        zone_id="zone-a",
        processing_capacity_tpa=50.0,
    )
    fac_a2 = Facility(
        facility_id=str(uuid.uuid4()),
        org_id=org_id,
        name="Confidential Plant Beta",
        city_id=city_id,
        zone_id="zone-a",
        processing_capacity_tpa=60.0,
    )

    # Zone B: 3 facilities (>= 3 -> cohort disclosed, DEFICIT hotspot)
    fac_b1 = Facility(
        facility_id=str(uuid.uuid4()),
        org_id=org_id,
        name="Textile Processing Site 1",
        city_id=city_id,
        zone_id="zone-b",
        processing_capacity_tpa=20.0,
    )
    fac_b2 = Facility(
        facility_id=str(uuid.uuid4()),
        org_id=org_id,
        name="Textile Processing Site 2",
        city_id=city_id,
        zone_id="zone-b",
        processing_capacity_tpa=30.0,
    )
    fac_b3 = Facility(
        facility_id=str(uuid.uuid4()),
        org_id=org_id,
        name="Textile Processing Site 3",
        city_id=city_id,
        zone_id="zone-b",
        processing_capacity_tpa=25.0,
    )

    # Zone C: 3 facilities (>= 3 -> SURPLUS capacity)
    fac_c1 = Facility(
        facility_id=str(uuid.uuid4()),
        org_id=org_id,
        name="Recycling Hub 1",
        city_id=city_id,
        zone_id="zone-c",
        processing_capacity_tpa=500.0,
    )
    fac_c2 = Facility(
        facility_id=str(uuid.uuid4()),
        org_id=org_id,
        name="Recycling Hub 2",
        city_id=city_id,
        zone_id="zone-c",
        processing_capacity_tpa=400.0,
    )
    fac_c3 = Facility(
        facility_id=str(uuid.uuid4()),
        org_id=org_id,
        name="Recycling Hub 3",
        city_id=city_id,
        zone_id="zone-c",
        processing_capacity_tpa=300.0,
    )

    db_session.add_all([fac_a1, fac_a2, fac_b1, fac_b2, fac_b3, fac_c1, fac_c2, fac_c3])
    db_session.flush()

    # Lots for Zone A (15 tonnes generated across 2 facilities)
    lot_a1 = MaterialLot(
        org_id=org_id,
        facility_id=fac_a1.facility_id,
        material_type="cotton-blend-offcuts",
        quantity=5000.0,
        unit="kg",
        status="available",
        availability_from=date(2026, 11, 1),
    )
    lot_a2 = MaterialLot(
        org_id=org_id,
        facility_id=fac_a2.facility_id,
        material_type="aluminum-scrap",
        quantity=10000.0,
        unit="kg",
        status="available",
        availability_from=date(2026, 11, 1),
    )

    # Lots for Zone B: 3 facilities, heavy generation (200 tonnes total vs 75 tonnes capacity -> DEFICIT)
    lot_b1 = MaterialLot(
        org_id=org_id,
        facility_id=fac_b1.facility_id,
        material_type="cotton-blend-offcuts",
        quantity=80000.0,
        unit="kg",
        status="available",
        availability_from=date(2026, 11, 1),
    )
    lot_b2 = MaterialLot(
        org_id=org_id,
        facility_id=fac_b2.facility_id,
        material_type="cotton-blend-offcuts",
        quantity=70000.0,
        unit="kg",
        status="shipped",
        availability_from=date(2026, 11, 1),
    )
    lot_b3 = MaterialLot(
        org_id=org_id,
        facility_id=fac_b3.facility_id,
        material_type="cotton-blend-offcuts",
        quantity=50000.0,
        unit="kg",
        status="verified_recovered",
        availability_from=date(2026, 11, 1),
        declared_attributes={"verified_recovered": True},
    )

    # Lots for Zone C: light generation (10 tonnes total vs 1200 tonnes capacity -> SURPLUS)
    lot_c1 = MaterialLot(
        org_id=org_id,
        facility_id=fac_c1.facility_id,
        material_type="spent-isopropanol",
        quantity=10000.0,
        unit="kg",
        status="available",
        availability_from=date(2026, 11, 1),
    )

    db_session.add_all([lot_a1, lot_a2, lot_b1, lot_b2, lot_b3, lot_c1])
    db_session.flush()

    # Add active listing for lot_b1 (80 tonnes offered)
    listing_b1 = Listing(
        material_lot_id=lot_b1.lot_id,
        organization_id=org_id,
        facility_id=fac_b1.facility_id,
        visibility=ListingVisibility.PUBLIC,
        asking_price_per_unit=50.0,
        currency="INR",
        available_quantity=80000.0,
        unit="kg",
        status=ListingStatus.ACTIVE,
    )

    db_session.add(listing_b1)
    db_session.flush()

    return {
        "city_id": city_id,
        "org_id": org_id,
        "fac_a": [fac_a1, fac_a2],
        "fac_b": [fac_b1, fac_b2, fac_b3],
        "fac_c": [fac_c1, fac_c2, fac_c3],
    }


class TestMunicipalIntelligenceEngine:
    def test_cohort_suppression_under_three_facilities(self, db_session, municipal_test_data):
        """Zone with fewer than 3 facilities masks metrics and suppresses cohort numbers."""
        city_id = municipal_test_data["city_id"]
        engine = MunicipalIntelligenceEngine(db_session)

        report = engine.get_aggregate_material_flows(city_id=city_id, zone_id="zone-a")

        assert report.city_id == city_id
        assert report.zone_id == "zone-a"
        assert report.cohort_suppressed is True
        assert report.facility_cohort_count is None
        assert report.flows is None
        assert report.suppression_reason is not None
        assert "fewer than 3" in report.suppression_reason

    def test_aggregate_material_flows_with_valid_cohort(self, db_session, municipal_test_data):
        """Zone with 3+ facilities discloses accurate lifecycle stage volumes without privacy leaks."""
        city_id = municipal_test_data["city_id"]
        engine = MunicipalIntelligenceEngine(db_session)

        report = engine.get_aggregate_material_flows(city_id=city_id, zone_id="zone-b")

        assert report.cohort_suppressed is False
        assert report.facility_cohort_count == 3
        assert report.flows is not None

        # 80t (lot_b1) + 70t (lot_b2) + 50t (lot_b3) = 200 tonnes generated
        assert report.flows.generated_tonnage == 200.0
        # lot_b1 has active listing -> 80 tonnes offered
        assert report.flows.offered_tonnage == 80.0
        # lot_b2 status is shipped -> 70 tonnes shipped
        assert report.flows.shipped_tonnage == 70.0
        # lot_b3 is verified_recovered -> 50 tonnes verified_recovered
        assert report.flows.verified_recovered_tonnage == 50.0
        # Textiles category
        assert report.flows.by_material_category["textiles"] == 200.0
        assert report.provenance == DataProvenanceLabel.REAL_VERIFIED

    def test_material_category_filter(self, db_session, municipal_test_data):
        """Material category filtering accurately scopes aggregate flows."""
        city_id = municipal_test_data["city_id"]
        engine = MunicipalIntelligenceEngine(db_session)

        # Zone B only has textiles
        textiles_report = engine.get_aggregate_material_flows(
            city_id=city_id, zone_id="zone-b", material_category="textiles"
        )
        assert textiles_report.cohort_suppressed is False
        assert textiles_report.flows.generated_tonnage == 200.0

        # Querying metallics in Zone B yields 0 tonnes
        metallics_report = engine.get_aggregate_material_flows(
            city_id=city_id, zone_id="zone-b", material_category="metallics"
        )
        assert metallics_report.cohort_suppressed is False
        assert metallics_report.flows.generated_tonnage == 0.0

    def test_capacity_gap_analysis_classifications(self, db_session, municipal_test_data):
        """Engine correctly classifies DEFICIT_HOTSPOT, SURPLUS_CAPACITY, and SUPPRESSED zones."""
        city_id = municipal_test_data["city_id"]
        engine = MunicipalIntelligenceEngine(db_session)

        gap_report = engine.get_capacity_gap_analysis(city_id=city_id)

        assert gap_report.city_id == city_id
        # Total generation: 15 (Zone A) + 200 (Zone B) + 10 (Zone C) = 225 tonnes
        assert gap_report.total_city_generation == 225.0
        # Total capacity: 110 (Zone A) + 75 (Zone B) + 1200 (Zone C) = 1385 tonnes
        assert gap_report.total_city_capacity == 1385.0
        assert gap_report.net_city_balance == 1160.0

        zones_map = {z.zone_id: z for z in gap_report.zones}

        # Zone A has <3 facilities -> SUPPRESSED
        zone_a = zones_map["zone-a"]
        assert zone_a.cohort_suppressed is True
        assert zone_a.facility_count is None
        assert zone_a.generation_tonnage is None
        assert zone_a.processing_capacity_tonnage is None
        assert zone_a.gap_status == "SUPPRESSED"

        # Zone B has 200t gen vs 75t capacity -> DEFICIT_HOTSPOT
        zone_b = zones_map["zone-b"]
        assert zone_b.cohort_suppressed is False
        assert zone_b.facility_count == 3
        assert zone_b.generation_tonnage == 200.0
        assert zone_b.processing_capacity_tonnage == 75.0
        assert zone_b.net_balance_tonnage == -125.0
        assert zone_b.gap_status == "DEFICIT_HOTSPOT"
        assert "textiles" in zone_b.top_deficit_categories

        # Zone C has 10t gen vs 1200t capacity -> SURPLUS_CAPACITY
        zone_c = zones_map["zone-c"]
        assert zone_c.cohort_suppressed is False
        assert zone_c.facility_count == 3
        assert zone_c.generation_tonnage == 10.0
        assert zone_c.processing_capacity_tonnage == 1200.0
        assert zone_c.net_balance_tonnage == 1190.0
        assert zone_c.gap_status == "SURPLUS_CAPACITY"

    def test_geographic_indicators_and_masking(self, db_session, municipal_test_data):
        """Geographic summary calculates density while masking sub-threshold zones."""
        city_id = municipal_test_data["city_id"]
        engine = MunicipalIntelligenceEngine(db_session)

        geo_summary = engine.get_geographic_indicators(city_id=city_id)

        assert geo_summary.city_id == city_id
        assert geo_summary.total_active_zones == 3
        assert geo_summary.total_city_facilities == 8
        assert geo_summary.total_city_tonnage == 225.0
        assert "textiles" in geo_summary.city_tonnage_by_category

        zones_map = {z.zone_id: z for z in geo_summary.zones}
        assert zones_map["zone-a"].cohort_suppressed is True
        assert zones_map["zone-a"].active_facility_count is None
        assert zones_map["zone-a"].total_tonnage is None

        assert zones_map["zone-b"].cohort_suppressed is False
        assert zones_map["zone-b"].active_facility_count == 3
        assert zones_map["zone-b"].total_tonnage == 200.0
        assert "textiles" in zones_map["zone-b"].top_categories
