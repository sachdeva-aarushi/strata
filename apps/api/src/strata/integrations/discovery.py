from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import List, Optional

from strata.domain.qualification.routes import CandidateRoute, get_candidate_routes_for_material
from strata.schemas.evidence import (
    EvidenceProvenance,
    EvidenceRecordCreate,
    EvidenceVerificationState,
    ExtractionMethod,
)


class DiscoveryProvider(ABC):
    """
    Interface for discovering candidate routes and receiver capability evidence.
    Abstracts web research (TinyFish), registry crawling, and directory lookups.
    """

    @abstractmethod
    def discover_routes(self, material_type: str) -> List[CandidateRoute]:
        """Finds potential receiver pathways for a given material type."""
        pass

    @abstractmethod
    def fetch_receiver_claims(self, route: CandidateRoute) -> List[EvidenceRecordCreate]:
        """
        Gathers publicly stated capability claims for a candidate route receiver.
        Note: Publicly stated claims do not prove acceptance of a specific lot or current capacity.
        """
        pass


class FakeDiscoveryProvider(DiscoveryProvider):
    """
    Deterministic fake discovery provider returning synthetic candidate routes and fixtures.
    All synthetic evidence is strictly tagged with SYNTHETIC_DEMO provenance.
    """

    def discover_routes(self, material_type: str) -> List[CandidateRoute]:
        return get_candidate_routes_for_material(material_type)

    def fetch_receiver_claims(self, route: CandidateRoute) -> List[EvidenceRecordCreate]:
        """Returns synthetic evidence claims simulating web discovery of receiver capability."""
        return [
            EvidenceRecordCreate(
                claim_subject="receiver_capability",
                claim_text=f"{route.processor_facility_name} operates secondary processing lines for {route.target_material_type}.",
                source_url=f"https://synthetic-directory.circularity.test/processors/{route.route_id}",
                source_title=f"{route.processor_facility_name} Public Capabilities Sheet",
                source_type="web",
                extraction_method=ExtractionMethod.TINYFISH_FETCH,
                provenance=EvidenceProvenance.PUBLICLY_STATED,
                verification_state=EvidenceVerificationState.UNVERIFIED,
                supporting_passage=f"Accepts {route.target_material_type} in accordance with standard industrial technical specifications.",
            )
        ]
