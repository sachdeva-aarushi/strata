from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


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
