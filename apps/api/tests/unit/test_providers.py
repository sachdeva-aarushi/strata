"""
Unit tests for TinyFish adapter and LLM adapter.

All tests use fake/mocked HTTP responses — no real network calls.
Tests explicitly document which assertions validate mock vs real provider behavior.
"""

import pytest
import httpx
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from strata.integrations.tinyfish import (
    TinyFishAdapter,
    TinyFishProviderError,
    TinyFishSearchResult,
    TinyFishFetchResult,
)
from strata.integrations.llm import (
    FakeLLMProvider,
    OpenAICompatibleLLMAdapter,
    LLMProviderError,
    get_llm_provider,
)
from strata.schemas.evidence import (
    EvidenceProvenance,
    EvidenceVerificationState,
    ExtractionMethod,
)


# =============================================================================
# TinyFish adapter tests (all use mocked HTTP — verified: MOCK)
# =============================================================================


class TestTinyFishAdapterInit:
    """Tests adapter construction. Verified with: MOCK (no network)."""

    def test_raises_without_api_key(self):
        """Adapter must refuse to construct without a key — avoids silent misconfiguration."""
        with pytest.raises(TinyFishProviderError, match="API key is not configured"):
            TinyFishAdapter(api_key="")

    def test_raises_with_none_api_key(self):
        with pytest.raises(TinyFishProviderError):
            TinyFishAdapter(api_key=None)

    def test_constructs_with_valid_key(self):
        adapter = TinyFishAdapter(api_key="tf_test_key_abc123")
        assert adapter is not None


