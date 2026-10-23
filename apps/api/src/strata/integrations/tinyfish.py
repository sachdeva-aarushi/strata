"""
TinyFish web-research adapter for STRATA.

Wraps two verified TinyFish REST APIs:
  - Search: GET  https://api.search.tinyfish.ai  (query params)
  - Fetch:  POST https://api.fetch.tinyfish.ai   (JSON body, urls[])

Authentication: X-API-Key header.
Rate limits: ~30 req/min (search), ~150 URL/min (fetch) on the free tier.

IMPORTANT architectural constraints:
  - This adapter NEVER silently falls back to fabricated results on failure.
  - Publicly retrieved text is tagged PUBLICLY_STATED and UNVERIFIED.
  - Any provider-level error (timeout, 4xx, 5xx, malformed JSON) raises
    TinyFishProviderError, which callers must handle explicitly.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from strata.core.config import settings
from strata.schemas.evidence import (
    EvidenceProvenance,
    EvidenceRecordCreate,
    EvidenceVerificationState,
    ExtractionMethod,
)

logger = logging.getLogger("strata.integrations.tinyfish")

# Verified TinyFish API base URLs (as of 2026-10)
_SEARCH_BASE_URL = "https://api.search.tinyfish.ai"
_FETCH_BASE_URL = "https://api.fetch.tinyfish.ai"

# Maximum URLs per fetch request (TinyFish documented limit)
_MAX_FETCH_URLS_PER_REQUEST = 10


class TinyFishProviderError(Exception):
    """Raised when a TinyFish API call fails unrecoverably."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class TinyFishSearchResult:
    """Structured representation of a single TinyFish search result entry."""

    __slots__ = ("position", "site_name", "title", "snippet", "url")

    def __init__(
        self,
        position: int,
        site_name: str,
        title: str,
        snippet: str,
        url: str,
    ) -> None:
        self.position = position
        self.site_name = site_name
        self.title = title
        self.snippet = snippet
        self.url = url


class TinyFishFetchResult:
    """Structured representation of a single TinyFish page-fetch result."""

    __slots__ = ("url", "final_url", "title", "description", "text")

    def __init__(
        self,
        url: str,
        final_url: str,
        title: str,
        description: str,
        text: str,
    ) -> None:
        self.url = url
        self.final_url = final_url
        self.title = title
        self.description = description
        self.text = text


