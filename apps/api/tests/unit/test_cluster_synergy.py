from datetime import date
import uuid
import pytest

from strata.core.errors import ResourceNotFoundError
from strata.domain.marketplace.cluster import ClusterSynergyEngine
from strata.domain.marketplace.models import BuyerRequirement, Listing
from strata.domain.marketplace.repository import MarketplaceRepository
from strata.domain.marketplace.schemas import ListingStatus, ListingVisibility
from strata.domain.materials.models import Facility, MaterialLot, Organization


@pytest.fixture
def test_cluster_data(db_session):
    cluster_id = "test-cluster-surat-textiles"
    buyer_org_id = str(uuid.uuid4())
    seller_org_1 = str(uuid.uuid4())
    seller_org_2 = str(uuid.uuid4())

    # Create Organizations
    for oid, name in [(buyer_org_id, "Buyer Mills"), (seller_org_1, "Spinning Mill Alpha"), (seller_org_2, "Weaving Mill Beta")]:
        db_session.add(Organization(org_id=oid, name=name))
    db_session.flush()

    # Create Facilities
    fac_buyer = Facility(facility_id=str(uuid.uuid4()), org_id=buyer_org_id, name="Buyer Central Processing", cluster_id=cluster_id)
    fac_seller_1 = Facility(facility_id=str(uuid.uuid4()), org_id=seller_org_1, name="Alpha Plant 1", cluster_id=cluster_id)
    fac_seller_2 = Facility(facility_id=str(uuid.uuid4()), org_id=seller_org_2, name="Beta Plant 2", cluster_id=cluster_id)
    db_session.add_all([fac_buyer, fac_seller_1, fac_seller_2])
    db_session.flush()

    repo = MarketplaceRepository(db_session)

    # Buyer Requirement: 500 kg of textiles (cotton blend), min_quantity=500, max_quantity=1200
    requirement = BuyerRequirement(
        organization_id=buyer_org_id,
        facility_id=fac_buyer.facility_id,
        material_category="textiles",
        min_quantity=500.0,
        max_quantity=1200.0,
        unit="kg",
        required_properties={"fiber": "cotton"},
        prohibited_conditions=["pvc", "moisture_gt_15"],
        visibility=ListingVisibility.CLUSTER_ONLY,
    )
    repo.add_requirement(requirement)

    # Lot 1: 200 kg cotton yarn scrap (Alpha, 80% cotton, 20% poly, moisture 8.0%, form=yarn)
    lot1 = MaterialLot(
        org_id=seller_org_1,
        facility_id=fac_seller_1.facility_id,
        material_type="cotton-blend-offcuts",
        quantity=200.0,
        unit="kg",
        status="available",
        availability_from=date(2026, 11, 1),
        declared_attributes={
            "cotton_pct": 80.0,
            "polyester_pct": 20.0,
            "moisture_pct": 8.0,
            "fibre_blend": {"cotton": 80.0, "polyester": 20.0},
            "physical_form": "yarn",
        },
    )
    # Lot 2: 350 kg cotton yarn scrap (Beta, 60% cotton, 40% poly, moisture 14.5%, form=yarn)
    lot2 = MaterialLot(
        org_id=seller_org_2,
        facility_id=fac_seller_2.facility_id,
        material_type="cotton-blend-offcuts",
        quantity=350.0,
        unit="kg",
        status="available",
        availability_from=date(2026, 11, 1),
        declared_attributes={
            "cotton_pct": 60.0,
            "polyester_pct": 40.0,
            "moisture_pct": 14.5,
            "fibre_blend": {"cotton": 60.0, "polyester": 40.0},
            "physical_form": "yarn",
        },
    )
    # Lot 3: Contaminated with PVC (should be rejected by prohibited_conditions)
    lot3 = MaterialLot(
        org_id=seller_org_1,
        facility_id=fac_seller_1.facility_id,
        material_type="cotton-blend-offcuts",
        quantity=400.0,
        unit="kg",
        status="available",
        availability_from=date(2026, 11, 1),
        declared_attributes={"pvc": True, "moisture_pct": 7.0, "physical_form": "yarn"},
    )
    # Lot 4: High moisture (moisture_pct = 18.0 > 15 -> should be rejected by moisture_gt_15)
    lot4 = MaterialLot(
        org_id=seller_org_2,
        facility_id=fac_seller_2.facility_id,
        material_type="cotton-blend-offcuts",
        quantity=600.0,
        unit="kg",
        status="available",
        availability_from=date(2026, 11, 1),
        declared_attributes={"moisture_pct": 18.0, "physical_form": "yarn"},
    )
    # Lot 5: Different material category (metallics / aluminum scrap -> should be rejected by category)
    lot5 = MaterialLot(
        org_id=seller_org_1,
        facility_id=fac_seller_1.facility_id,
        material_type="aluminum-scrap",
        quantity=1000.0,
        unit="kg",
        status="available",
        availability_from=date(2026, 11, 1),
        declared_attributes={},
    )
    # Lot 6: Buyer's own lot (should be excluded by multi-tenant boundary)
    lot6 = MaterialLot(
        org_id=buyer_org_id,
        facility_id=fac_buyer.facility_id,
        material_type="cotton-yarn-scrap",
        quantity=500.0,
        unit="kg",
        status="available",
        availability_from=date(2026, 11, 1),
        declared_attributes={},
    )

    db_session.add_all([lot1, lot2, lot3, lot4, lot5, lot6])
    db_session.flush()

    # Create active listings for all lots
    for lot in [lot1, lot2, lot3, lot4, lot5, lot6]:
        listing = Listing(
            material_lot_id=lot.lot_id,
            organization_id=lot.org_id,
            facility_id=lot.facility_id,
            visibility=ListingVisibility.CLUSTER_ONLY,
            asking_price_per_unit=50.0,
            currency="USD",
            available_quantity=lot.quantity,
            unit=lot.unit,
            status=ListingStatus.ACTIVE,
        )
        repo.add_listing(listing)

    return {
        "cluster_id": cluster_id,
        "requirement_id": requirement.id,
        "buyer_facility_id": fac_buyer.facility_id,
        "lot1_id": lot1.lot_id,
        "lot2_id": lot2.lot_id,
        "lot3_id": lot3.lot_id,
        "lot4_id": lot4.lot_id,
        "lot5_id": lot5.lot_id,
        "lot6_id": lot6.lot_id,
    }


