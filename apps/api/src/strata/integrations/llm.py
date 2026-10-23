"""
LLM provider interfaces for STRATA.

LLMs serve an *advisory role only*. They synthesize human-readable explanations
and next-action suggestions from deterministic gate outcomes. They do NOT:
  - Evaluate hard technical or regulatory constraints
  - Invent missing evidence facts
  - Override qualification engine decisions

When LLM_PROVIDER and LLM_API_KEY are set, OpenAICompatibleLLMAdapter is used.
Otherwise FakeLLMProvider is used (safe for offline dev and all tests).
"""
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import httpx

from strata.core.config import settings

logger = logging.getLogger("strata.integrations.llm")


class LLMProviderError(Exception):
    """Raised when an LLM call fails unrecoverably."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class LLMProvider(ABC):
    """
    Interface for advisory language model services.
    Advisory role only: LLMs synthesize explanations and structure user text,
    but never evaluate hard rules or invent missing evidence facts.
    """

    @abstractmethod
    def synthesize_explanation(
        self,
        route_name: str,
        status: str,
        passed_gates: List[str],
        blocking_conditions: List[str],
        missing_facts: List[str],
    ) -> str:
        """Synthesizes human-readable audit commentary from deterministic gate outcomes."""
        pass

    @abstractmethod
    def suggest_next_action(
        self,
        status: str,
        blocking_conditions: List[str],
        missing_facts: List[str],
    ) -> str:
        """Suggests concrete next steps based on the qualification outcome."""
        pass


class FakeLLMProvider(LLMProvider):
    """
    Deterministic fake LLM provider for tests and local development.
    Produces predictable, auditable text without external network dependencies.
    """

    def synthesize_explanation(
        self,
        route_name: str,
        status: str,
        passed_gates: List[str],
        blocking_conditions: List[str],
        missing_facts: List[str],
    ) -> str:
        if status == "unsupported":
            reasons = "; ".join(blocking_conditions) if blocking_conditions else "hard gate failure"
            return f"Route '{route_name}' is unsupported due to blocking constraint violations: {reasons}."
        elif status == "conditional":
            missing = ", ".join(missing_facts) if missing_facts else "unverified specifications"
            return (
                f"Route '{route_name}' is conditionally eligible. All hard constraints passed, "
                f"but missing critical verification facts: {missing}."
            )
        else:
            return (
                f"Route '{route_name}' is fully supported. All {len(passed_gates)} hard gates passed "
                f"and all critical specification evidence is satisfied."
            )

    def suggest_next_action(
        self,
        status: str,
        blocking_conditions: List[str],
        missing_facts: List[str],
    ) -> str:
        if status == "unsupported":
            return "Reroute material to an alternative processing tier or investigate pre-treatment options."
        elif status == "conditional":
            return f"Acquire required evidence: {', '.join(missing_facts)}."
        else:
            return "Proceed to Circular Exchange listing and RFQ preparation."


class OpenAICompatibleLLMAdapter(LLMProvider):
    """
    LLM adapter for OpenAI chat-completions-compatible APIs.

    Uses the configured LLM_PROVIDER, LLM_API_KEY, LLM_MODEL, and LLM_BASE_URL.
    Supported providers: "openai" (api.openai.com), "azure_openai" (custom base URL).

    Advisory role ONLY. The adapter generates *commentary* from deterministic outcomes;
    it does not make qualification decisions.

    On any network, auth, or parse failure, falls back to FakeLLMProvider behavior
    and logs a warning. This avoids surfacing LLM instability as API errors.
    """

    _PROVIDER_BASE_URLS: Dict[str, str] = {
        "openai": "https://api.openai.com/v1",
    }

    _DEFAULT_MODEL: Dict[str, str] = {
        "openai": "gpt-4o-mini",
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        provider: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self._provider = (provider or settings.LLM_PROVIDER or "openai").lower().strip()
        self._api_key = api_key or settings.LLM_API_KEY or ""
        self._timeout = timeout if timeout is not None else settings.LLM_TIMEOUT_SECONDS
        self._fallback = FakeLLMProvider()

        # Determine base URL and model
        resolved_base = (
            base_url
            or settings.LLM_BASE_URL
            or self._PROVIDER_BASE_URLS.get(self._provider, "https://api.openai.com/v1")
        )
        self._chat_url = resolved_base.rstrip("/") + "/chat/completions"

        self._model = (
            model
            or settings.LLM_MODEL
            or self._DEFAULT_MODEL.get(self._provider, "gpt-4o-mini")
        )

        if not self._api_key:
            logger.warning(
                "OpenAICompatibleLLMAdapter: No API key configured. "
                "All calls will use deterministic FakeLLMProvider output."
            )

    def _call_chat_completions(
        self,
        system_prompt: str,
        user_message: str,
        max_tokens: int = 300,
    ) -> str:
        """
        Calls the configured chat-completions endpoint.

        Returns the first message content string on success.
        Raises LLMProviderError on failure.
        """
        if not self._api_key:
            raise LLMProviderError("No API key configured.")

        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }

        try:
            response = httpx.post(
                self._chat_url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
            )
        except httpx.TimeoutException as exc:
            raise LLMProviderError(f"LLM request timed out after {self._timeout}s") from exc
        except httpx.RequestError as exc:
            raise LLMProviderError(f"LLM request failed: {exc}") from exc

        if response.status_code == 401:
            raise LLMProviderError("LLM authentication failed — check LLM_API_KEY.", status_code=401)
        if response.status_code == 429:
            raise LLMProviderError("LLM rate limit exceeded.", status_code=429)
        if response.status_code >= 400:
            raise LLMProviderError(
                f"LLM API returned HTTP {response.status_code}: {response.text[:200]}",
                status_code=response.status_code,
            )

        try:
            data = response.json()
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise LLMProviderError(f"LLM response parse error: {exc}") from exc

    def synthesize_explanation(
        self,
        route_name: str,
        status: str,
        passed_gates: List[str],
        blocking_conditions: List[str],
        missing_facts: List[str],
    ) -> str:
        """
        Synthesizes audit-grade commentary from deterministic gate outcomes.
        Falls back to FakeLLMProvider text on any LLM failure.
        """
        system = (
            "You are an industrial circularity compliance analyst. "
            "Write a concise, factual one-paragraph explanation of a ProofPath qualification outcome. "
            "Do not invent or assume facts not explicitly provided. "
            "Do not claim verified environmental savings; state facts only."
        )
        user = (
            f"Route: {route_name}\n"
            f"Outcome: {status}\n"
            f"Passed gates: {', '.join(passed_gates) or 'none'}\n"
            f"Blocking conditions: {'; '.join(blocking_conditions) or 'none'}\n"
            f"Missing critical facts: {', '.join(missing_facts) or 'none'}\n\n"
            "Write a plain-English one-paragraph explanation for the operator."
        )
        try:
            return self._call_chat_completions(system, user, max_tokens=200)
        except LLMProviderError as exc:
            logger.warning(
                "LLM synthesize_explanation failed (%s); using deterministic fallback.", exc
            )
            return self._fallback.synthesize_explanation(
                route_name, status, passed_gates, blocking_conditions, missing_facts
            )

    def suggest_next_action(
        self,
        status: str,
        blocking_conditions: List[str],
        missing_facts: List[str],
    ) -> str:
        """
        Suggests a concrete next action based on the qualification outcome.
        Falls back to FakeLLMProvider text on any LLM failure.
        """
        system = (
            "You are an industrial waste management advisor. "
            "Given a ProofPath qualification outcome, recommend one clear next action for the facility operator. "
            "Be specific and actionable. Do not invent environmental impact numbers."
        )
        user = (
            f"Outcome: {status}\n"
            f"Blocking conditions: {'; '.join(blocking_conditions) or 'none'}\n"
            f"Missing facts: {', '.join(missing_facts) or 'none'}\n\n"
            "Recommend a single clear next step."
        )
        try:
            return self._call_chat_completions(system, user, max_tokens=100)
        except LLMProviderError as exc:
            logger.warning(
                "LLM suggest_next_action failed (%s); using deterministic fallback.", exc
            )
            return self._fallback.suggest_next_action(status, blocking_conditions, missing_facts)


def get_llm_provider() -> LLMProvider:
    """
    Factory: returns the appropriate LLM provider based on current configuration.

    - If LLM_PROVIDER and LLM_API_KEY are set: OpenAICompatibleLLMAdapter
    - Otherwise: FakeLLMProvider (no external calls; safe for tests)
    """
    if settings.llm_configured:
        logger.info(
            "Using real LLM provider: %s / model: %s",
            settings.LLM_PROVIDER,
            settings.LLM_MODEL or "(default)",
        )
        return OpenAICompatibleLLMAdapter()
    logger.debug("No LLM credentials configured — using FakeLLMProvider.")
    return FakeLLMProvider()