class TestTinyFishSearch:
    """Tests the search method against mocked HTTP responses. Verified with: MOCK."""

    _VALID_SEARCH_RESPONSE = {
        "query": "aluminum scrap recycling",
        "total_results": 2,
        "page": 0,
        "results": [
            {
                "position": 1,
                "site_name": "recycling-directory.test",
                "title": "Industrial Aluminum Scrap Recyclers",
                "snippet": "Secondary smelter accepts aluminum alloy scrap from manufacturing.",
                "url": "https://recycling-directory.test/aluminum",
            },
            {
                "position": 2,
                "site_name": "metals-exchange.test",
                "title": "Midwest Secondary Smelting Corp",
                "snippet": "Midwest Secondary accepts 6000-series aluminum from industrial sources.",
                "url": "https://metals-exchange.test/midwest-smelting",
            },
        ],
    }

    def _mock_response(self, body: dict, status_code: int = 200):
        mock = MagicMock(spec=httpx.Response)
        mock.status_code = status_code
        mock.json.return_value = body
        mock.text = str(body)
        return mock

    def test_search_returns_results(self):
        adapter = TinyFishAdapter(api_key="tf_test_key", max_results=5)
        with patch("httpx.get", return_value=self._mock_response(self._VALID_SEARCH_RESPONSE)):
            results = adapter.search("aluminum scrap recycling")

        assert len(results) == 2
        assert isinstance(results[0], TinyFishSearchResult)
        assert results[0].position == 1
        assert results[0].site_name == "recycling-directory.test"
        assert "aluminum" in results[0].snippet.lower()

    def test_search_respects_max_results(self):
        adapter = TinyFishAdapter(api_key="tf_test_key", max_results=1)
        with patch("httpx.get", return_value=self._mock_response(self._VALID_SEARCH_RESPONSE)):
            results = adapter.search("aluminum")
        assert len(results) == 1

    def test_search_raises_on_401(self):
        adapter = TinyFishAdapter(api_key="tf_bad_key")
        bad_response = self._mock_response({}, status_code=401)
        with patch("httpx.get", return_value=bad_response):
            with pytest.raises(TinyFishProviderError, match="authentication failed"):
                adapter.search("test query")

    def test_search_raises_on_429(self):
        adapter = TinyFishAdapter(api_key="tf_test_key")
        rate_limited = self._mock_response({}, status_code=429)
        with patch("httpx.get", return_value=rate_limited):
            with pytest.raises(TinyFishProviderError, match="rate limit"):
                adapter.search("test query")

    def test_search_raises_on_timeout(self):
        adapter = TinyFishAdapter(api_key="tf_test_key")
        with patch("httpx.get", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(TinyFishProviderError, match="timed out"):
                adapter.search("test query")

    def test_search_raises_on_500(self):
        adapter = TinyFishAdapter(api_key="tf_test_key")
        server_error = self._mock_response({"error": "internal"}, status_code=500)
        with patch("httpx.get", return_value=server_error):
            with pytest.raises(TinyFishProviderError, match="HTTP 500"):
                adapter.search("test query")

    def test_search_raises_on_malformed_json(self):
        adapter = TinyFishAdapter(api_key="tf_test_key")
        bad_response = MagicMock(spec=httpx.Response)
        bad_response.status_code = 200
        bad_response.json.side_effect = ValueError("bad json")
        with patch("httpx.get", return_value=bad_response):
            with pytest.raises(TinyFishProviderError, match="non-JSON"):
                adapter.search("test query")

    def test_search_returns_empty_on_no_results(self):
        adapter = TinyFishAdapter(api_key="tf_test_key")
        empty_resp = self._mock_response({"results": [], "total_results": 0})
        with patch("httpx.get", return_value=empty_resp):
            results = adapter.search("obscure query with no results")
        assert results == []


class TestTinyFishFetch:
    """Tests the fetch method against mocked HTTP responses. Verified with: MOCK."""

    _VALID_FETCH_RESPONSE = {
        "results": [
            {
                "url": "https://example-recycler.test/capabilities",
                "final_url": "https://example-recycler.test/capabilities",
                "title": "Example Recycler — Industrial Capabilities",
                "description": "Secondary processing for aluminum and ferrous scrap.",
                "text": "# Industrial Capabilities\n\nWe accept aluminum alloy scrap (6000 series)...",
                "links": [],
            }
        ],
        "errors": [],
    }

    def _mock_response(self, body: dict, status_code: int = 200):
        mock = MagicMock(spec=httpx.Response)
        mock.status_code = status_code
        mock.json.return_value = body
        mock.text = str(body)
        return mock

    def test_fetch_returns_content(self):
        adapter = TinyFishAdapter(api_key="tf_test_key")
        with patch("httpx.post", return_value=self._mock_response(self._VALID_FETCH_RESPONSE)):
            results = adapter.fetch(["https://example-recycler.test/capabilities"])

        assert len(results) == 1
        assert isinstance(results[0], TinyFishFetchResult)
        assert "aluminum" in results[0].text.lower()
        assert results[0].title == "Example Recycler — Industrial Capabilities"

    def test_fetch_empty_urls_returns_empty(self):
        adapter = TinyFishAdapter(api_key="tf_test_key")
        results = adapter.fetch([])
        assert results == []

    def test_fetch_raises_on_too_many_urls(self):
        adapter = TinyFishAdapter(api_key="tf_test_key")
        with pytest.raises(TinyFishProviderError, match="at most 10"):
            adapter.fetch([f"https://example-{i}.test" for i in range(11)])

    def test_fetch_raises_on_401(self):
        adapter = TinyFishAdapter(api_key="tf_bad_key")
        with patch("httpx.post", return_value=self._mock_response({}, status_code=401)):
            with pytest.raises(TinyFishProviderError, match="authentication failed"):
                adapter.fetch(["https://example.test"])

    def test_fetch_raises_on_timeout(self):
        adapter = TinyFishAdapter(api_key="tf_test_key")
        with patch("httpx.post", side_effect=httpx.TimeoutException("timeout")):
            with pytest.raises(TinyFishProviderError, match="timed out"):
                adapter.fetch(["https://example.test"])


class TestTinyFishNormalization:
    """Tests that normalize_evidence methods produce correct STRATA evidence contracts. Verified: MOCK."""

    _SEARCH_RESPONSE = {
        "results": [
            {
                "position": 1,
                "site_name": "recycling.test",
                "title": "Aluminum Recycler Profile",
                "snippet": "Accepts 6061/6063 aluminum scrap in 500 kg batches.",
                "url": "https://recycling.test/profile",
            }
        ]
    }

    def _mock_get(self, body):
        mock = MagicMock(spec=httpx.Response)
        mock.status_code = 200
        mock.json.return_value = body
        return mock

    def test_search_normalize_provenance_and_verification(self):
        adapter = TinyFishAdapter(api_key="tf_test_key")
        with patch("httpx.get", return_value=self._mock_get(self._SEARCH_RESPONSE)):
            records = adapter.search_and_normalize_evidence(
                query="aluminum recycler",
                claim_subject="receiver_capability",
                lot_id="lot-abc-123",
            )

        assert len(records) == 1
        record = records[0]
        # Architecture constraint: publicly retrieved text must always be UNVERIFIED + PUBLICLY_STATED
        assert record.provenance == EvidenceProvenance.PUBLICLY_STATED
        assert record.verification_state == EvidenceVerificationState.UNVERIFIED
        assert record.extraction_method == ExtractionMethod.TINYFISH_FETCH
        assert record.lot_id == "lot-abc-123"
        assert record.claim_subject == "receiver_capability"
        assert record.source_url == "https://recycling.test/profile"

    def test_search_normalize_includes_content_hash(self):
        adapter = TinyFishAdapter(api_key="tf_test_key")
        with patch("httpx.get", return_value=self._mock_get(self._SEARCH_RESPONSE)):
            records = adapter.search_and_normalize_evidence(
                query="aluminum recycler",
                claim_subject="receiver_capability",
            )
        # Content hash should be set when there is non-empty snippet text
        assert records[0].content_hash is not None
        assert len(records[0].content_hash) == 64  # SHA-256 hex


# =============================================================================
# LLM adapter tests (all use mocked HTTP — verified: MOCK)
# =============================================================================


class TestFakeLLMProvider:
    """Tests FakeLLMProvider deterministic behavior. Verified with: MOCK (no network)."""

    def setup_method(self):
        self.llm = FakeLLMProvider()

    def test_unsupported_explanation_contains_blocking_reason(self):
        result = self.llm.synthesize_explanation(
            "Test Route", "unsupported", [], ["lead contamination detected"], []
        )
        assert "unsupported" in result.lower()
        assert "lead contamination" in result

    def test_conditional_explanation_names_missing_facts(self):
        result = self.llm.synthesize_explanation(
            "Test Route", "conditional", [], [], ["moisture assay", "alloy series"]
        )
        assert "conditional" in result.lower()
        assert "moisture assay" in result

    def test_supported_explanation_confirms_all_gates(self):
        result = self.llm.synthesize_explanation(
            "Test Route", "supported", ["gate-1", "gate-2"], [], []
        )
        assert "supported" in result.lower() or "2 hard gates" in result

    def test_next_action_unsupported_suggests_reroute(self):
        action = self.llm.suggest_next_action("unsupported", ["blocked"], [])
        assert "reroute" in action.lower() or "alternative" in action.lower()

    def test_next_action_conditional_names_missing(self):
        action = self.llm.suggest_next_action("conditional", [], ["moisture assay"])
        assert "moisture assay" in action

    def test_next_action_supported_suggests_listing(self):
        action = self.llm.suggest_next_action("supported", [], [])
        assert "exchange" in action.lower() or "listing" in action.lower()


class TestOpenAICompatibleLLMAdapter:
    """Tests OpenAI-compatible adapter with mocked HTTP. Verified with: MOCK."""

    def _make_adapter(self, api_key="sk-test-key"):
        return OpenAICompatibleLLMAdapter(api_key=api_key, model="gpt-4o-mini")

    def _mock_openai_response(self, content: str, status_code: int = 200):
        mock = MagicMock(spec=httpx.Response)
        mock.status_code = status_code
        mock.json.return_value = {
            "choices": [{"message": {"content": content, "role": "assistant"}}]
        }
        mock.text = content
        return mock

    def test_synthesize_explanation_returns_llm_text(self):
        adapter = self._make_adapter()
        llm_text = "The route is supported based on verified alloy and moisture data."
        with patch("httpx.post", return_value=self._mock_openai_response(llm_text)):
            result = adapter.synthesize_explanation("Route A", "supported", ["g1"], [], [])
        assert result == llm_text

    def test_falls_back_to_fake_on_timeout(self):
        adapter = self._make_adapter()
        with patch("httpx.post", side_effect=httpx.TimeoutException("timed out")):
            result = adapter.synthesize_explanation("Route A", "unsupported", [], ["lead found"], [])
        # Falls back deterministically — must NOT raise
        assert isinstance(result, str)
        assert len(result) > 0

    def test_falls_back_to_fake_on_401(self):
        adapter = self._make_adapter()
        with patch("httpx.post", return_value=self._mock_openai_response("", status_code=401)):
            result = adapter.suggest_next_action("conditional", [], ["moisture assay"])
        assert isinstance(result, str)
        assert len(result) > 0

    def test_falls_back_to_fake_on_malformed_response(self):
        adapter = self._make_adapter()
        bad_response = MagicMock(spec=httpx.Response)
        bad_response.status_code = 200
        bad_response.json.return_value = {"no_choices_key": True}
        with patch("httpx.post", return_value=bad_response):
            result = adapter.synthesize_explanation("Route A", "conditional", [], [], ["alloy series"])
        assert isinstance(result, str)

    def test_no_api_key_uses_deterministic_fallback(self):
        """Adapter with no key must fall back deterministically (no network call)."""
        adapter = OpenAICompatibleLLMAdapter(api_key="")
        result = adapter.synthesize_explanation("Route A", "supported", ["g1", "g2"], [], [])
        assert isinstance(result, str)


class TestGetLLMProviderFactory:
    """Tests the factory function. Verified with: MOCK."""

    def test_returns_fake_when_not_configured(self, monkeypatch):
        monkeypatch.setattr("strata.core.config.settings.LLM_PROVIDER", None)
        monkeypatch.setattr("strata.core.config.settings.LLM_API_KEY", None)
        provider = get_llm_provider()
        assert isinstance(provider, FakeLLMProvider)

    def test_returns_openai_adapter_when_configured(self, monkeypatch):
        monkeypatch.setattr("strata.core.config.settings.LLM_PROVIDER", "openai")
        monkeypatch.setattr("strata.core.config.settings.LLM_API_KEY", "sk-configured-key")
        provider = get_llm_provider()
        assert isinstance(provider, OpenAICompatibleLLMAdapter)
