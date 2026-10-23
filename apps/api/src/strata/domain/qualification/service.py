import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.orm import Session

from strata.core.errors import ResourceNotFoundError, ValidationError
from strata.domain.materials.models import MaterialLot
from strata.domain.materials.taxonomy import get_material_type
from strata.domain.qualification.models import (
    EvidenceRecord,
    Investigation,
    QualificationAssessment,
)
from strata.domain.qualification.routes import (
    CandidateRoute,
    RouteGateSpec,
    get_candidate_route_by_id,
    get_candidate_routes_for_material,
)
from strata.integrations.discovery import DiscoveryProvider, FakeDiscoveryProvider
from strata.integrations.llm import FakeLLMProvider, LLMProvider
from strata.schemas.evidence import (
    EvidenceProvenance,
    EvidenceRecordCreate,
    EvidenceRecordRead,
    EvidenceVerificationState,
    ExtractionMethod,
)
from strata.schemas.qualification import (
    HardGateResult,
    InvestigationExecutionStatus,
    InvestigationRead,
    MissingFact,
    QualificationAssessmentRead,
    QualificationOutcome,
)


class ProofPathQualificationEngine:
    """
    Authoritative deterministic evaluation engine for ProofPath.
    Evaluates candidate circularity routes against physical material lots.
    Rules:
    - Hard gate failure always produces UNSUPPORTED (inviolable block).
    - Missing critical facts produce CONDITIONAL.
    - All hard gates pass + all required facts verified produces SUPPORTED.
    - LLMs provide advisory commentary only and cannot evaluate eligibility or invent facts.
    """

    RULE_VERSION = "1.0.0"

    def __init__(self, llm_provider: Optional[LLMProvider] = None) -> None:
        self.llm = llm_provider or FakeLLMProvider()

    def evaluate(
        self,
        lot: MaterialLot,
        route: CandidateRoute,
        evidence_records: List[EvidenceRecord],
    ) -> QualificationAssessmentRead:
        """Deterministically evaluates a material lot against a candidate route specification."""
        gate_results: List[HardGateResult] = []
        blocking_conditions: List[str] = []
        missing_facts: List[MissingFact] = []
        evidence_refs: List[str] = [e.evidence_id for e in evidence_records]

        taxonomy_info = get_material_type(lot.material_type)
        is_hazardous_material = taxonomy_info.is_hazardous if taxonomy_info else False
        declared_attrs: Dict[str, Any] = lot.declared_attributes or {}

        # 1. Check for contradicted evidence (conflicting evidence check)
        contradicted_evidence = [
            e for e in evidence_records
            if e.verification_state == EvidenceVerificationState.CONTRADICTED.value
            or len(e.contradicted_by or []) > 0
        ]
        if contradicted_evidence:
            subjects = {e.claim_subject for e in contradicted_evidence}
            blocking_conditions.append(
                f"Conflicting or contradicted evidence detected for: {', '.join(sorted(subjects))}."
            )

        # 2. Evaluate each explicit hard gate deterministically
        for gate in route.hard_gates:
            outcome, mat_val = self._evaluate_gate(
                gate=gate,
                lot=lot,
                declared_attrs=declared_attrs,
                is_hazardous_material=is_hazardous_material,
                evidence_records=evidence_records,
            )

            is_blocking = (outcome == "fail")
            gate_results.append(
                HardGateResult(
                    gate_id=gate.gate_id,
                    gate_name=gate.name,
                    outcome=outcome,
                    material_value=mat_val,
                    required_value=gate.threshold_value,
                    blocking=is_blocking,
                )
            )

            if outcome == "fail":
                blocking_conditions.append(
                    f"Gate '{gate.name}' failed: material value {mat_val} violates requirement {gate.threshold_value}."
                )
            elif outcome == "unknown":
                missing_facts.append(
                    MissingFact(
                        fact_id=f"fact-for-{gate.gate_id}",
                        description=f"Specification required to evaluate '{gate.name}': {gate.description}",
                        acquisition_method="lab_test" if "contamination" in gate.field_name or "moisture" in gate.field_name else "document",
                        is_critical=True,
                    )
                )

        # 3. Evaluate required facts from route specifications
        for req_fact in route.required_facts:
            has_fact = self._has_fact_evidence(req_fact.fact_id, declared_attrs, evidence_records)
            if not has_fact:
                missing_facts.append(
                    MissingFact(
                        fact_id=req_fact.fact_id,
                        description=req_fact.description,
                        acquisition_method=req_fact.acquisition_method,
                        is_critical=req_fact.is_critical,
                    )
                )

        # 4. Determine authoritative qualification outcome
        if blocking_conditions or any(g.outcome == "fail" for g in gate_results):
            status = QualificationOutcome.UNSUPPORTED
        elif missing_facts or any(g.outcome == "unknown" for g in gate_results):
            status = QualificationOutcome.CONDITIONAL
        else:
            status = QualificationOutcome.SUPPORTED

        passed_gates = [g.gate_name for g in gate_results if g.outcome == "pass"]
        missing_fact_desc = [f.description for f in missing_facts]

        # 5. Synthesize audit rationale and next action (via advisory LLM interface)
        rationale = self.llm.synthesize_explanation(
            route_name=route.name,
            status=status.value,
            passed_gates=passed_gates,
            blocking_conditions=blocking_conditions,
            missing_facts=missing_fact_desc,
        )
        next_action = self.llm.suggest_next_action(
            status=status.value,
            blocking_conditions=blocking_conditions,
            missing_facts=missing_fact_desc,
        )

        return QualificationAssessmentRead(
            assessment_id=str(uuid.uuid4()),
            lot_id=lot.lot_id,
            candidate_route_id=route.route_id,
            status=status,
            hard_gate_results=gate_results,
            blocking_conditions=blocking_conditions,
            missing_facts=missing_facts,
            rationale=rationale,
            next_action=next_action,
            evidence_refs=evidence_refs,
            rule_version=self.RULE_VERSION,
            assessed_at=datetime.now(timezone.utc),
        )

    def _evaluate_gate(
        self,
        gate: RouteGateSpec,
        lot: MaterialLot,
        declared_attrs: Dict[str, Any],
        is_hazardous_material: bool,
        evidence_records: List[EvidenceRecord],
    ) -> Tuple[str, Any]:
        """Evaluates an individual gate spec returning (outcome: pass/fail/unknown, observed_value)."""
        field_name = gate.field_name

        if gate.rule_type == "boolean_check":
            observed = declared_attrs.get(field_name, is_hazardous_material if field_name == "is_hazardous" else None)
            if observed is None:
                return "unknown", None
            return ("pass" if observed == gate.threshold_value else "fail"), observed

        elif gate.rule_type == "max_threshold":
            observed = declared_attrs.get(field_name)
            # Check if evidence provides the value
            if observed is None:
                for ev in evidence_records:
                    if ev.claim_subject == field_name and ev.verification_state != EvidenceVerificationState.CONTRADICTED.value:
                        try:
                            observed = float(ev.claim_text.split()[0])
                            break
                        except (ValueError, IndexError):
                            pass
            if observed is None:
                return "unknown", None
            try:
                numeric_val = float(observed)
                threshold = float(gate.threshold_value)
                return ("pass" if numeric_val <= threshold else "fail"), numeric_val
            except (ValueError, TypeError):
                return "unknown", observed

        elif gate.rule_type == "min_threshold":
            if field_name == "quantity":
                observed = lot.quantity
            else:
                observed = declared_attrs.get(field_name)
            if observed is None:
                return "unknown", None
            try:
                numeric_val = float(observed)
                threshold = float(gate.threshold_value)
                return ("pass" if numeric_val >= threshold else "fail"), numeric_val
            except (ValueError, TypeError):
                return "unknown", observed

        elif gate.rule_type == "prohibited_values":
            contaminants = declared_attrs.get(field_name, declared_attrs.get("contaminants", []))
            if isinstance(contaminants, str):
                contaminants = [c.strip().lower() for c in contaminants.split(",")]
            elif isinstance(contaminants, list):
                contaminants = [str(c).strip().lower() for c in contaminants]
            else:
                contaminants = []

            prohibited = [str(p).strip().lower() for p in gate.threshold_value]
            violations = [c for c in contaminants if c in prohibited]
            if violations:
                return "fail", violations
            return "pass", contaminants

        return "unknown", None

    def _has_fact_evidence(
        self,
        fact_id: str,
        declared_attrs: Dict[str, Any],
        evidence_records: List[EvidenceRecord],
    ) -> bool:
        """Determines whether a required fact is verified in the lot attributes or evidence records."""
        # Check declared attributes
        normalized_key = fact_id.replace("fact-", "").replace("-", "_")
        for key in declared_attrs.keys():
            if normalized_key in key.lower():
                return True

        # Check evidence records
        for ev in evidence_records:
            if ev.verification_state == EvidenceVerificationState.CONTRADICTED.value:
                continue
            if normalized_key in ev.claim_subject.lower() or normalized_key in ev.claim_text.lower():
                return True

        return False


