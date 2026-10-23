import uuid
import pytest

from strata.core.auth import AuthUser
from strata.core.errors import (
    ForbiddenError,
    InvalidStateTransitionError,
    ResourceNotFoundError,
    ValidationError,
)
from strata.domain.marketplace.models import Listing
from strata.domain.marketplace.repository import MarketplaceRepository
from strata.domain.marketplace.schemas import (
    ListingStatus,
    ListingVisibility,
    OfferCreate,
    OfferStatus,
    RFQCreate,
    RFQStatus,
    WorkflowEventType,
)
from strata.domain.marketplace.service import MarketplaceService


@pytest.fixture
def test_users():
    seller_org = str(uuid.uuid4())
    buyer_org = str(uuid.uuid4())
    other_org = str(uuid.uuid4())

    return {
        "seller_operator": AuthUser(user_id=str(uuid.uuid4()), org_id=seller_org, role="facility_operator"),
        "seller_manager": AuthUser(user_id=str(uuid.uuid4()), org_id=seller_org, role="facility_manager"),
        "buyer_operator": AuthUser(user_id=str(uuid.uuid4()), org_id=buyer_org, role="facility_operator"),
        "buyer_manager": AuthUser(user_id=str(uuid.uuid4()), org_id=buyer_org, role="facility_manager"),
        "buyer_admin": AuthUser(user_id=str(uuid.uuid4()), org_id=buyer_org, role="buyer_admin"),
        "unrelated_user": AuthUser(user_id=str(uuid.uuid4()), org_id=other_org, role="buyer_admin"),
        "platform_admin": AuthUser(user_id=str(uuid.uuid4()), org_id=other_org, role="admin"),
    }


@pytest.fixture
def active_listing(db_session, test_users):
    repo = MarketplaceRepository(db_session)
    listing = Listing(
        material_lot_id=str(uuid.uuid4()),
        organization_id=test_users["seller_operator"].org_id,
        facility_id=str(uuid.uuid4()),
        visibility=ListingVisibility.PUBLIC,
        asking_price_per_unit=50.0,
        currency="USD",
        available_quantity=500.0,
        unit="kg",
        status=ListingStatus.ACTIVE,
    )
    return repo.add_listing(listing)


class TestListingLifecycle:
    def test_listing_pause_and_publish_transitions(self, db_session, test_users, active_listing):
        service = MarketplaceService(db_session)
        seller = test_users["seller_operator"]

        # ACTIVE -> PAUSED
        paused = service.update_listing_status(
            listing_id=active_listing.id,
            new_status=ListingStatus.PAUSED,
            actor=seller,
            notes="Temporarily paused for maintenance",
        )
        assert paused.status == ListingStatus.PAUSED

        # PAUSED -> ACTIVE (publish/resume)
        resumed = service.update_listing_status(
            listing_id=active_listing.id,
            new_status=ListingStatus.ACTIVE,
            actor=seller,
            notes="Resumed operations",
        )
        assert resumed.status == ListingStatus.ACTIVE

        # ACTIVE -> WITHDRAWN
        withdrawn = service.update_listing_status(
            listing_id=active_listing.id,
            new_status=ListingStatus.WITHDRAWN,
            actor=seller,
            notes="Withdrawing listing",
        )
        assert withdrawn.status == ListingStatus.WITHDRAWN

    def test_listing_invalid_transitions(self, db_session, test_users, active_listing):
        service = MarketplaceService(db_session)
        seller = test_users["seller_operator"]

        # Move to WITHDRAWN
        service.update_listing_status(
            listing_id=active_listing.id,
            new_status=ListingStatus.WITHDRAWN,
            actor=seller,
        )

        # Attempt to resume from WITHDRAWN -> raises 422
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            service.update_listing_status(
                listing_id=active_listing.id,
                new_status=ListingStatus.ACTIVE,
                actor=seller,
            )
        assert exc_info.value.status_code == 422

    def test_listing_status_tenant_isolation(self, db_session, test_users, active_listing):
        service = MarketplaceService(db_session)
        buyer = test_users["buyer_operator"]

        # Other organization cannot modify listing status
        with pytest.raises(ResourceNotFoundError):
            service.update_listing_status(
                listing_id=active_listing.id,
                new_status=ListingStatus.PAUSED,
                actor=buyer,
            )


