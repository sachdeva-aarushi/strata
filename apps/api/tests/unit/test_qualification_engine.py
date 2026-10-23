import pytest
from datetime import datetime, timezone

from strata.domain.materials.models import MaterialLot
from strata.domain.qualification.models import EvidenceRecord
from strata.domain.qualification.routes import CANDIDATE_ROUTES
from strata.domain.qualification.service import ProofPathQualificationEngine
from strata.schemas.evidence import (
    EvidenceProvenance,
    EvidenceVerificationState,
    ExtractionMethod,
)
from strata.schemas.qualification import QualificationOutcome


@pytest.fixture
def engine():
    return ProofPathQualificationEngine()


@pytest.fixture
def aluminum_route():
    return CANDIDATE_ROUTES["route-secondary-aluminum-smelter"]


def test_qualification_successful_supported(engine, aluminum_route):
    """
    Verifies that a material lot satisfying all hard constraints and possessing
    verified facts achieves authoritative 'supported' status.
    """
    lot = MaterialLot(
        lot_id="lot-test-supported-001",
        org_id="org-test",
        facility_id="fac-001",
        material_type="aluminum-scrap",
        quantity=2500.0,
        unit="kg",
        status="active",
        declared_attributes={
            "is_hazardous": False,
            "oil_contamination_pct": 0.5,  # Threshold is 1.5% -> passes
            "contaminants": ["dirt"],      # No lead, cadmium, radioactive -> passes
            "alloy_series": "6061",        # Required fact 1 present
        },
    )

    evidence = [
        EvidenceRecord(
            evidence_id="ev-moisture-001",
            org_id="org-test",
            lot_id=lot.lot_id,
            claim_subject="moisture_level",
            claim_text="moisture_level lab assay measured <0.05% moisture content (dry).",
            source_url="https://lab.internal.test/reports/LAB-9921",
            source_title="Certified Lab Moisture Test",
            source_type="lab_report",
            retrieved_at=datetime.now(timezone.utc),
            extraction_method=ExtractionMethod.LAB_TEST.value,
            provenance=EvidenceProvenance.INDEPENDENTLY_VERIFIED.value,
            verification_state=EvidenceVerificationState.VERIFIED.value,
            supporting_passage="Karl-Fischer oven test reveals no detectable surface or bulk moisture.",
            content_hash="sha256-abcdef0123456789",
        )
    ]

    assessment = engine.evaluate(lot=lot, route=aluminum_route, evidence_records=evidence)

    assert assessment.status == QualificationOutcome.SUPPORTED
    assert len(assessment.blocking_conditions) == 0
    assert len(assessment.missing_facts) == 0
    assert assessment.rule_version == "1.0.0"
    assert "route-secondary-aluminum-smelter" == assessment.candidate_route_id
    assert all(gate.outcome == "pass" for gate in assessment.hard_gate_results)


def test_qualification_hard_incompatibility_unsupported(engine, aluminum_route):
    """
    Verifies that a hard gate failure (e.g. prohibited contaminant or excessive oil)
    strictly results in 'unsupported', generating an explicit blocking condition.
    """
    lot = MaterialLot(
        lot_id="lot-test-incompatible-002",
        org_id="org-test",
        facility_id="fac-001",
        material_type="aluminum-scrap",
        quantity=3000.0,
        unit="kg",
        status="active",
        declared_attributes={
            "is_hazardous": False,
            "oil_contamination_pct": 4.8,  # Exceeds max 1.5%
            "contaminants": ["lead", "dirt"],  # Contains prohibited 'lead'
            "alloy_series": "6061",
        },
    )

    assessment = engine.evaluate(lot=lot, route=aluminum_route, evidence_records=[])

    assert assessment.status == QualificationOutcome.UNSUPPORTED
    assert len(assessment.blocking_conditions) >= 2
    # Oil gate failed
    assert any("oil" in cond.lower() for cond in assessment.blocking_conditions)
    # Prohibited metals gate failed
    assert any("prohibited" in cond.lower() or "lead" in cond.lower() for cond in assessment.blocking_conditions)
    assert any(gate.outcome == "fail" and gate.blocking for gate in assessment.hard_gate_results)


