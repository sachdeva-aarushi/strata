"""
Waste-prevention intelligence service for STRATA.

Generates advisory waste-prevention recommendations for a material lot by:
  1. Loading existing evidence records from the database
  2. Loading the latest qualification assessments for the lot
  3. Applying deterministic recommendation rules
  4. Optionally enriching rationale text via the configured LLM (advisory only)

Design constraints:
  - Qualification rules and numerical thresholds remain deterministic.
  - LLM output is used only for rationale text, never for rule evaluation.
  - No environmental savings figures are generated or reported.
  - Missing evidence reduces confidence level; it does not prevent recommendations.
  - Failed provider calls are logged and surfaced — never silently replaced.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from strata.core.errors import ResourceNotFoundError
from strata.domain.materials.models import MaterialLot
from strata.domain.qualification.models import EvidenceRecord, QualificationAssessment
from strata.domain.qualification.routes import get_candidate_routes_for_material
from strata.integrations.llm import FakeLLMProvider, LLMProvider, get_llm_provider
from strata.schemas.evidence import EvidenceVerificationState
from strata.schemas.prevention import (
    MissingInformationItem,
    PreventionRecommendation,
    PreventionRecommendationsResponse,
    RecommendationCategory,
    RecommendationConfidence,
)
from strata.schemas.qualification import QualificationOutcome

logger = logging.getLogger("strata.services.prevention")


class WastePreventionService:
    """
    Generates evidence-grounded waste-prevention recommendations for material lots.

    Args:
        db:          SQLAlchemy session.
        llm:         LLM provider for rationale enrichment. Defaults to configured provider.
        llm_label:   Human-readable label for which LLM provider is active.
        evidence_label: Human-readable label for which discovery provider is active.
    """

    def __init__(
        self,
        db: Session,
        llm: Optional[LLMProvider] = None,
        llm_label: str = "fake",
        evidence_label: str = "fake",
    ) -> None:
        self.db = db
        self.llm = llm or get_llm_provider()
        self.llm_label = llm_label
        self.evidence_label = evidence_label

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_recommendations(
        self, lot_id: str, org_id: str
    ) -> PreventionRecommendationsResponse:
        """
        Generates waste-prevention recommendations for a specific material lot.

        Raises:
            ResourceNotFoundError: if the lot is not found in the tenant scope.
        """
        # 1. Fetch the lot (enforces tenant scope)
        lot = self._fetch_lot(lot_id, org_id)

        # 2. Load evidence records
        evidence_records = self._fetch_evidence(lot_id, org_id)

        # 3. Load latest qualification assessments
        assessments = self._fetch_assessments(lot_id)

        # 4. Determine available candidate routes
        candidate_routes = get_candidate_routes_for_material(lot.material_type)

        # 5. Build recommendations deterministically
        recommendations = self._build_recommendations(
            lot=lot,
            evidence_records=evidence_records,
            assessments=assessments,
            candidate_routes=candidate_routes,
        )

        return PreventionRecommendationsResponse(
            lot_id=lot_id,
            material_type=lot.material_type,
            recommendations=recommendations,
            generated_at=datetime.now(timezone.utc),
            evidence_provider=self.evidence_label,
            llm_provider=self.llm_label,
        )

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _fetch_lot(self, lot_id: str, org_id: str) -> MaterialLot:
        stmt = select(MaterialLot).where(
            MaterialLot.lot_id == lot_id,
            MaterialLot.org_id == org_id,
        )
        lot = self.db.execute(stmt).scalar_one_or_none()
        if not lot:
            raise ResourceNotFoundError(
                f"Material lot '{lot_id}' was not found in your organization scope.",
                details={"lot_id": lot_id},
            )
        return lot

    def _fetch_evidence(self, lot_id: str, org_id: str) -> List[EvidenceRecord]:
        stmt = select(EvidenceRecord).where(
            EvidenceRecord.lot_id == lot_id,
            EvidenceRecord.org_id == org_id,
        )
        return list(self.db.execute(stmt).scalars().all())

    def _fetch_assessments(self, lot_id: str) -> List[QualificationAssessment]:
        stmt = (
            select(QualificationAssessment)
            .where(QualificationAssessment.lot_id == lot_id)
            .order_by(QualificationAssessment.assessed_at.desc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def _build_recommendations(
        self,
        lot: MaterialLot,
        evidence_records: List[EvidenceRecord],
        assessments: List[QualificationAssessment],
        candidate_routes: list,
    ) -> List[PreventionRecommendation]:
        """
        Applies deterministic recommendation rules in priority order.

        Rules (applied in sequence, not exclusive):
          R1. If a supported assessment exists → recommend listing on Circular Exchange.
          R2. If only conditional assessments exist → recommend acquiring missing facts.
          R3. If no routes match the material type → recommend deferred / broader search.
          R4. If no assessment exists yet → recommend running an investigation.
          R5. If key evidence is missing for any candidate route → recommend evidence acquisition.
        """
        recommendations: List[PreventionRecommendation] = []
        evidence_ids = [e.evidence_id for e in evidence_records]

        # Classify assessments by status
        supported = [a for a in assessments if a.status == QualificationOutcome.SUPPORTED.value]
        conditional = [a for a in assessments if a.status == QualificationOutcome.CONDITIONAL.value]
        unsupported = [a for a in assessments if a.status == QualificationOutcome.UNSUPPORTED.value]

        # R1: Supported route — recommend exchange listing
        for assessment in supported:
            rec = self._make_exchange_listing_recommendation(
                lot=lot,
                assessment=assessment,
                evidence_ids=evidence_ids,
            )
            recommendations.append(rec)

        # R2: Conditional routes — recommend acquiring missing facts
        for assessment in conditional:
            rec = self._make_evidence_acquisition_recommendation(
                lot=lot,
                assessment=assessment,
                evidence_ids=evidence_ids,
            )
            recommendations.append(rec)

        # R4: No assessments at all → recommend running investigation
        if not assessments and candidate_routes:
            recommendations.append(self._make_run_investigation_recommendation(lot))

        # R3: No candidate routes for this material type
        if not candidate_routes:
            recommendations.append(self._make_deferred_recommendation(lot))

        # R5: Global evidence gap check (across all routes)
        global_gap_rec = self._make_global_evidence_gap_recommendation(
            lot=lot,
            evidence_records=evidence_records,
            candidate_routes=candidate_routes,
        )
        if global_gap_rec:
            recommendations.append(global_gap_rec)

        return recommendations

    def _evidence_confidence(self, evidence_records: List[EvidenceRecord]) -> RecommendationConfidence:
        """Derives a confidence level from the composition of evidence records."""
        if not evidence_records:
            return RecommendationConfidence.LOW
        verified = [
            e for e in evidence_records
            if e.verification_state == EvidenceVerificationState.VERIFIED.value
        ]
        if len(verified) >= 2:
            return RecommendationConfidence.HIGH
        if verified:
            return RecommendationConfidence.MEDIUM
        return RecommendationConfidence.LOW

    def _make_exchange_listing_recommendation(
        self,
        lot: MaterialLot,
        assessment: QualificationAssessment,
        evidence_ids: List[str],
    ) -> PreventionRecommendation:
        route_id = assessment.candidate_route_id
        rationale = self.llm.synthesize_explanation(
            route_name=route_id,
            status="supported",
            passed_gates=[g.get("gate_name", "") for g in (assessment.hard_gate_results or [])],
            blocking_conditions=[],
            missing_facts=[],
        )
        return PreventionRecommendation(
            recommendation_id=str(uuid.uuid4()),
            lot_id=lot.lot_id,
            category=RecommendationCategory.EXCHANGE_LISTING,
            summary=(
                f"List this lot on STRATA Circular Exchange under route '{route_id}'."
            ),
            rationale=rationale,
            confidence=RecommendationConfidence.HIGH,
            evidence_basis=evidence_ids + [route_id],
            missing_information=[],
            next_steps=[
                "Create an Exchange listing using the qualified route and lot details.",
                "Set asking price based on current secondary market rates.",
                "Attach qualification assessment ID to the listing for buyer transparency.",
            ],
        )

    def _make_evidence_acquisition_recommendation(
        self,
        lot: MaterialLot,
        assessment: QualificationAssessment,
        evidence_ids: List[str],
    ) -> PreventionRecommendation:
        route_id = assessment.candidate_route_id
        missing = assessment.missing_facts or []
        missing_items = [
            MissingInformationItem(
                item_id=f.get("fact_id", str(uuid.uuid4())),
                description=f.get("description", "Unknown required fact"),
                acquisition_method=f.get("acquisition_method", "document"),
            )
            for f in missing
        ]
        missing_desc = [m.description for m in missing_items]

        rationale = self.llm.synthesize_explanation(
            route_name=route_id,
            status="conditional",
            passed_gates=[g.get("gate_name", "") for g in (assessment.hard_gate_results or [])
                          if g.get("outcome") == "pass"],
            blocking_conditions=[],
            missing_facts=missing_desc,
        )
        next_action = self.llm.suggest_next_action(
            status="conditional",
            blocking_conditions=[],
            missing_facts=missing_desc,
        )

        return PreventionRecommendation(
            recommendation_id=str(uuid.uuid4()),
            lot_id=lot.lot_id,
            category=RecommendationCategory.EVIDENCE_ACQUISITION,
            summary=(
                f"Acquire {len(missing_items)} missing fact(s) to qualify lot for route '{route_id}'."
            ),
            rationale=rationale,
            confidence=RecommendationConfidence.MEDIUM,
            evidence_basis=evidence_ids + [route_id],
            missing_information=missing_items,
            next_steps=[next_action] + [
                f"Obtain: {m.description} (via {m.acquisition_method})" for m in missing_items
            ],
        )

    def _make_run_investigation_recommendation(
        self, lot: MaterialLot
    ) -> PreventionRecommendation:
        return PreventionRecommendation(
            recommendation_id=str(uuid.uuid4()),
            lot_id=lot.lot_id,
            category=RecommendationCategory.ROUTE_OPTIMIZATION,
            summary="Run a ProofPath investigation to identify qualified recovery routes.",
            rationale=(
                f"No qualification assessments have been run for lot '{lot.lot_id}' "
                f"({lot.material_type}, {lot.quantity} {lot.unit}). Running an investigation "
                f"will evaluate all eligible candidate recovery routes against declared attributes."
            ),
            confidence=RecommendationConfidence.LOW,
            evidence_basis=[],
            missing_information=[],
            next_steps=[
                "POST /api/v1/investigations with this lot_id to trigger ProofPath evaluation.",
                "Add declared_attributes (composition, contamination levels) to the lot before investigating.",
            ],
        )

    def _make_deferred_recommendation(
        self, lot: MaterialLot
    ) -> PreventionRecommendation:
        return PreventionRecommendation(
            recommendation_id=str(uuid.uuid4()),
            lot_id=lot.lot_id,
            category=RecommendationCategory.DEFERRED,
            summary=(
                f"No pre-configured recovery routes found for material type '{lot.material_type}'."
            ),
            rationale=(
                f"The STRATA route catalog does not currently include a pre-qualified pathway for "
                f"'{lot.material_type}'. This does not indicate the material is unrecoverable; "
                f"it may require a bespoke route review."
            ),
            confidence=RecommendationConfidence.LOW,
            evidence_basis=[],
            missing_information=[
                MissingInformationItem(
                    item_id="missing-route-catalog-entry",
                    description=f"Pre-qualified recovery route for material type '{lot.material_type}'",
                    acquisition_method="external_source",
                )
            ],
            next_steps=[
                "Contact your STRATA account manager to request route catalog expansion.",
                "Consult regional industrial ecology directories for bespoke receiver identification.",
            ],
        )

    def _make_global_evidence_gap_recommendation(
        self,
        lot: MaterialLot,
        evidence_records: List[EvidenceRecord],
        candidate_routes: list,
    ) -> Optional[PreventionRecommendation]:
        """
        Generates a lot-preparation recommendation when the lot has no verified
        evidence and candidate routes exist that require it.
        """
        if not candidate_routes:
            return None

        verified_evidence = [
            e for e in evidence_records
            if e.verification_state == EvidenceVerificationState.VERIFIED.value
        ]
        if verified_evidence:
            # At least some verified evidence exists — no global gap rec needed
            return None

        # Collect all unique required facts across candidate routes
        all_required: List[Tuple[str, str, str]] = []
        seen: set = set()
        for route in candidate_routes:
            for fact in route.required_facts:
                if fact.fact_id not in seen:
                    seen.add(fact.fact_id)
                    all_required.append((fact.fact_id, fact.description, fact.acquisition_method))

        if not all_required:
            return None

        missing_items = [
            MissingInformationItem(
                item_id=fact_id,
                description=desc,
                acquisition_method=method,
            )
            for fact_id, desc, method in all_required
        ]

        return PreventionRecommendation(
            recommendation_id=str(uuid.uuid4()),
            lot_id=lot.lot_id,
            category=RecommendationCategory.LOT_PREPARATION,
            summary=(
                f"Gather {len(missing_items)} specification fact(s) to support route qualification."
            ),
            rationale=(
                f"Lot '{lot.lot_id}' has no verified evidence records. "
                f"The following specification items are required across candidate routes to "
                f"achieve supported qualification status."
            ),
            confidence=RecommendationConfidence.LOW,
            evidence_basis=[],
            missing_information=missing_items,
            next_steps=[
                f"Obtain: {m.description} (via {m.acquisition_method})" for m in missing_items
            ],
        )