class TestRFQCreationAndApprovalGates:
    def test_rfq_create_draft_and_submit(self, db_session, test_users, active_listing):
        service = MarketplaceService(db_session)
        buyer = test_users["buyer_operator"]

        payload = RFQCreate(
            listing_id=active_listing.id,
            buyer_facility_id=str(uuid.uuid4()),
            requested_quantity=100.0,
            unit="kg",
            target_price_per_unit=45.0,
            notes="Need 100kg batch",
        )
        rfq = service.create_rfq(payload, actor=buyer)
        assert rfq.status == RFQStatus.DRAFT
        assert rfq.seller_organization_id == active_listing.organization_id

        # Submit for approval
        submitted = service.submit_rfq_for_approval(rfq.id, actor=buyer)
        assert submitted.status == RFQStatus.PENDING_APPROVAL

    def test_rfq_create_directly_pending_approval(self, db_session, test_users, active_listing):
        service = MarketplaceService(db_session)
        buyer = test_users["buyer_operator"]

        payload = RFQCreate(
            listing_id=active_listing.id,
            buyer_facility_id=str(uuid.uuid4()),
            requested_quantity=100.0,
            unit="kg",
            submit_for_approval=True,
        )
        rfq = service.create_rfq(payload, actor=buyer)
        assert rfq.status == RFQStatus.PENDING_APPROVAL

    def test_rfq_approval_role_gate(self, db_session, test_users, active_listing):
        service = MarketplaceService(db_session)
        buyer_operator = test_users["buyer_operator"]
        buyer_manager = test_users["buyer_manager"]

        payload = RFQCreate(
            listing_id=active_listing.id,
            buyer_facility_id=str(uuid.uuid4()),
            requested_quantity=100.0,
            unit="kg",
            submit_for_approval=True,
        )
        rfq = service.create_rfq(payload, actor=buyer_operator)

        # Buyer operator lacks permission to approve
        with pytest.raises(ForbiddenError) as exc_info:
            service.approve_rfq(rfq.id, actor=buyer_operator)
        assert exc_info.value.status_code == 403

        # Buyer manager approves RFQ
        approved = service.approve_rfq(rfq.id, actor=buyer_manager)
        assert approved.status == RFQStatus.OPEN

    def test_rfq_cannot_target_inactive_listing(self, db_session, test_users, active_listing):
        service = MarketplaceService(db_session)
        seller = test_users["seller_operator"]
        buyer = test_users["buyer_operator"]

        # Pause listing
        service.update_listing_status(active_listing.id, ListingStatus.PAUSED, actor=seller)

        payload = RFQCreate(
            listing_id=active_listing.id,
            buyer_facility_id=str(uuid.uuid4()),
            requested_quantity=50.0,
            unit="kg",
        )
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            service.create_rfq(payload, actor=buyer)
        assert exc_info.value.status_code == 422

    def test_rfq_cannot_target_own_listing(self, db_session, test_users, active_listing):
        service = MarketplaceService(db_session)
        seller = test_users["seller_operator"]

        payload = RFQCreate(
            listing_id=active_listing.id,
            buyer_facility_id=str(uuid.uuid4()),
            requested_quantity=50.0,
            unit="kg",
        )
        with pytest.raises(ValidationError):
            service.create_rfq(payload, actor=seller)