class ProofPathQualificationService:
    """Application service coordinating investigations, evidence, and qualification runs."""

    def __init__(
        self,
        db: Session,
        engine: Optional[ProofPathQualificationEngine] = None,
        discovery_provider: Optional[DiscoveryProvider] = None,
    ) -> None:
        self.db = db
        self.engine = engine or ProofPathQualificationEngine()
        self.discovery = discovery_provider or FakeDiscoveryProvider()

    def add_evidence(self, payload: EvidenceRecordCreate, org_id: str) -> EvidenceRecordRead:
        """Persists a new evidence claim linked to a tenant organization and optional material lot."""
        record = EvidenceRecord(
            evidence_id=str(uuid.uuid4()),
            org_id=org_id,
            lot_id=payload.lot_id,
            claim_subject=payload.claim_subject,
            claim_text=payload.claim_text,
            source_url=payload.source_url,
            source_title=payload.source_title,
            source_type=payload.source_type,
            retrieved_at=payload.retrieved_at or datetime.now(timezone.utc),
            extraction_method=payload.extraction_method.value,
            provenance=payload.provenance.value,
            verification_state=payload.verification_state.value,
            supporting_passage=payload.supporting_passage,
            content_hash=payload.content_hash,
            document_ref=payload.document_ref,
            verified_by=payload.verified_by,
            contradicted_by=[],
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return EvidenceRecordRead.model_validate(record)

    def get_evidence_for_lot(self, lot_id: str, org_id: str) -> List[EvidenceRecordRead]:
        """Lists all evidence records associated with a specific material lot."""
        stmt = select(EvidenceRecord).where(
            EvidenceRecord.lot_id == lot_id,
            EvidenceRecord.org_id == org_id,
        ).order_by(EvidenceRecord.retrieved_at.desc())
        records = self.db.execute(stmt).scalars().all()
        return [EvidenceRecordRead.model_validate(r) for r in records]

    def run_investigation(
        self,
        lot_id: str,
        org_id: str,
        candidate_route_ids: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> InvestigationRead:
        """
        Executes a qualification investigation: gathers evidence, identifies candidate routes,
        evaluates deterministic criteria, and persists audit assessments.
        """
        # 1. Fetch material lot within tenant scope
        lot_stmt = select(MaterialLot).where(
            MaterialLot.lot_id == lot_id,
            MaterialLot.org_id == org_id,
        )
        lot = self.db.execute(lot_stmt).scalar_one_or_none()
        if not lot:
            raise ResourceNotFoundError(
                f"Material lot '{lot_id}' was not found in your organization scope.",
                details={"lot_id": lot_id},
            )

        # 2. Gather existing evidence records for this lot
        ev_stmt = select(EvidenceRecord).where(
            EvidenceRecord.lot_id == lot_id,
            EvidenceRecord.org_id == org_id,
        )
        evidence_records = list(self.db.execute(ev_stmt).scalars().all())

        # 3. Determine candidate routes
        if candidate_route_ids:
            routes = []
            for r_id in candidate_route_ids:
                r = get_candidate_route_by_id(r_id)
                if r:
                    routes.append(r)
        else:
            routes = self.discovery.discover_routes(lot.material_type)

        # 4. Create Investigation entity
        investigation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        inv = Investigation(
            investigation_id=investigation_id,
            org_id=org_id,
            lot_id=lot_id,
            status=InvestigationExecutionStatus.COMPLETED.value,
            notes=notes,
            created_at=now,
            completed_at=now,
        )
        self.db.add(inv)
        self.db.flush()

        # 5. Evaluate each route deterministically
        assessment_models: List[QualificationAssessmentRead] = []
        for route in routes:
            assessment_read = self.engine.evaluate(
                lot=lot,
                route=route,
                evidence_records=evidence_records,
            )
            assessment_models.append(assessment_read)

            qa_entity = QualificationAssessment(
                assessment_id=assessment_read.assessment_id,
                investigation_id=investigation_id,
                lot_id=lot_id,
                candidate_route_id=route.route_id,
                status=assessment_read.status.value,
                hard_gate_results=[g.model_dump() for g in assessment_read.hard_gate_results],
                blocking_conditions=assessment_read.blocking_conditions,
                missing_facts=[f.model_dump() for f in assessment_read.missing_facts],
                rationale=assessment_read.rationale,
                next_action=assessment_read.next_action,
                evidence_refs=assessment_read.evidence_refs,
                rule_version=assessment_read.rule_version,
                assessed_at=assessment_read.assessed_at,
            )
            self.db.add(qa_entity)

        self.db.commit()
        self.db.refresh(inv)

        return InvestigationRead(
            investigation_id=inv.investigation_id,
            org_id=inv.org_id,
            lot_id=inv.lot_id,
            status=InvestigationExecutionStatus(inv.status),
            assessments=assessment_models,
            error_message=inv.error_message,
            created_at=inv.created_at,
            completed_at=inv.completed_at,
        )

    def get_investigation(self, investigation_id: str, org_id: str) -> InvestigationRead:
        """Retrieves an investigation run and its associated assessments."""
        stmt = select(Investigation).where(
            Investigation.investigation_id == investigation_id,
            Investigation.org_id == org_id,
        )
        inv = self.db.execute(stmt).scalar_one_or_none()
        if not inv:
            raise ResourceNotFoundError(
                f"Investigation with ID '{investigation_id}' was not found in your organization scope.",
                details={"investigation_id": investigation_id},
            )

        qa_stmt = select(QualificationAssessment).where(
            QualificationAssessment.investigation_id == investigation_id
        )
        qa_entities = self.db.execute(qa_stmt).scalars().all()
        assessments = [
            QualificationAssessmentRead(
                assessment_id=qa.assessment_id,
                lot_id=qa.lot_id,
                candidate_route_id=qa.candidate_route_id,
                status=QualificationOutcome(qa.status),
                hard_gate_results=[HardGateResult(**g) for g in qa.hard_gate_results],
                blocking_conditions=qa.blocking_conditions,
                missing_facts=[MissingFact(**f) for f in qa.missing_facts],
                rationale=qa.rationale,
                next_action=qa.next_action,
                evidence_refs=qa.evidence_refs,
                rule_version=qa.rule_version,
                assessed_at=qa.assessed_at,
            )
            for qa in qa_entities
        ]

        return InvestigationRead(
            investigation_id=inv.investigation_id,
            org_id=inv.org_id,
            lot_id=inv.lot_id,
            status=InvestigationExecutionStatus(inv.status),
            assessments=assessments,
            error_message=inv.error_message,
            created_at=inv.created_at,
            completed_at=inv.completed_at,
        )

    def get_route_assessments_for_lot(self, lot_id: str, org_id: str) -> List[QualificationAssessmentRead]:
        """Retrieves all latest qualification assessments recorded for a material lot."""
        # Ensure lot belongs to tenant
        lot_stmt = select(MaterialLot).where(
            MaterialLot.lot_id == lot_id,
            MaterialLot.org_id == org_id,
        )
        lot = self.db.execute(lot_stmt).scalar_one_or_none()
        if not lot:
            raise ResourceNotFoundError(
                f"Material lot '{lot_id}' was not found in your organization scope.",
                details={"lot_id": lot_id},
            )

        stmt = select(QualificationAssessment).where(
            QualificationAssessment.lot_id == lot_id
        ).order_by(QualificationAssessment.assessed_at.desc())
        qa_entities = self.db.execute(stmt).scalars().all()

        return [
            QualificationAssessmentRead(
                assessment_id=qa.assessment_id,
                lot_id=qa.lot_id,
                candidate_route_id=qa.candidate_route_id,
                status=QualificationOutcome(qa.status),
                hard_gate_results=[HardGateResult(**g) for g in qa.hard_gate_results],
                blocking_conditions=qa.blocking_conditions,
                missing_facts=[MissingFact(**f) for f in qa.missing_facts],
                rationale=qa.rationale,
                next_action=qa.next_action,
                evidence_refs=qa.evidence_refs,
                rule_version=qa.rule_version,
                assessed_at=qa.assessed_at,
            )
            for qa in qa_entities
        ]
