"""
Discovery provider interfaces for STRATA.

DiscoveryProvider abstracts how STRATA finds candidate recovery routes and
gathers publicly stated receiver capability claims.

Two implementations:
  - TinyFishDiscoveryProvider: real web-discovery using the TinyFish API
  - FakeDiscoveryProvider: deterministic fixtures for tests and offline dev

Architecture constraints:
  - Publicly retrieved capability claims are tagged PUBLICLY_STATED / UNVERIFIED.
  - A publicly stated claim does NOT imply acceptance of a specific lot.
  - Provider failures must be surfaced explicitly (no silent fabrication).
"""

import logging
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

logger = logging.getLogger("strata.integrations.discovery")


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


class TinyFishDiscoveryProvider(DiscoveryProvider):
    """
    Real web-discovery provider using the TinyFish Search and Fetch APIs.

    Search strategy:
      1. Routes are always sourced from the deterministic CANDIDATE_ROUTES catalog
         (routes are not invented from web searches).
      2. For each route, TinyFish is used to look up publicly stated capabilities
         of the named processor facility, which are stored as PUBLICLY_STATED /
         UNVERIFIED evidence records.

    Failure handling:
      - If TinyFish is unavailable or returns an error, the method logs the
        failure and returns an empty list (no evidence). It does NOT fabricate
        receiver claims.

    Args:
        api_key: Override for TINYFISH_API_KEY. Defaults to settings value.
        timeout: Override for TINYFISH_TIMEOUT_SECONDS. Defaults to settings value.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self._api_key = api_key
        self._timeout = timeout

    def _get_adapter(self):
        """Lazily instantiates the TinyFish adapter (avoids import-time config reads in tests)."""
        from strata.integrations.tinyfish import TinyFishAdapter, TinyFishProviderError  # noqa: F401
        return TinyFishAdapter(api_key=self._api_key, timeout=self._timeout)

    def discover_routes(self, material_type: str) -> List[CandidateRoute]:
        """
        Returns candidate routes from the authoritative deterministic catalog.
        Web discovery is not used for route identification to ensure reproducibility.
        """
        return get_candidate_routes_for_material(material_type)

    def fetch_receiver_claims(self, route: CandidateRoute) -> List[EvidenceRecordCreate]:
        """
        Searches TinyFish for publicly stated capabilities of the route's processor facility.
        Returns empty list on provider failure (does not fabricate claims).
        """
        from strata.integrations.tinyfish import TinyFishProviderError

        query = (
            f'"{route.processor_facility_name}" {route.target_material_type} '
            f"recycling processing capability industrial"
        )
        purpose = (
            f"Find publicly stated processing capabilities of {route.processor_facility_name} "
            f"for {route.target_material_type} as secondary receiver evidence."
        )

        try:
            adapter = self._get_adapter()
            evidence = adapter.search_and_normalize_evidence(
                query=query,
                claim_subject="receiver_capability",
                purpose=purpose,
            )
            logger.info(
                "TinyFish discovered %d public claims for route %s (processor: %s)",
                len(evidence),
                route.route_id,
                route.processor_facility_name,
            )
            return evidence

        except TinyFishProviderError as exc:
            logger.warning(
                "TinyFish receiver claims lookup failed for route %s: %s. "
                "Returning empty evidence list (no fabrication).",
                route.route_id,
                exc,
            )
            return []
        except Exception as exc:
            logger.error(
                "Unexpected error during TinyFish discovery for route %s: %s",
                route.route_id,
                exc,
                exc_info=True,
            )
            return []


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


def get_discovery_provider() -> DiscoveryProvider:
    """
    Factory: returns the appropriate discovery provider based on current configuration.

    - If TINYFISH_API_KEY is set: TinyFishDiscoveryProvider
    - Otherwise: FakeDiscoveryProvider (no external calls; safe for tests)
    """
    from strata.core.config import settings

    if settings.tinyfish_configured:
        logger.info("Using TinyFish discovery provider.")
        return TinyFishDiscoveryProvider()
    logger.debug("No TinyFish API key configured — using FakeDiscoveryProvider.")
    return FakeDiscoveryProvider()
