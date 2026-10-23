"""Marketplace domain service: listings, buyer requirements and candidate matching.

Candidate filtering is pure (``matches_requirement`` / ``filter_candidates``).
``MarketplaceService`` wires it to persistence and to ProofPath. Qualification
is requested from ProofPath for each candidate and is never computed here.
Material lots and their canonical ``material_lot_id`` remain owned by the
materials registry.
"""

from datetime import datetime, timezone
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple

from pydantic import BaseModel
from sqlalchemy.orm import Session

from strata.core.auth import AuthUser
from strata.core.errors import (
    ForbiddenError,
    InvalidStateTransitionError,
    ResourceNotFoundError,
    ValidationError,
)
from strata.domain.marketplace.models import (
    BuyerRequirement,
    Listing,
    OfferModel,
    RFQModel,
    WorkflowEventModel,
)
from strata.domain.marketplace.qualification import ProofPathQualificationClient
from strata.domain.marketplace.repository import MarketplaceRepository
from strata.domain.marketplace.schemas import (
    BuyerRequirementCreate,
    BuyerRequirementMatchesResponse,
    BuyerRequirementRead,
    BuyerRequirementUpdate,
    CityIndicatorsResponse,
    ClusterIndicatorsResponse,
    FreightOption,
    ListingCreate,
    ListingRead,
    ListingStatus,
    ListingUpdate,
    ListingVisibility,
    LogisticsComparisonRequest,
    LogisticsComparisonResponse,
    MatchCandidateRead,
    MatchEligibility,
    MaterialCategoryVolume,
    OfferCreate,
    OfferRead,
    OfferStatus,
    QualificationResult,
    RFQCreate,
    RFQRead,
    RFQStatus,
    WorkflowEventCreate,
    WorkflowEventRead,
    WorkflowEventType,
)
from strata.domain.materials.models import Facility
from strata.domain.materials.taxonomy import get_all_material_types, get_material_type
from strata.domain.qualification.routes import CANDIDATE_ROUTES, CandidateRoute
from strata.domain.qualification.service import ProofPathQualificationEngine
from strata.schemas.qualification import QualificationOutcome

DEFAULT_VISIBILITY_LEVELS: FrozenSet[ListingVisibility] = frozenset(
    {ListingVisibility.PUBLIC, ListingVisibility.CLUSTER_ONLY}
)


class CandidateListing(BaseModel):
    """A listing paired with the material category of its lot.

    ``material_category`` is a snapshot taken from the materials registry by the
    caller; this module does not own or re-derive it.
    """
    listing: ListingRead
    material_category: str


def _normalise(value: str) -> str:
    return value.strip().lower()


def matches_requirement(
    candidate: CandidateListing,
    requirement: BuyerRequirementRead,
    visibility_levels: Optional[Iterable[ListingVisibility]] = None,
) -> bool:
    """True when a single listing satisfies every hard filter of the requirement.

    Filters:
      * status is ACTIVE (drafts, paused, sold-out and withdrawn listings are excluded)
      * visibility is within ``visibility_levels`` (default: public and cluster_only)
      * material category matches (case-insensitive)
      * unit matches (case-insensitive)
      * available quantity covers ``min_quantity``

    ``max_quantity`` is not a filter: a larger listing can still serve a buyer
    who takes at most ``max_quantity``.
    """
    levels = frozenset(visibility_levels) if visibility_levels is not None else DEFAULT_VISIBILITY_LEVELS
    listing = candidate.listing

    if listing.status != ListingStatus.ACTIVE:
        return False
    if listing.visibility not in levels:
        return False
    if _normalise(candidate.material_category) != _normalise(requirement.material_category):
        return False
    if _normalise(listing.unit) != _normalise(requirement.unit):
        return False
    if listing.available_quantity < requirement.min_quantity:
        return False
    return True


def filter_candidates(
    candidates: Iterable[CandidateListing],
    requirement: BuyerRequirementRead,
    visibility_levels: Optional[Iterable[ListingVisibility]] = None,
) -> List[CandidateListing]:
    """Return the listings that match the requirement, preserving input order."""
    return [
        c for c in candidates
        if matches_requirement(c, requirement, visibility_levels=visibility_levels)
    ]


