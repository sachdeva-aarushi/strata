"""Structured HTTP adapter for ProofPath qualification.

The qualification algorithm and the canonical material lot registry belong to
ProofPath / the materials domain. This module only calls ProofPath's
``POST /api/v1/qualification/assess`` endpoint and validates the response
against the ``QualificationResult`` contract.
"""

import logging
from typing import Any, Dict, Optional

import httpx
from pydantic import ValidationError as PydanticValidationError

from strata.core.config import settings
from strata.core.errors import StrataError
from strata.domain.marketplace.schemas import QualificationResult
from strata.schemas.qualification import AssessmentStatus

logger = logging.getLogger(__name__)

ASSESS_PATH = "/api/v1/qualification/assess"


class QualificationServiceError(StrataError):
    """ProofPath could not produce a valid assessment."""

    def __init__(self, message: str, reason: str, details: Optional[Dict[str, Any]] = None) -> None:
        payload = {"reason": reason, **(details or {})}
        super().__init__(
            message=message,
            code="QUALIFICATION_SERVICE_UNAVAILABLE",
            status_code=502,
            details=payload,
        )
        self.reason = reason


def build_mock_result(material_lot_id: str, requirement_id: str, reason: str) -> Dict[str, Any]:
    """Offline placeholder. Always ``pending`` so it never reads as a real qualification."""
    result = QualificationResult(
        material_lot_id=material_lot_id,
        requirement_id=requirement_id,
        status=AssessmentStatus.PENDING,
        rationale=f"MOCK result: ProofPath unavailable ({reason}). No qualification was performed.",
        next_action="Re-run the assessment once ProofPath is reachable.",
        rule_version="mock",
        source="mock",
    )
    return result.model_dump(mode="json")


class ProofPathQualificationClient:
    """Async client for ProofPath's qualification assessment endpoint."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        mock_fallback: Optional[bool] = None,
        mock_only: bool = False,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        """
        Args:
            base_url: ProofPath host, without the path. Defaults to settings.PROOFPATH_BASE_URL.
            timeout_seconds: Per-request timeout. Defaults to settings.PROOFPATH_TIMEOUT_SECONDS.
            mock_fallback: Return a mock result on outage instead of raising.
                Defaults to settings.PROOFPATH_MOCK_FALLBACK.
            mock_only: Never touch the network; always return the mock result.
                For offline tests and local demos.
            transport: Optional httpx transport, used to inject ``httpx.MockTransport`` in tests.
        """
        self.base_url = (base_url or settings.PROOFPATH_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.PROOFPATH_TIMEOUT_SECONDS
        self.mock_fallback = settings.PROOFPATH_MOCK_FALLBACK if mock_fallback is None else mock_fallback
        self.mock_only = mock_only
        self._transport = transport

    async def assess_lot_qualification(self, material_lot_id: str, requirement_id: str) -> dict:
        """Ask ProofPath whether a lot qualifies against a buyer requirement.

        Returns a validated ``QualificationResult`` as a JSON-compatible dict.

        Raises:
            QualificationServiceError: ProofPath is unreachable, times out, returns
                a non-2xx status, or returns a payload that fails schema validation,
                and mock fallback is disabled.
        """
        if self.mock_only:
            return build_mock_result(material_lot_id, requirement_id, reason="mock_only mode")

        payload = {"material_lot_id": material_lot_id, "requirement_id": requirement_id}
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(ASSESS_PATH, json=payload)
        except httpx.TimeoutException as exc:
            return self._fail(material_lot_id, requirement_id, "timeout", f"ProofPath timed out: {exc}")
        except httpx.HTTPError as exc:
            return self._fail(material_lot_id, requirement_id, "connection", f"ProofPath unreachable: {exc}")

        if response.status_code >= 300:
            return self._fail(
                material_lot_id,
                requirement_id,
                "http_status",
                f"ProofPath returned HTTP {response.status_code}",
                status_code=response.status_code,
            )

        try:
            body = response.json()
        except ValueError:
            return self._fail(material_lot_id, requirement_id, "schema", "ProofPath response is not JSON")

        if not isinstance(body, dict):
            return self._fail(material_lot_id, requirement_id, "schema", "ProofPath response is not an object")

        # Echo the ids we asked about if ProofPath omits them; never trust a mismatch silently.
        body.setdefault("material_lot_id", material_lot_id)
        body.setdefault("requirement_id", requirement_id)
        if body["material_lot_id"] != material_lot_id or body["requirement_id"] != requirement_id:
            return self._fail(material_lot_id, requirement_id, "schema", "ProofPath echoed mismatched identifiers")

        try:
            result = QualificationResult.model_validate({**body, "source": "proofpath"})
        except PydanticValidationError as exc:
            return self._fail(
                material_lot_id,
                requirement_id,
                "schema",
                "ProofPath response failed schema validation",
                errors=[{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()],
            )

        return result.model_dump(mode="json")

    def _fail(
        self,
        material_lot_id: str,
        requirement_id: str,
        reason: str,
        message: str,
        **details: Any,
    ) -> Dict[str, Any]:
        """Either return a mock result (fallback enabled) or raise a typed error."""
        logger.warning("proofpath_assess_failed reason=%s message=%s", reason, message)
        if self.mock_fallback:
            return build_mock_result(material_lot_id, requirement_id, reason=reason)
        raise QualificationServiceError(message=message, reason=reason, details=details)