class TinyFishAdapter:
    """
    HTTP adapter for TinyFish Search and Fetch APIs.

    Raises TinyFishProviderError on any network, auth, rate-limit, or
    parse failure. Callers decide whether to propagate or degrade gracefully.

    Args:
        api_key: TinyFish API key.  Defaults to ``settings.TINYFISH_API_KEY``.
        timeout: Per-request timeout in seconds.
        max_results: Max search results to request.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        max_results: Optional[int] = None,
    ) -> None:
        self._api_key: str = api_key or settings.TINYFISH_API_KEY or ""
        self._timeout = timeout if timeout is not None else settings.TINYFISH_TIMEOUT_SECONDS
        self._max_results = max_results if max_results is not None else settings.TINYFISH_MAX_SEARCH_RESULTS

        if not self._api_key:
            raise TinyFishProviderError(
                "TinyFish API key is not configured. "
                "Set TINYFISH_API_KEY in your environment."
            )

    def _headers(self) -> dict:
        return {
            "X-API-Key": self._api_key,
            "Accept": "application/json",
        }

    def search(
        self,
        query: str,
        purpose: Optional[str] = None,
        location: str = "US",
    ) -> List[TinyFishSearchResult]:
        """
        Executes a TinyFish web search and returns ranked results.

        GET https://api.search.tinyfish.ai
          ?query=<query>&purpose=<purpose>&location=<location>

        Raises:
            TinyFishProviderError: on any HTTP or parse failure.
        """
        params: dict = {"query": query, "location": location}
        if purpose:
            params["purpose"] = purpose

        logger.debug("TinyFish search: %r", query)
        try:
            response = httpx.get(
                _SEARCH_BASE_URL,
                params=params,
                headers=self._headers(),
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise TinyFishProviderError(
                f"TinyFish search timed out after {self._timeout}s: {exc}"
            ) from exc
        except httpx.RequestError as exc:
            raise TinyFishProviderError(
                f"TinyFish search request failed: {exc}"
            ) from exc

        if response.status_code == 401:
            raise TinyFishProviderError(
                "TinyFish authentication failed — invalid or expired API key.",
                status_code=401,
            )
        if response.status_code == 429:
            raise TinyFishProviderError(
                "TinyFish rate limit exceeded. Back off and retry.",
                status_code=429,
            )
        if response.status_code >= 400:
            raise TinyFishProviderError(
                f"TinyFish search returned HTTP {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )

        try:
            data = response.json()
        except Exception as exc:
            raise TinyFishProviderError(
                f"TinyFish search returned non-JSON response: {exc}"
            ) from exc

        raw_results = data.get("results", [])
        if not isinstance(raw_results, list):
            raise TinyFishProviderError(
                f"TinyFish search response 'results' field is not a list: {type(raw_results)}"
            )

        results: List[TinyFishSearchResult] = []
        for item in raw_results[: self._max_results]:
            try:
                results.append(
                    TinyFishSearchResult(
                        position=int(item.get("position", 0)),
                        site_name=str(item.get("site_name", "")),
                        title=str(item.get("title", "")),
                        snippet=str(item.get("snippet", "")),
                        url=str(item.get("url", "")),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping malformed TinyFish search result item: %s", exc)

        logger.info(
            "TinyFish search returned %d results for query %r",
            len(results),
            query,
        )
        return results

    def fetch(
        self,
        urls: List[str],
        purpose: Optional[str] = None,
        format: str = "markdown",
    ) -> List[TinyFishFetchResult]:
        """
        Fetches and extracts clean text from one or more URLs.

        POST https://api.fetch.tinyfish.ai
          Body: {"urls": [...], "purpose": "...", "format": "markdown"}

        Maximum 10 URLs per request (TinyFish documented limit).

        Raises:
            TinyFishProviderError: on any HTTP or parse failure.
        """
        if not urls:
            return []
        if len(urls) > _MAX_FETCH_URLS_PER_REQUEST:
            raise TinyFishProviderError(
                f"TinyFish fetch accepts at most {_MAX_FETCH_URLS_PER_REQUEST} URLs per request; "
                f"{len(urls)} were provided."
            )

        body: dict = {"urls": urls, "format": format}
        if purpose:
            body["purpose"] = purpose

        logger.debug("TinyFish fetch: %d URL(s)", len(urls))
        try:
            response = httpx.post(
                _FETCH_BASE_URL,
                json=body,
                headers=self._headers(),
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise TinyFishProviderError(
                f"TinyFish fetch timed out after {self._timeout}s: {exc}"
            ) from exc
        except httpx.RequestError as exc:
            raise TinyFishProviderError(
                f"TinyFish fetch request failed: {exc}"
            ) from exc

        if response.status_code == 401:
            raise TinyFishProviderError(
                "TinyFish authentication failed — invalid or expired API key.",
                status_code=401,
            )
        if response.status_code == 429:
            raise TinyFishProviderError(
                "TinyFish rate limit exceeded. Back off and retry.",
                status_code=429,
            )
        if response.status_code >= 400:
            raise TinyFishProviderError(
                f"TinyFish fetch returned HTTP {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )

        try:
            data = response.json()
        except Exception as exc:
            raise TinyFishProviderError(
                f"TinyFish fetch returned non-JSON response: {exc}"
            ) from exc

        raw_results = data.get("results", [])
        if not isinstance(raw_results, list):
            raise TinyFishProviderError(
                f"TinyFish fetch response 'results' field is not a list: {type(raw_results)}"
            )

        results: List[TinyFishFetchResult] = []
        for item in raw_results:
            try:
                results.append(
                    TinyFishFetchResult(
                        url=str(item.get("url", "")),
                        final_url=str(item.get("final_url", item.get("url", ""))),
                        title=str(item.get("title", "")),
                        description=str(item.get("description", "")),
                        text=str(item.get("text", "")),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                logger.warning("Skipping malformed TinyFish fetch result item: %s", exc)

        # Log any per-URL errors reported by TinyFish
        for err in data.get("errors", []):
            logger.warning("TinyFish fetch error for URL %s: %s", err.get("url"), err.get("message"))

        logger.info("TinyFish fetch returned %d page(s)", len(results))
        return results

    # -------------------------------------------------------------------------
    # High-level helper: normalize to STRATA evidence contracts
    # -------------------------------------------------------------------------

    def search_and_normalize_evidence(
        self,
        query: str,
        claim_subject: str,
        lot_id: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> List[EvidenceRecordCreate]:
        """
        Runs a TinyFish search and normalizes results to EvidenceRecordCreate.

        All records are tagged:
          - extraction_method = TINYFISH_FETCH
          - provenance = PUBLICLY_STATED
          - verification_state = UNVERIFIED

        Publicly retrieved text is *never* treated as independently verified.
        The caller is responsible for any subsequent verification steps.

        Returns an empty list (not an error) when no results are found.
        Raises TinyFishProviderError on API-level failure.
        """
        retrieved_at = datetime.now(timezone.utc)
        search_results = self.search(query=query, purpose=purpose)
        if not search_results:
            return []

        evidence: List[EvidenceRecordCreate] = []
        for result in search_results:
            text = result.snippet
            content_hash = (
                hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None
            )
            evidence.append(
                EvidenceRecordCreate(
                    lot_id=lot_id,
                    claim_subject=claim_subject,
                    claim_text=text or f"Search result from {result.url}",
                    source_url=result.url,
                    source_title=result.title,
                    source_type="web",
                    retrieved_at=retrieved_at,
                    extraction_method=ExtractionMethod.TINYFISH_FETCH,
                    provenance=EvidenceProvenance.PUBLICLY_STATED,
                    verification_state=EvidenceVerificationState.UNVERIFIED,
                    supporting_passage=text[:500] if text else None,
                    content_hash=content_hash,
                )
            )

        return evidence

    def fetch_and_normalize_evidence(
        self,
        urls: List[str],
        claim_subject: str,
        lot_id: Optional[str] = None,
        purpose: Optional[str] = None,
    ) -> List[EvidenceRecordCreate]:
        """
        Fetches page content from the given URLs and normalizes to EvidenceRecordCreate.

        Same provenance tagging rules as ``search_and_normalize_evidence`` apply.
        """
        retrieved_at = datetime.now(timezone.utc)
        fetch_results = self.fetch(urls=urls, purpose=purpose)
        if not fetch_results:
            return []

        evidence: List[EvidenceRecordCreate] = []
        for page in fetch_results:
            # Use first 2000 chars of page text as the claim text
            page_text = (page.text or "").strip()
            claim_text = page_text[:2000] if page_text else f"Fetched page at {page.final_url}"
            content_hash = (
                hashlib.sha256(page_text.encode("utf-8")).hexdigest() if page_text else None
            )
            evidence.append(
                EvidenceRecordCreate(
                    lot_id=lot_id,
                    claim_subject=claim_subject,
                    claim_text=claim_text,
                    source_url=page.final_url,
                    source_title=page.title,
                    source_type="web",
                    retrieved_at=retrieved_at,
                    extraction_method=ExtractionMethod.TINYFISH_FETCH,
                    provenance=EvidenceProvenance.PUBLICLY_STATED,
                    verification_state=EvidenceVerificationState.UNVERIFIED,
                    supporting_passage=page.description[:500] if page.description else None,
                    content_hash=content_hash,
                )
            )

        return evidence