class TestClusterSynergyEngine:
    def test_find_compatible_lots_filtering(self, db_session, test_cluster_data):
        engine = ClusterSynergyEngine(db_session)
        compatible = engine.find_compatible_lots(
            requirement_id=test_cluster_data["requirement_id"],
            cluster_id=test_cluster_data["cluster_id"],
        )

        compatible_ids = {l.lot_id for l in compatible}

        # Lot 1 (valid cotton yarn) and Lot 2 (valid cotton yarn) must be included
        assert test_cluster_data["lot1_id"] in compatible_ids
        assert test_cluster_data["lot2_id"] in compatible_ids

        # Lot 3 (PVC prohibited condition) must be excluded
        assert test_cluster_data["lot3_id"] not in compatible_ids

        # Lot 4 (moisture 18% > 15% prohibited) must be excluded
        assert test_cluster_data["lot4_id"] not in compatible_ids

        # Lot 5 (aluminum metallics) must be excluded
        assert test_cluster_data["lot5_id"] not in compatible_ids

        # Lot 6 (buyer's own lot) must be excluded
        assert test_cluster_data["lot6_id"] not in compatible_ids

    def test_batch_aggregation_proposals_calculation(self, db_session, test_cluster_data):
        engine = ClusterSynergyEngine(db_session)
        proposals = engine.generate_aggregation_proposals(
            requirement_id=test_cluster_data["requirement_id"],
            cluster_id=test_cluster_data["cluster_id"],
            max_lots_per_batch=5,
        )

        # Neither Lot 1 (200kg) nor Lot 2 (350kg) alone meets min_quantity (500kg).
        # But together (200 + 350 = 550kg), they satisfy min_quantity!
        assert len(proposals) >= 1
        prop = proposals[0]

        assert prop.total_quantity == 550.0
        assert prop.unit == "kg"
        assert prop.target_min_quantity == 500.0
        assert len(prop.lots) == 2

        # Check composite attributes: weighted averages
        # Weighted cotton: (200 * 80 + 350 * 60) / 550 = (16000 + 21000) / 550 = 37000 / 550 ≈ 67.27%
        assert "cotton_pct" in prop.composite_attributes
        assert pytest.approx(prop.composite_attributes["cotton_pct"], rel=1e-2) == 67.27

        # Weighted moisture: (200 * 8.0 + 350 * 14.5) / 550 = (1600 + 5075) / 550 = 6675 / 550 ≈ 12.14%
        assert "moisture_pct" in prop.composite_attributes
        assert pytest.approx(prop.composite_attributes["moisture_pct"], rel=1e-2) == 12.14

        # Fiber blend dict weighted averages
        assert "fibre_blend" in prop.composite_attributes
        assert pytest.approx(prop.composite_attributes["fibre_blend"]["cotton"], rel=1e-2) == 67.27
        assert pytest.approx(prop.composite_attributes["fibre_blend"]["polyester"], rel=1e-2) == 32.73

        # Quality variance warnings: moisture spread is 14.5 - 8.0 = 6.5% (> 5%), so a warning must be emitted
        assert len(prop.quality_variance_warnings) > 0
        assert any("moisture_pct" in w for w in prop.quality_variance_warnings)

    def test_aggregation_does_not_mutate_underlying_db_records(self, db_session, test_cluster_data):
        engine = ClusterSynergyEngine(db_session)
        lot1_before = db_session.get(MaterialLot, test_cluster_data["lot1_id"])
        qty_before = lot1_before.quantity
        status_before = lot1_before.status

        # Generate proposals
        engine.generate_aggregation_proposals(
            requirement_id=test_cluster_data["requirement_id"],
            cluster_id=test_cluster_data["cluster_id"],
        )

        db_session.expire_all()
        lot1_after = db_session.get(MaterialLot, test_cluster_data["lot1_id"])
        assert lot1_after.quantity == qty_before
        assert lot1_after.status == status_before

    def test_calculate_indicative_logistics(self, db_session, test_cluster_data):
        engine = ClusterSynergyEngine(db_session)
        lot_ids = [test_cluster_data["lot1_id"], test_cluster_data["lot2_id"]]

        estimate = engine.calculate_indicative_logistics(
            lot_ids=lot_ids,
            destination_facility_id=test_cluster_data["buyer_facility_id"],
            rate_per_km_tonne=12.5,
        )

        # Total tonnage: 200kg + 350kg = 550kg = 0.55 tonnes
        assert estimate.total_tonnage == 0.55

        # 2 distinct facilities: (2 - 1) * 30.0 + 45.0 = 75.0 km
        assert estimate.total_distance_km == 75.0

        # Cost: 0.55 * 75.0 * 12.5 = 515.625 ≈ 515.62 INR
        assert estimate.estimated_transport_cost_inr == 515.62

        # Emissions: 0.55 * 75.0 * 0.105 = 4.33 kg CO2e
        assert estimate.estimated_transport_emissions_kg_co2e == 4.33
        assert estimate.currency == "INR"

    def test_calculate_indicative_logistics_missing_lot_raises_404(self, db_session, test_cluster_data):
        engine = ClusterSynergyEngine(db_session)
        with pytest.raises(ResourceNotFoundError):
            engine.calculate_indicative_logistics(
                lot_ids=["non-existent-lot-uuid"],
                destination_facility_id=test_cluster_data["buyer_facility_id"],
            )

    def test_get_cluster_indicators(self, db_session, test_cluster_data):
        engine = ClusterSynergyEngine(db_session)
        summary = engine.get_cluster_indicators(test_cluster_data["cluster_id"])

        assert summary.cluster_id == test_cluster_data["cluster_id"]
        assert summary.active_listings_count == 6
        # Total tonnage: 200 + 350 + 400 + 600 + 1000 + 500 = 3050 kg = 3.05 tonnes
        assert summary.total_available_tonnage == 3.05
        assert "textiles" in summary.tonnage_by_category
        assert "metallics" in summary.tonnage_by_category
        assert summary.potential_aggregation_opportunities >= 1