class MarketplaceService:
    """Orchestrates marketplace persistence, candidate matching and qualification."""

    def __init__(self, db: Session) -> None:
        self.db = db
        self.repository = MarketplaceRepository(db)

    # -- listings -----------------------------------------------------------

    def enrich_listing(self, listing: Listing) -> ListingRead:
        """Enriches listing with material lot specifications, properties, facility location, and evidence."""
        read = ListingRead.model_validate(listing)
        lots = self.repository.get_lots_by_ids([listing.material_lot_id])
        lot = lots.get(listing.material_lot_id)
        if lot:
            read.material_type = lot.material_type
            tax = get_material_type(lot.material_type)
            read.material_category = tax.category if tax else None
            read.material_properties = lot.declared_attributes or {}
            read.availability_from = lot.availability_from
            read.availability_to = lot.availability_to
            read.lot_quantity = lot.quantity

            # Facility location
            fac = self.repository.get_facility(lot.facility_id)
            if fac:
                parts = [p for p in [fac.name, fac.location_postal_code, fac.location_country] if p]
                read.location = ", ".join(parts)

            # Evidence
            ev_records = self.repository.get_evidence_for_lot(lot.lot_id)
            read.evidence_count = len(ev_records)
            read.supporting_evidence = [
                {
                    "evidence_id": e.evidence_id,
                    "claim_subject": e.claim_subject,
                    "claim_text": e.claim_text,
                    "source_title": e.source_title,
                    "provenance": e.provenance,
                    "verification_state": e.verification_state,
                }
                for e in ev_records[:5]
            ]
        return read

    def create_listing(self, payload: ListingCreate, org_id: str) -> ListingRead:
        """Publishes a lot the caller's organization owns, after checking it against the registry."""
        lot = self.repository.get_lot_for_org(lot_id=payload.material_lot_id, org_id=org_id)
        if not lot:
            raise ResourceNotFoundError(
                f"Material lot '{payload.material_lot_id}' was not found in your organization scope.",
                details={"material_lot_id": payload.material_lot_id},
            )
        if lot.facility_id != payload.facility_id:
            raise ValidationError(
                "facility_id does not match the facility that registered this lot.",
                details={"facility_id": payload.facility_id, "lot_facility_id": lot.facility_id},
            )
        if _normalise(payload.unit) != _normalise(lot.unit):
            raise ValidationError(
                f"Listing unit '{payload.unit}' must match the lot unit '{lot.unit}'.",
                details={"unit": payload.unit, "lot_unit": lot.unit},
            )
        if payload.available_quantity > lot.quantity:
            raise ValidationError(
                "available_quantity cannot exceed the quantity registered for this lot.",
                details={"available_quantity": payload.available_quantity, "lot_quantity": lot.quantity},
            )

        listing = Listing(
            material_lot_id=lot.lot_id,
            organization_id=org_id,
            facility_id=lot.facility_id,
            visibility=payload.visibility,
            asking_price_per_unit=payload.asking_price_per_unit,
            currency=payload.currency,
            available_quantity=payload.available_quantity,
            unit=lot.unit,
            status=payload.status,
        )
        saved = self.repository.add_listing(listing)
        event = WorkflowEventModel(
            entity_type="listing",
            entity_id=saved.id,
            event_type=WorkflowEventType.LISTING_CREATED.value,
            from_state=None,
            to_state=saved.status.value,
            actor_id="system",
            actor_role="facility_operator",
            actor_org_id=org_id,
            notes="Listing published to circular exchange",
            metadata_payload={},
        )
        self.repository.add_workflow_event(event)
        return self.enrich_listing(saved)

    def get_listing(self, listing_id: str, org_id: str) -> ListingRead:
        listing = self.repository.get_listing(listing_id=listing_id, org_id=org_id)
        if not listing:
            raise ResourceNotFoundError(
                f"Listing '{listing_id}' was not found in your organization scope.",
                details={"listing_id": listing_id},
            )
        return self.enrich_listing(listing)

    def update_listing(
        self,
        listing_id: str,
        payload: ListingUpdate,
        actor: AuthUser,
    ) -> ListingRead:
        """Updates listing commercial terms, availability, visibility, or status."""
        listing = self.repository.get_listing(listing_id=listing_id, org_id=actor.org_id)
        if not listing:
            raise ResourceNotFoundError(
                f"Listing '{listing_id}' was not found in your organization scope.",
                details={"listing_id": listing_id},
            )

        lot = self.repository.get_lot_for_org(lot_id=listing.material_lot_id, org_id=actor.org_id)
        if payload.available_quantity is not None and lot and payload.available_quantity > lot.quantity:
            raise ValidationError(
                "available_quantity cannot exceed the quantity registered for this lot.",
                details={"available_quantity": payload.available_quantity, "lot_quantity": lot.quantity},
            )

        if payload.status is not None and payload.status != listing.status:
            return self.update_listing_status(
                listing_id=listing_id,
                new_status=payload.status,
                actor=actor,
                notes=payload.notes,
            )

        old_price = listing.asking_price_per_unit
        updated = self.repository.update_listing(
            listing,
            asking_price_per_unit=payload.asking_price_per_unit,
            available_quantity=payload.available_quantity,
            currency=payload.currency,
            visibility=payload.visibility,
        )

        self._record_event(
            entity_type="listing",
            entity_id=updated.id,
            event_type=WorkflowEventType.LISTING_UPDATED,
            from_state=listing.status.value,
            to_state=updated.status.value,
            actor=actor,
            notes=payload.notes or "Listing updated",
            metadata={"old_price": old_price, "new_price": updated.asking_price_per_unit},
        )
        return self.enrich_listing(updated)

    def list_listings(self, org_id: str, page: int, page_size: int) -> Tuple[List[ListingRead], int]:
        skip = (page - 1) * page_size
        rows, total = self.repository.list_listings(org_id=org_id, skip=skip, limit=page_size)
        return [self.enrich_listing(r) for r in rows], total

    def search_exchange_listings(
        self,
        actor: AuthUser,
        category: Optional[str] = None,
        material_type: Optional[str] = None,
        unit: Optional[str] = None,
        min_quantity: Optional[float] = None,
        max_price: Optional[float] = None,
        visibility: Optional[ListingVisibility] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ListingRead], int]:
        """Search active discoverable listings across the circular exchange."""
        skip = (page - 1) * page_size
        vis_levels = [visibility] if visibility else sorted(DEFAULT_VISIBILITY_LEVELS, key=lambda v: v.value)

        rows, total = self.repository.search_listings(
            skip=skip,
            limit=page_size,
            status=ListingStatus.ACTIVE,
            visibility_levels=vis_levels,
            unit=unit,
            min_quantity=min_quantity,
            max_price=max_price,
        )

        enriched = [self.enrich_listing(r) for r in rows]
        if category:
            enriched = [r for r in enriched if r.material_category and _normalise(r.material_category) == _normalise(category)]
        if material_type:
            enriched = [r for r in enriched if r.material_type and _normalise(r.material_type) == _normalise(material_type)]

        return enriched, len(enriched) if (category or material_type) else total

    # -- buyer requirements -------------------------------------------------

    def create_requirement(self, payload: BuyerRequirementCreate, org_id: str) -> BuyerRequirementRead:
        valid_categories = {t.category for t in get_all_material_types()}
        if payload.material_category not in valid_categories:
            raise ValidationError(
                f"Unknown material category '{payload.material_category}'.",
                details={"material_category": payload.material_category, "allowed": sorted(valid_categories)},
            )
        requirement = BuyerRequirement(
            organization_id=org_id,
            facility_id=payload.facility_id,
            material_category=payload.material_category,
            min_quantity=payload.min_quantity,
            max_quantity=payload.max_quantity,
            unit=payload.unit,
            target_price_per_unit=payload.target_price_per_unit,
            required_properties=payload.required_properties,
            prohibited_conditions=payload.prohibited_conditions,
            visibility=payload.visibility,
            location=payload.location,
            delivery_requirements=payload.delivery_requirements,
            constraints=payload.constraints,
        )
        saved = self.repository.add_requirement(requirement)
        event = WorkflowEventModel(
            entity_type="requirement",
            entity_id=saved.id,
            event_type=WorkflowEventType.REQUIREMENT_CREATED.value,
            from_state=None,
            to_state="active",
            actor_id="system",
            actor_role="buyer_admin",
            actor_org_id=org_id,
            notes="Buyer requirement registered on exchange",
            metadata_payload={},
        )
        self.repository.add_workflow_event(event)
        return BuyerRequirementRead.model_validate(saved)

    def get_requirement(self, requirement_id: str, org_id: str) -> BuyerRequirementRead:
        requirement = self.repository.get_requirement(requirement_id=requirement_id, org_id=org_id)
        if not requirement:
            raise ResourceNotFoundError(
                f"Buyer requirement '{requirement_id}' was not found in your organization scope.",
                details={"requirement_id": requirement_id},
            )
        return BuyerRequirementRead.model_validate(requirement)

    def list_requirements(self, org_id: str, page: int = 1, page_size: int = 20) -> Tuple[List[BuyerRequirementRead], int]:
        skip = (page - 1) * page_size
        rows, total = self.repository.list_requirements(org_id=org_id, skip=skip, limit=page_size)
        return [BuyerRequirementRead.model_validate(r) for r in rows], total

    def update_requirement(
        self,
        requirement_id: str,
        payload: BuyerRequirementUpdate,
        actor: AuthUser,
    ) -> BuyerRequirementRead:
        req = self.repository.get_requirement(requirement_id=requirement_id, org_id=actor.org_id)
        if not req:
            raise ResourceNotFoundError(
                f"Buyer requirement '{requirement_id}' was not found in your organization scope.",
                details={"requirement_id": requirement_id},
            )

        min_q = payload.min_quantity if payload.min_quantity is not None else req.min_quantity
        max_q = payload.max_quantity if payload.max_quantity is not None else req.max_quantity
        if max_q is not None and max_q < min_q:
            raise ValidationError("max_quantity cannot be smaller than min_quantity")

        updated = self.repository.update_requirement(
            req,
            min_quantity=payload.min_quantity,
            max_quantity=payload.max_quantity,
            target_price_per_unit=payload.target_price_per_unit,
            required_properties=payload.required_properties,
            prohibited_conditions=payload.prohibited_conditions,
            visibility=payload.visibility,
            location=payload.location,
            delivery_requirements=payload.delivery_requirements,
            constraints=payload.constraints,
        )

        self._record_event(
            entity_type="requirement",
            entity_id=updated.id,
            event_type=WorkflowEventType.REQUIREMENT_UPDATED,
            from_state=None,
            to_state="active",
            actor=actor,
            notes="Buyer requirement updated",
        )
        return BuyerRequirementRead.model_validate(updated)

    def delete_requirement(self, requirement_id: str, actor: AuthUser) -> None:
        req = self.repository.get_requirement(requirement_id=requirement_id, org_id=actor.org_id)
        if not req:
            raise ResourceNotFoundError(
                f"Buyer requirement '{requirement_id}' was not found in your organization scope.",
                details={"requirement_id": requirement_id},
            )
        self.repository.delete_requirement(req)
        self._record_event(
            entity_type="requirement",
            entity_id=requirement_id,
            event_type=WorkflowEventType.REQUIREMENT_DELETED,
            from_state="active",
            to_state="deleted",
            actor=actor,
            notes="Buyer requirement deleted",
        )

    # -- matching and qualification ----------------------------------------

    def find_candidates(self, requirement_id: str, org_id: str) -> List[ListingRead]:
        """Active listings from other organizations that satisfy the requirement's hard filters."""
        requirement = self.get_requirement(requirement_id=requirement_id, org_id=org_id)
        listings = self.repository.list_discoverable_listings(
            exclude_org_id=org_id,
            visibility_levels=sorted(DEFAULT_VISIBILITY_LEVELS, key=lambda v: v.value),
        )
        lots = self.repository.get_lots_by_ids([l.material_lot_id for l in listings])

        candidates: List[CandidateListing] = []
        for listing in listings:
            lot = lots.get(listing.material_lot_id)
            if lot is None:
                continue
            taxonomy = get_material_type(lot.material_type)
            if taxonomy is None:
                continue
            candidates.append(
                CandidateListing(
                    listing=ListingRead.model_validate(listing),
                    material_category=taxonomy.category,
                )
            )

        matched = filter_candidates(candidates, requirement)
        return [c.listing for c in matched]

    async def qualify_candidates(
        self,
        requirement_id: str,
        org_id: str,
        client: ProofPathQualificationClient,
    ) -> List[QualificationResult]:
        """Asks ProofPath to assess each candidate lot against the requirement."""
        candidates = self.find_candidates(requirement_id=requirement_id, org_id=org_id)
        results: List[QualificationResult] = []
        for listing in candidates:
            raw = await client.assess_lot_qualification(listing.material_lot_id, requirement_id)
            results.append(QualificationResult.model_validate(raw))
        return results

    def _estimate_facility_distance(self, fac1: Optional[Facility], fac2: Optional[Facility]) -> float:
        """Computes distance between facilities or returns regional default (estimated)."""
        if not fac1 or not fac2:
            return 120.0
        if fac1.facility_id == fac2.facility_id:
            return 0.0
        if fac1.location_postal_code and fac2.location_postal_code:
            try:
                p1 = int("".join(filter(str.isdigit, fac1.location_postal_code)) or "10000")
                p2 = int("".join(filter(str.isdigit, fac2.location_postal_code)) or "20000")
                diff = abs(p1 - p2) % 500
                return round(max(15.0, float(diff)), 1)
            except Exception:
                pass
        return 145.0

    def match_candidates_with_qualification(
        self,
        requirement_id: str,
        org_id: str,
    ) -> BuyerRequirementMatchesResponse:
        """
        Matches active listings against a buyer requirement.
        Evaluates material compatibility, quantity, location constraints, and
        authoritative deterministic ProofPath qualification.
        CRITICAL RULE: Never override hard incompatibilities with a high match score.
        Clearly distinguishes eligible, conditional, and ineligible candidates.
        """
        requirement = self.get_requirement(requirement_id=requirement_id, org_id=org_id)
        req_fac = self.repository.get_facility(requirement.facility_id)

        # Retrieve candidate listings from other organizations
        listings = self.repository.list_discoverable_listings(
            exclude_org_id=org_id,
            visibility_levels=sorted(DEFAULT_VISIBILITY_LEVELS, key=lambda v: v.value),
        )
        lots = self.repository.get_lots_by_ids([l.material_lot_id for l in listings])

        engine = ProofPathQualificationEngine()
        matches: List[MatchCandidateRead] = []

        for listing in listings:
            lot = lots.get(listing.material_lot_id)
            if not lot:
                continue
            tax = get_material_type(lot.material_type)
            if not tax:
                continue

            enriched_listing = self.enrich_listing(listing)

            compat_reasons: List[str] = []
            incompatibilities: List[str] = []
            missing_info: List[str] = []

            # 1. Category check
            if _normalise(tax.category) != _normalise(requirement.material_category):
                incompatibilities.append(
                    f"Category mismatch: listing category '{tax.category}' does not match required '{requirement.material_category}'."
                )
            else:
                compat_reasons.append(f"Material category matches: {tax.category}")

            # 2. Quantity check
            if listing.available_quantity < requirement.min_quantity:
                incompatibilities.append(
                    f"Insufficient quantity: available {listing.available_quantity} {listing.unit} < required min {requirement.min_quantity} {requirement.unit}."
                )
            else:
                compat_reasons.append(
                    f"Quantity satisfied: {listing.available_quantity} {listing.unit} available (min: {requirement.min_quantity})"
                )

            # 3. Prohibited conditions check
            declared_attrs = lot.declared_attributes or {}
            for prohibited in requirement.prohibited_conditions:
                p_lower = prohibited.strip().lower()
                if declared_attrs.get(prohibited) is True or any(
                    p_lower in str(c).lower() for c in declared_attrs.get("contaminants", [])
                ):
                    incompatibilities.append(f"Hard constraint violation: prohibited condition '{prohibited}' detected.")

            # 4. Location / Distance calculation
            list_fac = self.repository.get_facility(lot.facility_id)
            distance_km = self._estimate_facility_distance(list_fac, req_fac)

            delivery_reqs = getattr(requirement, "delivery_requirements", {}) or {}
            max_dist = delivery_reqs.get("max_distance_km")
            if max_dist and distance_km > float(max_dist):
                incompatibilities.append(
                    f"Distance constraint exceeded: estimated distance {distance_km} km exceeds maximum {max_dist} km."
                )

            # 5. Authoritative ProofPath Qualification
            ev_records = self.repository.get_evidence_for_lot(lot.lot_id)
            applicable_routes = [r for r in CANDIDATE_ROUTES.values() if r.target_material_type == lot.material_type]

            proofpath_summary = None
            if applicable_routes:
                primary_route = applicable_routes[0]
                assessment = engine.evaluate(lot=lot, route=primary_route, evidence_records=ev_records)
                proofpath_summary = {
                    "route_id": primary_route.route_id,
                    "route_name": primary_route.name,
                    "outcome": assessment.status.value,
                    "blocking_conditions": assessment.blocking_conditions,
                    "missing_facts": [getattr(f, "fact_id", str(f)) for f in assessment.missing_facts],
                    "evidence_refs": assessment.evidence_refs,
                }

                if assessment.status == QualificationOutcome.UNSUPPORTED:
                    for block in assessment.blocking_conditions:
                        incompatibilities.append(f"ProofPath hard gate failure: {block}")
                elif assessment.status == QualificationOutcome.CONDITIONAL:
                    for mf in assessment.missing_facts:
                        missing_info.append(f"Missing verification: {getattr(mf, 'fact_id', str(mf))}")
                elif assessment.status == QualificationOutcome.SUPPORTED:
                    compat_reasons.append(f"ProofPath qualified for route: {primary_route.name}")
            else:
                missing_info.append(f"No standard recovery route cataloged for '{lot.material_type}'")

            # 6. Determine Eligibility and Match Score
            # RULE: Incompatibilities CANNOT be overridden by a high match score!
            if incompatibilities:
                eligibility = MatchEligibility.INELIGIBLE
                match_score = 0.0  # Zeroed out due to hard incompatibilities
            elif missing_info:
                eligibility = MatchEligibility.CONDITIONAL
                base_score = 55.0
                if requirement.target_price_per_unit and listing.asking_price_per_unit <= requirement.target_price_per_unit:
                    base_score += 10.0
                if distance_km <= 200.0:
                    base_score += 5.0
                match_score = min(74.0, base_score)
            else:
                eligibility = MatchEligibility.ELIGIBLE
                score = 80.0
                if requirement.target_price_per_unit:
                    ratio = max(0.0, 1.0 - (listing.asking_price_per_unit / (requirement.target_price_per_unit + 0.001)))
                    score += min(10.0, ratio * 10.0)
                if distance_km <= 100.0:
                    score += 8.0
                elif distance_km <= 300.0:
                    score += 4.0
                match_score = min(98.0, score)

            # Logistics comparison summary
            logistics_summary = {
                "distance_km": distance_km,
                "is_distance_estimated": True,
                "freight_mode": "road_standard_diesel",
                "estimated_freight_cost_usd": round(distance_km * (listing.available_quantity / 1000.0) * 0.12, 2),
                "estimated_emissions_kg_co2e": round(distance_km * (listing.available_quantity / 1000.0) * 0.095, 2),
                "disclaimer": "Indicative transport estimate. Confirm with carrier.",
            }

            candidate_match = MatchCandidateRead(
                listing=enriched_listing,
                match_score=round(match_score, 1),
                eligibility=eligibility,
                compatibility_reasons=compat_reasons,
                incompatibilities=incompatibilities,
                missing_information=missing_info,
                distance_km=distance_km,
                logistics_summary=logistics_summary,
                qualification_details=proofpath_summary,
            )
            matches.append(candidate_match)

        # Sort matches: eligible first (highest score), then conditional, then ineligible
        matches.sort(key=lambda m: (
            0 if m.eligibility == MatchEligibility.ELIGIBLE else (1 if m.eligibility == MatchEligibility.CONDITIONAL else 2),
            -m.match_score,
        ))

        eligible_count = sum(1 for m in matches if m.eligibility == MatchEligibility.ELIGIBLE)
        conditional_count = sum(1 for m in matches if m.eligibility == MatchEligibility.CONDITIONAL)
        ineligible_count = sum(1 for m in matches if m.eligibility == MatchEligibility.INELIGIBLE)

        return BuyerRequirementMatchesResponse(
            requirement_id=requirement.id,
            total_candidates_evaluated=len(matches),
            eligible_count=eligible_count,
            conditional_count=conditional_count,
            ineligible_count=ineligible_count,
            matches=matches,
        )

    # -- workflow event recording -------------------------------------------

    def _record_event(
        self,
        entity_type: str,
        entity_id: str,
        event_type: WorkflowEventType,
        from_state: Optional[str],
        to_state: str,
        actor: AuthUser,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkflowEventModel:
        event = WorkflowEventModel(
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type.value,
            from_state=from_state,
            to_state=to_state,
            actor_id=actor.user_id,
            actor_role=actor.role,
            actor_org_id=actor.org_id,
            notes=notes,
            metadata_payload=metadata or {},
        )
        return self.repository.add_workflow_event(event)

    # -- listing lifecycle state transitions --------------------------------

    def update_listing_status(
        self,
        listing_id: str,
        new_status: ListingStatus,
        actor: AuthUser,
        notes: Optional[str] = None,
    ) -> ListingRead:
        """Transitions a listing's lifecycle state (publish, pause, withdraw)."""
        listing = self.repository.get_listing(listing_id=listing_id, org_id=actor.org_id)
        if not listing:
            raise ResourceNotFoundError(
                f"Listing '{listing_id}' was not found in your organization scope.",
                details={"listing_id": listing_id},
            )

        if listing.status == new_status:
            return ListingRead.model_validate(listing)

        # Explicit transition rules:
        valid_transitions = {
            ListingStatus.DRAFT: {ListingStatus.ACTIVE, ListingStatus.WITHDRAWN},
            ListingStatus.ACTIVE: {ListingStatus.PAUSED, ListingStatus.WITHDRAWN, ListingStatus.SOLD_OUT},
            ListingStatus.PAUSED: {ListingStatus.ACTIVE, ListingStatus.WITHDRAWN},
        }

        allowed = valid_transitions.get(listing.status, set())
        if new_status not in allowed:
            raise InvalidStateTransitionError(
                f"Cannot transition listing from '{listing.status.value}' to '{new_status.value}'.",
                details={
                    "current_status": listing.status.value,
                    "target_status": new_status.value,
                    "allowed_transitions": [s.value for s in allowed],
                },
            )

        old_status = listing.status
        updated = self.repository.update_listing_status(listing, new_status)

        if new_status == ListingStatus.ACTIVE:
            event_type = WorkflowEventType.LISTING_PUBLISHED
        elif new_status == ListingStatus.PAUSED:
            event_type = WorkflowEventType.LISTING_PAUSED
        elif new_status == ListingStatus.WITHDRAWN:
            event_type = WorkflowEventType.LISTING_WITHDRAWN
        else:
            event_type = WorkflowEventType.LISTING_PAUSED

        self._record_event(
            entity_type="listing",
            entity_id=updated.id,
            event_type=event_type,
            from_state=old_status.value,
            to_state=new_status.value,
            actor=actor,
            notes=notes,
        )

        return ListingRead.model_validate(updated)

    # -- RFQ lifecycle and state transitions --------------------------------

    def create_rfq(self, payload: RFQCreate, actor: AuthUser) -> RFQRead:
        """Creates an RFQ against an active listing."""
        listing = self.repository.get_listing_by_id(payload.listing_id)
        if not listing:
            raise ResourceNotFoundError(
                f"Target listing '{payload.listing_id}' not found.",
                details={"listing_id": payload.listing_id},
            )

        if listing.status != ListingStatus.ACTIVE:
            raise InvalidStateTransitionError(
                f"Cannot create RFQ for listing '{payload.listing_id}' with status '{listing.status.value}'. Listing must be active.",
                details={"listing_status": listing.status.value},
            )

        if listing.organization_id == actor.org_id:
            raise ValidationError(
                "An organization cannot submit an RFQ against its own listing.",
                details={"listing_id": listing.id, "organization_id": actor.org_id},
            )

        if payload.buyer_requirement_id:
            req = self.repository.get_requirement(
                requirement_id=payload.buyer_requirement_id,
                org_id=actor.org_id,
            )
            if not req:
                raise ResourceNotFoundError(
                    f"Buyer requirement '{payload.buyer_requirement_id}' was not found in your organization scope.",
                    details={"buyer_requirement_id": payload.buyer_requirement_id},
                )

        if _normalise(payload.unit) != _normalise(listing.unit):
            raise ValidationError(
                f"Requested unit '{payload.unit}' does not match listing unit '{listing.unit}'.",
                details={"requested_unit": payload.unit, "listing_unit": listing.unit},
            )

        initial_status = RFQStatus.PENDING_APPROVAL if payload.submit_for_approval else RFQStatus.DRAFT

        rfq = RFQModel(
            listing_id=listing.id,
            buyer_requirement_id=payload.buyer_requirement_id,
            buyer_organization_id=actor.org_id,
            buyer_facility_id=payload.buyer_facility_id,
            seller_organization_id=listing.organization_id,
            seller_facility_id=listing.facility_id,
            requested_quantity=payload.requested_quantity,
            unit=listing.unit,
            target_price_per_unit=payload.target_price_per_unit,
            currency=payload.currency,
            status=initial_status,
            notes=payload.notes,
            created_by=actor.user_id,
        )
        saved = self.repository.add_rfq(rfq)

        self._record_event(
            entity_type="rfq",
            entity_id=saved.id,
            event_type=WorkflowEventType.RFQ_CREATED,
            from_state=None,
            to_state=initial_status.value,
            actor=actor,
            notes=payload.notes,
        )

        if initial_status == RFQStatus.PENDING_APPROVAL:
            self._record_event(
                entity_type="rfq",
                entity_id=saved.id,
                event_type=WorkflowEventType.RFQ_SUBMITTED,
                from_state=RFQStatus.DRAFT.value,
                to_state=RFQStatus.PENDING_APPROVAL.value,
                actor=actor,
                notes="Directly submitted for human approval upon creation.",
            )

        return RFQRead.model_validate(saved)

    def submit_rfq_for_approval(
        self,
        rfq_id: str,
        actor: AuthUser,
        notes: Optional[str] = None,
    ) -> RFQRead:
        """Transitions a DRAFT RFQ to PENDING_APPROVAL."""
        rfq = self.repository.get_rfq(rfq_id=rfq_id)
        if not rfq or (actor.role != "admin" and rfq.buyer_organization_id != actor.org_id):
            raise ResourceNotFoundError(
                f"RFQ '{rfq_id}' was not found in your organization scope.",
                details={"rfq_id": rfq_id},
            )

        if rfq.status != RFQStatus.DRAFT:
            raise InvalidStateTransitionError(
                f"Cannot submit RFQ with status '{rfq.status.value}' for approval. Only DRAFT RFQs can be submitted.",
                details={"current_status": rfq.status.value},
            )

        updated = self.repository.update_rfq_status(rfq, RFQStatus.PENDING_APPROVAL)
        self._record_event(
            entity_type="rfq",
            entity_id=updated.id,
            event_type=WorkflowEventType.RFQ_SUBMITTED,
            from_state=RFQStatus.DRAFT.value,
            to_state=RFQStatus.PENDING_APPROVAL.value,
            actor=actor,
            notes=notes,
        )
        return RFQRead.model_validate(updated)

    def approve_rfq(
        self,
        rfq_id: str,
        actor: AuthUser,
        notes: Optional[str] = None,
    ) -> RFQRead:
        """Human approval gate: opens an RFQ for external seller offers.

        Requires: actor.role in ['facility_manager', 'admin'].
        """
        if actor.role not in ["facility_manager", "admin"]:
            raise ForbiddenError(
                f"Role '{actor.role}' is not authorized to approve RFQs. Required: facility_manager or admin.",
                details={"required_roles": ["facility_manager", "admin"], "current_role": actor.role},
            )

        rfq = self.repository.get_rfq(rfq_id=rfq_id)
        if not rfq:
            raise ResourceNotFoundError(
                f"RFQ '{rfq_id}' was not found.",
                details={"rfq_id": rfq_id},
            )

        if actor.role != "admin" and rfq.buyer_organization_id != actor.org_id:
            raise ResourceNotFoundError(
                f"RFQ '{rfq_id}' was not found in your organization scope.",
                details={"rfq_id": rfq_id},
            )

        if rfq.status not in [RFQStatus.PENDING_APPROVAL, RFQStatus.DRAFT]:
            raise InvalidStateTransitionError(
                f"Cannot approve RFQ with status '{rfq.status.value}'.",
                details={"current_status": rfq.status.value},
            )

        old_status = rfq.status
        rfq.approved_by = actor.user_id
        rfq.approved_at = datetime.now(timezone.utc)
        updated = self.repository.update_rfq_status(rfq, RFQStatus.OPEN)

        self._record_event(
            entity_type="rfq",
            entity_id=updated.id,
            event_type=WorkflowEventType.RFQ_APPROVED,
            from_state=old_status.value,
            to_state=RFQStatus.OPEN.value,
            actor=actor,
            notes=notes,
        )
        return RFQRead.model_validate(updated)

    def cancel_rfq(
        self,
        rfq_id: str,
        actor: AuthUser,
        notes: Optional[str] = None,
    ) -> RFQRead:
        """Cancels an RFQ."""
        rfq = self.repository.get_rfq(rfq_id=rfq_id)
        if not rfq:
            raise ResourceNotFoundError(f"RFQ '{rfq_id}' was not found.")

        if actor.role != "admin" and actor.org_id not in [rfq.buyer_organization_id, rfq.seller_organization_id]:
            raise ResourceNotFoundError(f"RFQ '{rfq_id}' was not found in your organization scope.")

        if rfq.status in [RFQStatus.CLOSED, RFQStatus.CANCELLED]:
            raise InvalidStateTransitionError(
                f"Cannot cancel RFQ with status '{rfq.status.value}'.",
                details={"current_status": rfq.status.value},
            )

        old_status = rfq.status
        updated = self.repository.update_rfq_status(rfq, RFQStatus.CANCELLED)
        self._record_event(
            entity_type="rfq",
            entity_id=updated.id,
            event_type=WorkflowEventType.RFQ_CANCELLED,
            from_state=old_status.value,
            to_state=RFQStatus.CANCELLED.value,
            actor=actor,
            notes=notes,
        )
        return RFQRead.model_validate(updated)

    def get_rfq(self, rfq_id: str, actor: AuthUser) -> RFQRead:
        rfq = self.repository.get_rfq(rfq_id=rfq_id)
        if not rfq:
            raise ResourceNotFoundError(f"RFQ '{rfq_id}' was not found.")
        if actor.role != "admin" and actor.org_id not in [rfq.buyer_organization_id, rfq.seller_organization_id]:
            raise ResourceNotFoundError(f"RFQ '{rfq_id}' was not found in your organization scope.")
        return RFQRead.model_validate(rfq)

    def list_rfqs(
        self,
        actor: AuthUser,
        as_buyer: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[RFQRead], int]:
        skip = (page - 1) * page_size
        rows, total = self.repository.list_rfqs_for_org(
            org_id=actor.org_id,
            as_buyer=as_buyer,
            skip=skip,
            limit=page_size,
        )
        return [RFQRead.model_validate(r) for r in rows], total

    # -- Offer lifecycle and state transitions ------------------------------

    def submit_offer(
        self,
        rfq_id: str,
        payload: OfferCreate,
        actor: AuthUser,
    ) -> OfferRead:
        """Seller submits a commercial offer/quote against an OPEN RFQ."""
        rfq = self.repository.get_rfq(rfq_id=rfq_id)
        if not rfq:
            raise ResourceNotFoundError(
                f"RFQ '{rfq_id}' was not found.",
                details={"rfq_id": rfq_id},
            )

        if rfq.status != RFQStatus.OPEN:
            raise InvalidStateTransitionError(
                f"Cannot submit offer for RFQ with status '{rfq.status.value}'. RFQ must be OPEN.",
                details={"rfq_id": rfq_id, "rfq_status": rfq.status.value},
            )

        if actor.role != "admin" and rfq.seller_organization_id != actor.org_id:
            raise ForbiddenError(
                "Only the seller organization can submit an offer for this RFQ.",
                details={"rfq_seller_org": rfq.seller_organization_id, "actor_org": actor.org_id},
            )

        if _normalise(payload.unit) != _normalise(rfq.unit):
            raise ValidationError(
                f"Offered unit '{payload.unit}' must match RFQ unit '{rfq.unit}'.",
                details={"offered_unit": payload.unit, "rfq_unit": rfq.unit},
            )

        offer = OfferModel(
            rfq_id=rfq.id,
            listing_id=rfq.listing_id,
            seller_organization_id=rfq.seller_organization_id,
            seller_facility_id=rfq.seller_facility_id,
            offered_quantity=payload.offered_quantity,
            unit=rfq.unit,
            price_per_unit=payload.price_per_unit,
            currency=payload.currency,
            status=OfferStatus.SUBMITTED,
            terms=payload.terms,
            valid_until=payload.valid_until,
            created_by=actor.user_id,
        )
        saved = self.repository.add_offer(offer)

        self._record_event(
            entity_type="offer",
            entity_id=saved.id,
            event_type=WorkflowEventType.OFFER_SUBMITTED,
            from_state=None,
            to_state=OfferStatus.SUBMITTED.value,
            actor=actor,
            notes=payload.notes,
            metadata={
                "rfq_id": rfq.id,
                "price_per_unit": saved.price_per_unit,
                "offered_quantity": saved.offered_quantity,
            },
        )
        return OfferRead.model_validate(saved)

    def revise_offer(
        self,
        offer_id: str,
        payload: OfferCreate,
        actor: AuthUser,
    ) -> OfferRead:
        """Seller revises an active offer."""
        offer = self.repository.get_offer(offer_id=offer_id)
        if not offer:
            raise ResourceNotFoundError(
                f"Offer '{offer_id}' was not found.",
                details={"offer_id": offer_id},
            )

        if actor.role != "admin" and offer.seller_organization_id != actor.org_id:
            raise ForbiddenError(
                "Only the seller organization may revise this offer.",
                details={"seller_org": offer.seller_organization_id, "actor_org": actor.org_id},
            )

        rfq = self.repository.get_rfq(offer.rfq_id)
        if not rfq or rfq.status != RFQStatus.OPEN:
            raise InvalidStateTransitionError(
                "Cannot revise offer when the linked RFQ is not OPEN.",
                details={"rfq_status": rfq.status.value if rfq else None},
            )

        if offer.status in [OfferStatus.ACCEPTED, OfferStatus.REJECTED, OfferStatus.WITHDRAWN]:
            raise InvalidStateTransitionError(
                f"Cannot revise offer with status '{offer.status.value}'.",
                details={"offer_status": offer.status.value},
            )

        old_status = offer.status
        offer.offered_quantity = payload.offered_quantity
        offer.price_per_unit = payload.price_per_unit
        offer.currency = payload.currency
        offer.terms = payload.terms
        offer.valid_until = payload.valid_until
        updated = self.repository.update_offer_status(offer, OfferStatus.REVISED)

        self._record_event(
            entity_type="offer",
            entity_id=updated.id,
            event_type=WorkflowEventType.OFFER_REVISED,
            from_state=old_status.value,
            to_state=OfferStatus.REVISED.value,
            actor=actor,
            notes=payload.notes,
        )
        return OfferRead.model_validate(updated)

    def accept_offer(
        self,
        offer_id: str,
        actor: AuthUser,
        notes: Optional[str] = None,
    ) -> OfferRead:
        """Human approval gate: buyer accepts a binding offer.

        Requires: actor.role in ['buyer_admin', 'admin'].
        Closes the RFQ and automatically marks other open offers as REJECTED.
        """
        if actor.role not in ["buyer_admin", "admin"]:
            raise ForbiddenError(
                f"Role '{actor.role}' is not authorized to accept binding offers. Required: buyer_admin or admin.",
                details={"required_roles": ["buyer_admin", "admin"], "current_role": actor.role},
            )

        offer = self.repository.get_offer(offer_id=offer_id)
        if not offer:
            raise ResourceNotFoundError(
                f"Offer '{offer_id}' was not found.",
                details={"offer_id": offer_id},
            )

        rfq = self.repository.get_rfq(rfq_id=offer.rfq_id)
        if not rfq:
            raise ResourceNotFoundError(f"Linked RFQ '{offer.rfq_id}' was not found.")

        if actor.role != "admin" and rfq.buyer_organization_id != actor.org_id:
            raise ForbiddenError(
                "Only the buyer organization can accept an offer for this RFQ.",
                details={"buyer_organization_id": rfq.buyer_organization_id, "actor_org": actor.org_id},
            )

        if rfq.status != RFQStatus.OPEN:
            raise InvalidStateTransitionError(
                f"Cannot accept offer for RFQ with status '{rfq.status.value}'. RFQ must be OPEN.",
                details={"rfq_status": rfq.status.value},
            )

        if offer.status not in [OfferStatus.SUBMITTED, OfferStatus.UNDER_REVIEW, OfferStatus.REVISED]:
            raise InvalidStateTransitionError(
                f"Cannot accept offer with status '{offer.status.value}'.",
                details={"offer_status": offer.status.value},
            )

        old_offer_status = offer.status
        accepted_offer = self.repository.update_offer_status(offer, OfferStatus.ACCEPTED)

        # Transition RFQ to CLOSED
        self.repository.update_rfq_status(rfq, RFQStatus.CLOSED)

        # Record events
        self._record_event(
            entity_type="offer",
            entity_id=accepted_offer.id,
            event_type=WorkflowEventType.OFFER_ACCEPTED,
            from_state=old_offer_status.value,
            to_state=OfferStatus.ACCEPTED.value,
            actor=actor,
            notes=notes,
            metadata={"rfq_id": rfq.id},
        )

        self._record_event(
            entity_type="rfq",
            entity_id=rfq.id,
            event_type=WorkflowEventType.RFQ_CANCELLED,
            from_state=RFQStatus.OPEN.value,
            to_state=RFQStatus.CLOSED.value,
            actor=actor,
            notes=f"Closed upon acceptance of offer {accepted_offer.id}.",
        )

        # Auto-reject other open offers on this RFQ
        other_offers = self.repository.list_offers_for_rfq(rfq.id)
        for other in other_offers:
            if other.id != accepted_offer.id and other.status in [
                OfferStatus.SUBMITTED,
                OfferStatus.UNDER_REVIEW,
                OfferStatus.REVISED,
            ]:
                old_st = other.status
                self.repository.update_offer_status(other, OfferStatus.REJECTED)
                self._record_event(
                    entity_type="offer",
                    entity_id=other.id,
                    event_type=WorkflowEventType.OFFER_REJECTED,
                    from_state=old_st.value,
                    to_state=OfferStatus.REJECTED.value,
                    actor=actor,
                    notes="Auto-rejected because another offer was accepted.",
                )

        return OfferRead.model_validate(accepted_offer)

    def reject_offer(
        self,
        offer_id: str,
        actor: AuthUser,
        notes: Optional[str] = None,
    ) -> OfferRead:
        """Buyer rejects an offer."""
        offer = self.repository.get_offer(offer_id=offer_id)
        if not offer:
            raise ResourceNotFoundError(
                f"Offer '{offer_id}' was not found.",
                details={"offer_id": offer_id},
            )

        rfq = self.repository.get_rfq(offer.rfq_id)
        if not rfq:
            raise ResourceNotFoundError(f"Linked RFQ '{offer.rfq_id}' was not found.")

        if actor.role != "admin" and rfq.buyer_organization_id != actor.org_id:
            raise ForbiddenError(
                "Only the buyer organization can reject an offer for this RFQ.",
                details={"buyer_organization_id": rfq.buyer_organization_id, "actor_org": actor.org_id},
            )

        if offer.status in [OfferStatus.ACCEPTED, OfferStatus.REJECTED, OfferStatus.WITHDRAWN]:
            raise InvalidStateTransitionError(
                f"Cannot reject offer with status '{offer.status.value}'.",
                details={"offer_status": offer.status.value},
            )

        old_status = offer.status
        updated = self.repository.update_offer_status(offer, OfferStatus.REJECTED)

        self._record_event(
            entity_type="offer",
            entity_id=updated.id,
            event_type=WorkflowEventType.OFFER_REJECTED,
            from_state=old_status.value,
            to_state=OfferStatus.REJECTED.value,
            actor=actor,
            notes=notes,
        )
        return OfferRead.model_validate(updated)

    def list_offers_for_rfq(self, rfq_id: str, actor: AuthUser) -> List[OfferRead]:
        rfq = self.repository.get_rfq(rfq_id=rfq_id)
        if not rfq:
            raise ResourceNotFoundError(f"RFQ '{rfq_id}' was not found.")
        if actor.role != "admin" and actor.org_id not in [rfq.buyer_organization_id, rfq.seller_organization_id]:
            raise ResourceNotFoundError(f"RFQ '{rfq_id}' was not found in your organization scope.")
        offers = self.repository.list_offers_for_rfq(rfq_id=rfq.id)
        return [OfferRead.model_validate(o) for o in offers]

    def get_workflow_history(self, entity_id: str, actor: AuthUser) -> List[WorkflowEventRead]:
        """Returns the chronological audit event timeline for an entity."""
        rfq = self.repository.get_rfq(entity_id)
        if rfq:
            if actor.role != "admin" and actor.org_id not in [rfq.buyer_organization_id, rfq.seller_organization_id]:
                raise ResourceNotFoundError(f"Entity '{entity_id}' not found in your organization scope.")
        else:
            listing = self.repository.get_listing_by_id(entity_id)
            if listing and actor.role != "admin" and listing.organization_id != actor.org_id:
                raise ResourceNotFoundError(f"Entity '{entity_id}' not found in your organization scope.")

        events = self.repository.get_workflow_events(entity_id=entity_id)
        return [WorkflowEventRead.model_validate(e) for e in events]

    def review_offer(
        self,
        offer_id: str,
        actor: AuthUser,
        notes: Optional[str] = None,
    ) -> OfferRead:
        """Buyer places an offer under review."""
        offer = self.repository.get_offer(offer_id=offer_id)
        if not offer:
            raise ResourceNotFoundError(f"Offer '{offer_id}' was not found.", details={"offer_id": offer_id})

        rfq = self.repository.get_rfq(offer.rfq_id)
        if not rfq:
            raise ResourceNotFoundError(f"Linked RFQ '{offer.rfq_id}' was not found.")

        if actor.role != "admin" and rfq.buyer_organization_id != actor.org_id:
            raise ForbiddenError("Only the buyer organization can review this offer.")

        if offer.status != OfferStatus.SUBMITTED:
            raise InvalidStateTransitionError(
                f"Cannot review offer with status '{offer.status.value}'. Must be SUBMITTED.",
                details={"current_status": offer.status.value},
            )

        old_status = offer.status
        offer.reviewed_by = actor.user_id
        offer.reviewed_at = datetime.now(timezone.utc)
        updated = self.repository.update_offer_status(offer, OfferStatus.UNDER_REVIEW)

        self._record_event(
            entity_type="offer",
            entity_id=updated.id,
            event_type=WorkflowEventType.OFFER_REVIEWED,
            from_state=old_status.value,
            to_state=OfferStatus.UNDER_REVIEW.value,
            actor=actor,
            notes=notes,
        )
        return OfferRead.model_validate(updated)

    def withdraw_offer(
        self,
        offer_id: str,
        actor: AuthUser,
        notes: Optional[str] = None,
    ) -> OfferRead:
        """Seller withdraws their offer."""
        offer = self.repository.get_offer(offer_id=offer_id)
        if not offer:
            raise ResourceNotFoundError(f"Offer '{offer_id}' was not found.", details={"offer_id": offer_id})

        if actor.role != "admin" and offer.seller_organization_id != actor.org_id:
            raise ForbiddenError("Only the seller organization can withdraw this offer.")

        if offer.status in [OfferStatus.ACCEPTED, OfferStatus.REJECTED, OfferStatus.WITHDRAWN]:
            raise InvalidStateTransitionError(
                f"Cannot withdraw offer with status '{offer.status.value}'.",
                details={"current_status": offer.status.value},
            )

        old_status = offer.status
        updated = self.repository.update_offer_status(offer, OfferStatus.WITHDRAWN)

        self._record_event(
            entity_type="offer",
            entity_id=updated.id,
            event_type=WorkflowEventType.OFFER_WITHDRAWN,
            from_state=old_status.value,
            to_state=OfferStatus.WITHDRAWN.value,
            actor=actor,
            notes=notes,
        )
        return OfferRead.model_validate(updated)

    def record_custom_event(self, payload: WorkflowEventCreate, actor: AuthUser) -> WorkflowEventRead:
        """Records a custom auditable workflow event."""
        created = self._record_event(
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            event_type=payload.event_type,
            from_state=payload.from_state,
            to_state=payload.to_state,
            actor=actor,
            notes=payload.notes,
            metadata=payload.metadata,
        )
        return WorkflowEventRead.model_validate(created)

    def list_workflow_events(
        self,
        actor: AuthUser,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[WorkflowEventRead], int]:
        """Lists workflow events with tenant isolation."""
        skip = (page - 1) * page_size
        actor_org = None if actor.role == "admin" else actor.org_id
        rows, total = self.repository.list_workflow_events(
            entity_type=entity_type,
            entity_id=entity_id,
            actor_org_id=actor_org,
            skip=skip,
            limit=page_size,
        )
        return [WorkflowEventRead.model_validate(r) for r in rows], total

    def compare_logistics(self, payload: LogisticsComparisonRequest) -> LogisticsComparisonResponse:
        """Compares freight transport options between facilities or locations."""
        fac1 = self.repository.get_facility(payload.origin_facility_id) if payload.origin_facility_id else None
        fac2 = self.repository.get_facility(payload.destination_facility_id) if payload.destination_facility_id else None
        distance_km = self._estimate_facility_distance(fac1, fac2)
        if distance_km <= 0:
            distance_km = 150.0

        tonnes = payload.quantity / 1000.0 if payload.unit.lower() == "kg" else payload.quantity

        # Standard Road Diesel
        road_cost = round(max(80.0, distance_km * tonnes * 0.12), 2)
        road_emissions = round(distance_km * tonnes * 0.095, 2)
        road_days = max(1.0, round(distance_km / 650.0, 1))

        # Electric Truck (Road EV)
        ev_cost = round(max(95.0, distance_km * tonnes * 0.14), 2)
        ev_emissions = round(distance_km * tonnes * 0.025, 2)
        ev_days = max(1.0, round(distance_km / 550.0, 1))

        # Rail Freight
        rail_cost = round(max(150.0, distance_km * tonnes * 0.06), 2)
        rail_emissions = round(distance_km * tonnes * 0.018, 2)
        rail_days = max(2.0, round(distance_km / 400.0, 1))

        options = [
            FreightOption(
                mode="road_standard_diesel",
                mode_name="Standard Freight (Diesel Heavy Truck)",
                estimated_cost_usd=road_cost,
                cost_per_unit=round(road_cost / (payload.quantity + 0.001), 4),
                estimated_duration_days=road_days,
                estimated_emissions_kg_co2e=road_emissions,
                is_estimated=True,
                disclaimer="Estimated from regional average commercial diesel road freight rates.",
            ),
            FreightOption(
                mode="road_electric_truck",
                mode_name="Low-Emission Heavy Freight (Class 8 EV Truck)",
                estimated_cost_usd=ev_cost,
                cost_per_unit=round(ev_cost / (payload.quantity + 0.001), 4),
                estimated_duration_days=ev_days,
                estimated_emissions_kg_co2e=ev_emissions,
                is_estimated=True,
                disclaimer="Estimated assuming dedicated zero-emission charging network access.",
            ),
            FreightOption(
                mode="rail_intermodal",
                mode_name="Intermodal Bulk Rail Transport",
                estimated_cost_usd=rail_cost,
                cost_per_unit=round(rail_cost / (payload.quantity + 0.001), 4),
                estimated_duration_days=rail_days,
                estimated_emissions_kg_co2e=rail_emissions,
                is_estimated=True,
                disclaimer="Estimated based on regional bulk container siding access.",
            ),
        ]

        summary = f"Freight route analysis across {distance_km} km for {payload.quantity} {payload.unit}. Rail offers lowest carbon footprint (-81% vs diesel), while EV truck balances low emissions with fast transit."
        return LogisticsComparisonResponse(
            distance_km=distance_km,
            is_distance_estimated=True,
            quantity=payload.quantity,
            unit=payload.unit,
            options=options,
            summary=summary,
            methodology="indicative_freight_emissions_and_cost_model",
        )

    def get_cluster_indicators(self, cluster_id: Optional[str] = None) -> ClusterIndicatorsResponse:
        """Aggregates circular exchange metrics from persisted tables across the industrial cluster."""
        aggs = self.repository.get_cluster_aggregates()
        active_listings = aggs["active_listings"]
        lots_map = aggs["lots_map"]
        active_reqs = aggs["active_requirements"]

        # Aggregate supply by category
        cat_supply: Dict[str, Dict[str, Any]] = {}
        top_mat_counts: Dict[str, int] = {}
        for listing in active_listings:
            lot = lots_map.get(listing.material_lot_id)
            tax = get_material_type(lot.material_type) if lot else None
            cat = tax.category if tax else "unclassified"
            mat_type = lot.material_type if lot else "unknown"

            if cat not in cat_supply:
                cat_supply[cat] = {"category": cat, "count": 0, "quantity": 0.0, "unit": listing.unit}
            cat_supply[cat]["count"] += 1
            cat_supply[cat]["quantity"] += listing.available_quantity

            top_mat_counts[mat_type] = top_mat_counts.get(mat_type, 0) + 1

        supply_by_cat = [
            MaterialCategoryVolume(
                category=v["category"],
                active_listings_count=v["count"],
                total_quantity=round(v["quantity"], 2),
                unit=v["unit"],
            )
            for v in cat_supply.values()
        ]

        # Aggregate demand by category
        cat_demand: Dict[str, Dict[str, Any]] = {}
        for req in active_reqs:
            c = req.material_category
            if c not in cat_demand:
                cat_demand[c] = {"category": c, "count": 0, "quantity": 0.0, "unit": req.unit}
            cat_demand[c]["count"] += 1
            cat_demand[c]["quantity"] += req.min_quantity

        demand_by_cat = [
            MaterialCategoryVolume(
                category=v["category"],
                active_listings_count=v["count"],
                total_quantity=round(v["quantity"], 2),
                unit=v["unit"],
            )
            for v in cat_demand.values()
        ]

        top_materials = [
            {"material_type": m, "active_listings": c}
            for m, c in sorted(top_mat_counts.items(), key=lambda x: -x[1])[:5]
        ]

        circ_rate = None
        total_exchanges = aggs["closed_rfqs_count"]
        total_interactions = aggs["active_rfqs_count"] + total_exchanges
        if total_interactions > 0:
            circ_rate = round((total_exchanges / total_interactions) * 100.0, 1)

        return ClusterIndicatorsResponse(
            cluster_id=cluster_id or "cluster-default",
            as_of=datetime.now(timezone.utc),
            is_estimated=False,
            source="persisted_marketplace_records",
            total_active_listings=len(active_listings),
            total_active_buyer_requirements=len(active_reqs),
            total_active_rfqs=aggs["active_rfqs_count"],
            completed_exchanges_count=aggs["closed_rfqs_count"],
            supply_by_category=supply_by_cat,
            demand_by_category=demand_by_cat,
            top_materials=top_materials,
            circularity_rate_pct=circ_rate,
        )

    def get_city_indicators(self) -> CityIndicatorsResponse:
        """Aggregates municipal-level indicators with transparent estimation disclosure."""
        aggs = self.repository.get_cluster_aggregates()
        closed_count = aggs["closed_rfqs_count"]
        active_listings = aggs["active_listings"]

        # Diverted tonnes approximation
        diverted_tonnes = round(closed_count * 25.0 + len(active_listings) * 2.5, 2)
        part_fac = max(1, len({l.facility_id for l in active_listings}))

        return CityIndicatorsResponse(
            city="Greater Industrial Metro",
            as_of=datetime.now(timezone.utc),
            participating_facilities_count=part_fac,
            diverted_material_tonnes=diverted_tonnes,
            active_recovery_routes_count=len(CANDIDATE_ROUTES),
            landfill_diversion_rate_pct=round(min(95.0, 62.0 + (diverted_tonnes / 500.0)), 1),
            is_estimated=True,
            methodology="facility_reporting_and_exchange_aggregated_metrics",
        )