class TestOfferWorkflowAndAcceptanceGates:
    @pytest.fixture
    def open_rfq(self, db_session, test_users, active_listing):
        service = MarketplaceService(db_session)
        buyer_operator = test_users["buyer_operator"]
        buyer_manager = test_users["buyer_manager"]

        payload = RFQCreate(
            listing_id=active_listing.id,
            buyer_facility_id=str(uuid.uuid4()),
            requested_quantity=100.0,
            unit="kg",
            target_price_per_unit=45.0,
            submit_for_approval=True,
        )
        rfq = service.create_rfq(payload, actor=buyer_operator)
        return service.approve_rfq(rfq.id, actor=buyer_manager)

    def test_offer_submission_and_revision(self, db_session, test_users, open_rfq):
        service = MarketplaceService(db_session)
        seller = test_users["seller_operator"]

        offer_payload = OfferCreate(
            offered_quantity=100.0,
            unit="kg",
            price_per_unit=48.0,
            terms="FOB Origin, Net 30",
        )
        offer = service.submit_offer(open_rfq.id, offer_payload, actor=seller)
        assert offer.status == OfferStatus.SUBMITTED
        assert offer.price_per_unit == 48.0

        # Seller revises offer
        revised_payload = OfferCreate(
            offered_quantity=100.0,
            unit="kg",
            price_per_unit=46.5,
            terms="FOB Origin, Net 30, discount applied",
        )
        revised = service.revise_offer(offer.id, revised_payload, actor=seller)
        assert revised.status == OfferStatus.REVISED
        assert revised.price_per_unit == 46.5

    def test_offer_submission_rejected_if_rfq_not_open(self, db_session, test_users, active_listing):
        service = MarketplaceService(db_session)
        buyer = test_users["buyer_operator"]
        seller = test_users["seller_operator"]

        payload = RFQCreate(
            listing_id=active_listing.id,
            buyer_facility_id=str(uuid.uuid4()),
            requested_quantity=100.0,
            unit="kg",
            submit_for_approval=False, # DRAFT
        )
        draft_rfq = service.create_rfq(payload, actor=buyer)

        offer_payload = OfferCreate(offered_quantity=100.0, unit="kg", price_per_unit=50.0)
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            service.submit_offer(draft_rfq.id, offer_payload, actor=seller)
        assert exc_info.value.status_code == 422

    def test_offer_submission_unauthorized_party(self, db_session, test_users, open_rfq):
        service = MarketplaceService(db_session)
        unrelated = test_users["unrelated_user"]

        offer_payload = OfferCreate(offered_quantity=100.0, unit="kg", price_per_unit=50.0)
        with pytest.raises(ForbiddenError) as exc_info:
            service.submit_offer(open_rfq.id, offer_payload, actor=unrelated)
        assert exc_info.value.status_code == 403

    def test_offer_acceptance_gate_and_rfq_closure(self, db_session, test_users, open_rfq):
        service = MarketplaceService(db_session)
        seller = test_users["seller_operator"]
        buyer_operator = test_users["buyer_operator"]
        buyer_manager = test_users["buyer_manager"]
        buyer_admin = test_users["buyer_admin"]

        # Seller submits two competing/alternative offers
        offer1 = service.submit_offer(open_rfq.id, OfferCreate(offered_quantity=100.0, unit="kg", price_per_unit=48.0), actor=seller)
        offer2 = service.submit_offer(open_rfq.id, OfferCreate(offered_quantity=100.0, unit="kg", price_per_unit=47.0), actor=seller)

        # Buyer operator or manager cannot accept binding offer
        with pytest.raises(ForbiddenError):
            service.accept_offer(offer2.id, actor=buyer_operator)
        with pytest.raises(ForbiddenError):
            service.accept_offer(offer2.id, actor=buyer_manager)

        # Buyer admin accepts offer 2
        accepted = service.accept_offer(offer2.id, actor=buyer_admin, notes="Best price accepted")
        assert accepted.status == OfferStatus.ACCEPTED

        # RFQ is now CLOSED
        rfq = service.get_rfq(open_rfq.id, actor=buyer_admin)
        assert rfq.status == RFQStatus.CLOSED

        # Offer 1 was automatically marked REJECTED
        all_offers = service.list_offers_for_rfq(open_rfq.id, actor=buyer_admin)
        offer1_updated = next(o for o in all_offers if o.id == offer1.id)
        assert offer1_updated.status == OfferStatus.REJECTED

        # Cannot accept an offer on a CLOSED RFQ
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            service.accept_offer(offer1.id, actor=buyer_admin)
        assert exc_info.value.status_code == 422

    def test_offer_rejection_workflow(self, db_session, test_users, open_rfq):
        service = MarketplaceService(db_session)
        seller = test_users["seller_operator"]
        buyer_admin = test_users["buyer_admin"]

        offer = service.submit_offer(open_rfq.id, OfferCreate(offered_quantity=100.0, unit="kg", price_per_unit=60.0), actor=seller)
        rejected = service.reject_offer(offer.id, actor=buyer_admin, notes="Price too high")
        assert rejected.status == OfferStatus.REJECTED

        # Cannot reject an already rejected offer
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            service.reject_offer(offer.id, actor=buyer_admin)
        assert exc_info.value.status_code == 422


class TestWorkflowAuditEvents:
    def test_audit_event_history_recorded(self, db_session, test_users, active_listing):
        service = MarketplaceService(db_session)
        buyer_operator = test_users["buyer_operator"]
        buyer_manager = test_users["buyer_manager"]
        buyer_admin = test_users["buyer_admin"]
        seller = test_users["seller_operator"]

        # Step 1: Create RFQ
        rfq = service.create_rfq(
            RFQCreate(listing_id=active_listing.id, buyer_facility_id=str(uuid.uuid4()), requested_quantity=100.0, unit="kg"),
            actor=buyer_operator,
        )
        # Step 2: Submit RFQ
        service.submit_rfq_for_approval(rfq.id, actor=buyer_operator)
        # Step 3: Approve RFQ
        service.approve_rfq(rfq.id, actor=buyer_manager)
        # Step 4: Submit Offer
        offer = service.submit_offer(rfq.id, OfferCreate(offered_quantity=100.0, unit="kg", price_per_unit=49.0), actor=seller)
        # Step 5: Accept Offer
        service.accept_offer(offer.id, actor=buyer_admin)

        # Inspect history for RFQ
        rfq_history = service.get_workflow_history(rfq.id, actor=buyer_admin)
        event_types = [e.event_type for e in rfq_history]
        assert WorkflowEventType.RFQ_CREATED.value in event_types
        assert WorkflowEventType.RFQ_SUBMITTED.value in event_types
        assert WorkflowEventType.RFQ_APPROVED.value in event_types
        assert WorkflowEventType.RFQ_CANCELLED.value in event_types # Closed transition

        # Inspect history for Offer
        offer_history = service.get_workflow_history(offer.id, actor=buyer_admin)
        offer_event_types = [e.event_type for e in offer_history]
        assert WorkflowEventType.OFFER_SUBMITTED.value in offer_event_types
        assert WorkflowEventType.OFFER_ACCEPTED.value in offer_event_types
