import uuid
import pytest

from strata.core.errors import DuplicateEventError, InvalidStateTransitionError
from strata.domain.impact.service import ImpactLedgerService
from strata.domain.materials.models import Facility, Organization
from strata.schemas.impact import (
    ImpactRecordCreate,
    LifecycleEventType,
    UncertaintyRating,
    VerificationStatus,
)


@pytest.fixture
def org_and_facility(db_session):
    org_id = str(uuid.uuid4())
    fac_id = str(uuid.uuid4())
    org = Organization(org_id=org_id, name="Impact Test Mills", org_type="processor")
    fac = Facility(facility_id=fac_id, org_id=org_id, name="Impact Processing Depot")
    db_session.add_all([org, fac])
    db_session.flush()
    return {"org_id": org_id, "facility_id": fac_id}


class TestImpactLedgerUnit:
    """Unit test suite for the Verified Impact Ledger and environmental calculations."""

    def test_environmental_impact_factor_calculations(self, db_session):
        """Environmental calculation determines correct avoided landfill mass and CO2e abatement."""
        service = ImpactLedgerService(db_session)

        # 1. Textiles factor: 14.2 kg CO2e / kg
        textiles_calc = service.calculate_environmental_impact(mass_kg=1000.0, material_category="textiles")
        assert textiles_calc.mass_kg == 1000.0
        assert textiles_calc.landfill_avoided_kg == 1000.0
        assert textiles_calc.co2e_avoided_kg == 14200.0
        assert textiles_calc.factor_used == 14.2
        assert textiles_calc.uncertainty_rating == UncertaintyRating.LOW
        assert "WARM" in textiles_calc.factor_source

        # 2. Metallics factor: 8.5 kg CO2e / kg
        metal_calc = service.calculate_environmental_impact(mass_kg=2000.0, material_category="metallics")
        assert metal_calc.landfill_avoided_kg == 2000.0
        assert metal_calc.co2e_avoided_kg == 17000.0
        assert metal_calc.factor_used == 8.5
        assert metal_calc.uncertainty_rating == UncertaintyRating.LOW

        # 3. Chemicals factor: 2.1 kg CO2e / kg
        chem_calc = service.calculate_environmental_impact(mass_kg=500.0, material_category="chemicals")
        assert chem_calc.co2e_avoided_kg == 1050.0
        assert chem_calc.factor_used == 2.1
        assert chem_calc.uncertainty_rating == UncertaintyRating.LOW

        # 4. Unknown / Default category
        unknown_calc = service.calculate_environmental_impact(mass_kg=300.0, material_category="unobtainium")
        assert unknown_calc.co2e_avoided_kg == 300.0
        assert unknown_calc.factor_used == 1.0
        assert unknown_calc.uncertainty_rating == UncertaintyRating.HIGH

    def test_state_ordering_enforcement(self, db_session, org_and_facility):
        """State machine rejects out-of-order lifecycle events."""
        service = ImpactLedgerService(db_session)
        lot_id = f"lot-{uuid.uuid4()}"
        org_id = org_and_facility["org_id"]
        fac_id = org_and_facility["facility_id"]

        # 1. Attempting 'shipped' before 'generated' fails
        with pytest.raises(InvalidStateTransitionError) as exc_shipped:
            service.record_lifecycle_impact_event(
                ImpactRecordCreate(
                    lot_id=lot_id,
                    facility_id=fac_id,
                    event_type="shipped",
                    mass_kg=500.0,
                    displaced_material_category="textiles",
                ),
                actor_org_id=org_id,
            )
        assert "generated" in str(exc_shipped.value)

        # 2. Attempting 'verified_recovered' before 'accepted' or 'processed' fails
        with pytest.raises(InvalidStateTransitionError) as exc_rec:
            service.record_lifecycle_impact_event(
                ImpactRecordCreate(
                    lot_id=lot_id,
                    facility_id=fac_id,
                    event_type="verified_recovered",
                    mass_kg=500.0,
                    displaced_material_category="textiles",
                ),
                actor_org_id=org_id,
            )
        assert "accepted" in str(exc_rec.value)

    def test_double_counting_prevention(self, db_session, org_and_facility):
        """Duplicate event registration for the same lot is strictly blocked."""
        service = ImpactLedgerService(db_session)
        lot_id = f"lot-{uuid.uuid4()}"
        org_id = org_and_facility["org_id"]
        fac_id = org_and_facility["facility_id"]

        payload = ImpactRecordCreate(
            lot_id=lot_id,
            facility_id=fac_id,
            event_type="generated",
            mass_kg=2500.0,
            displaced_material_category="metallics",
        )

        # First recording succeeds
        first_record = service.record_lifecycle_impact_event(payload, actor_org_id=org_id)
        assert first_record.event_type == "generated"
        assert first_record.mass_kg == 2500.0

        # Attempting duplicate 'generated' event raises DuplicateEventError
        with pytest.raises(DuplicateEventError) as exc_dup:
            service.record_lifecycle_impact_event(payload, actor_org_id=org_id)
        assert exc_dup.value.status_code == 409
        assert "Double-counting is strictly prevented" in str(exc_dup.value)

    def test_complete_lifecycle_progression_and_mass_balance(self, db_session, org_and_facility):
        """Full lifecycle event chain records accurately and calculates correct mass balance."""
        service = ImpactLedgerService(db_session)
        lot_id = f"lot-{uuid.uuid4()}"
        org_id = org_and_facility["org_id"]
        fac_id = org_and_facility["facility_id"]
        evidence_uuid = str(uuid.uuid4())

        lifecycle_steps = [
            ("generated", None),
            ("offered", None),
            ("shipped", None),
            ("accepted", None),
            ("processed", None),
            ("verified_recovered", evidence_uuid),
        ]

        for event, ev_id in lifecycle_steps:
            rec = service.record_lifecycle_impact_event(
                ImpactRecordCreate(
                    lot_id=lot_id,
                    facility_id=fac_id,
                    event_type=event,
                    mass_kg=4000.0,
                    displaced_material_category="textiles",
                    evidence_id=ev_id,
                ),
                actor_org_id=org_id,
            )
            assert rec.event_type == event

            if event == "verified_recovered":
                assert rec.verification_status == VerificationStatus.VERIFIED_RECOVERED.value
                assert rec.evidence_id == evidence_uuid

        # Verify Mass Balance Summary
        summary = service.get_mass_balance_and_summary(organization_id=org_id)
        mb = summary.mass_balance

        assert mb.total_generated_kg == 4000.0
        assert mb.total_offered_kg == 4000.0
        assert mb.total_shipped_kg == 4000.0
        assert mb.total_accepted_kg == 4000.0
        assert mb.total_processed_kg == 4000.0
        assert mb.total_verified_recovered_kg == 4000.0
        assert mb.total_landfill_avoided_kg == 4000.0
        # 4000 kg * 14.2 kg CO2e / kg = 56,800.0 kg CO2e
        assert mb.total_co2e_avoided_kg == 56800.0
        assert mb.net_in_pipeline_kg == 0.0
        assert len(summary.records) == 6

    def test_get_supported_methodologies(self, db_session):
        """Retrieves documented factor methodologies."""
        service = ImpactLedgerService(db_session)
        methods = service.get_supported_methodologies()

        assert len(methods) >= 1
        m = methods[0]
        assert m.methodology_version == "v1.0"
        assert "textiles" in m.factors_by_category
        assert m.factors_by_category["textiles"]["factor_kg_co2e_per_kg"] == 14.2