def test_qualification_missing_critical_facts_conditional(engine, aluminum_route):
    """
    Verifies that when hard constraints are not violated but critical facts
    (e.g., moisture test, alloy series) are missing, status is strictly 'conditional'.
    """
    lot = MaterialLot(
        lot_id="lot-test-conditional-003",
        org_id="org-test",
        facility_id="fac-001",
        material_type="aluminum-scrap",
        quantity=1500.0,
        unit="kg",
        status="active",
        declared_attributes={
            "is_hazardous": False,
            "oil_contamination_pct": 0.8,
            "contaminants": [],
            # Missing alloy_series and moisture test
        },
    )

    assessment = engine.evaluate(lot=lot, route=aluminum_route, evidence_records=[])

    assert assessment.status == QualificationOutcome.CONDITIONAL
    assert len(assessment.blocking_conditions) == 0  # No hard gate failed
    assert len(assessment.missing_facts) >= 2
    fact_ids = [f.fact_id for f in assessment.missing_facts]
    assert "fact-alloy-series" in fact_ids
    assert "fact-moisture-level" in fact_ids


def test_qualification_conflicting_or_contradicted_evidence(engine, aluminum_route):
    """
    Verifies that if evidence on a lot is contradicted or conflicting,
    the qualification engine flags a blocking condition and prevents 'supported'.
    """
    lot = MaterialLot(
        lot_id="lot-test-conflict-004",
        org_id="org-test",
        facility_id="fac-001",
        material_type="aluminum-scrap",
        quantity=2000.0,
        unit="kg",
        status="active",
        declared_attributes={
            "is_hazardous": False,
            "oil_contamination_pct": 0.5,
            "contaminants": [],
            "alloy_series": "6061",
        },
    )

    # Moisture evidence is marked as contradicted by an opposing lab check
    contradicted_evidence = [
        EvidenceRecord(
            evidence_id="ev-moisture-conflict",
            org_id="org-test",
            lot_id=lot.lot_id,
            claim_subject="moisture_level",
            claim_text="moisture_level under 0.05%",
            source_url="https://supplier.internal/cert-1",
            source_title="Supplier Quality Certificate",
            source_type="certificate",
            retrieved_at=datetime.now(timezone.utc),
            extraction_method=ExtractionMethod.USER_UPLOAD.value,
            provenance=EvidenceProvenance.USER_REPORTED.value,
            verification_state=EvidenceVerificationState.CONTRADICTED.value,
            contradicted_by=["ev-lab-retest-fail"],
        )
    ]

    assessment = engine.evaluate(lot=lot, route=aluminum_route, evidence_records=contradicted_evidence)

    # Must not be supported due to conflicting evidence and missing verified moisture
    assert assessment.status in (QualificationOutcome.UNSUPPORTED, QualificationOutcome.CONDITIONAL)
    assert any("conflicting" in cond.lower() or "contradicted" in cond.lower() for cond in assessment.blocking_conditions)


def test_qualification_deterministic_reproducibility(engine, aluminum_route):
    """
    Verifies that evaluating the same lot and candidate route multiple times
    is strictly deterministic and yields identical results and rule version.
    """
    lot = MaterialLot(
        lot_id="lot-test-reproduce-005",
        org_id="org-test",
        facility_id="fac-001",
        material_type="aluminum-scrap",
        quantity=1800.0,
        unit="kg",
        status="active",
        declared_attributes={
            "is_hazardous": False,
            "oil_contamination_pct": 1.2,
            "contaminants": ["trace_iron"],
            "alloy_series": "5052",
        },
    )

    assessment_1 = engine.evaluate(lot=lot, route=aluminum_route, evidence_records=[])
    assessment_2 = engine.evaluate(lot=lot, route=aluminum_route, evidence_records=[])

    assert assessment_1.status == assessment_2.status
    assert assessment_1.rule_version == assessment_2.rule_version == "1.0.0"
    assert assessment_1.blocking_conditions == assessment_2.blocking_conditions
    assert [g.outcome for g in assessment_1.hard_gate_results] == [g.outcome for g in assessment_2.hard_gate_results]
    assert [f.fact_id for f in assessment_1.missing_facts] == [f.fact_id for f in assessment_2.missing_facts]
