"""Service layer integration hook for STRATA verified impact blockchain anchoring.

Provides the singular, high-level entry point (AnchorService) for the application
and background workers (e.g. impact worker) to anchor verified circularity records
onto EVM blockchains without coupling core persistence to blockchain availability.
"""

import logging
from typing import Any, Dict, Optional, Union

# Handle imports whether accessed as standalone domain.blockchain or within strata package
try:
    from strata.domain.blockchain.evidence_hash import compute_evidence_hash
    from strata.domain.blockchain.anchor_client import (
        BlockchainAnchorClient,
        AnchorReceipt,
        BlockchainAnchorConfig,
    )
except ImportError:
    from domain.blockchain.evidence_hash import compute_evidence_hash
    from domain.blockchain.anchor_client import (
        BlockchainAnchorClient,
        AnchorReceipt,
        BlockchainAnchorConfig,
    )

logger = logging.getLogger("strata.blockchain.anchor_service")


class AnchorService:
    """Singular entry point for anchoring impact records to the blockchain.

    Decouples the core domain/worker from direct Web3 and RPC dependencies,
    guaranteeing that impact record persistence to PostgreSQL succeeds regardless
    of blockchain status.
    """

    def __init__(
        self,
        impact_record_or_client: Optional[Union[Dict[str, Any], Any, BlockchainAnchorClient]] = None,
        anchor_client: Optional[BlockchainAnchorClient] = None,
    ) -> None:
        """Initializes AnchorService.

        Can be initialized with:
          - AnchorService(client)
          - AnchorService(impact_record, client)
          - AnchorService() (uses default BlockchainAnchorClient)
        """
        self.default_record: Optional[Any] = None
        self.anchor_client: Optional[BlockchainAnchorClient] = None

        if isinstance(impact_record_or_client, BlockchainAnchorClient):
            self.anchor_client = impact_record_or_client
        elif impact_record_or_client is not None:
            self.default_record = impact_record_or_client
            if anchor_client is not None:
                self.anchor_client = anchor_client

        if anchor_client is not None and self.anchor_client is None:
            self.anchor_client = anchor_client

        if self.anchor_client is None:
            self.anchor_client = BlockchainAnchorClient()

    async def anchor_record(
        self,
        impact_record: Optional[Union[Dict[str, Any], Any]] = None,
        anchor_client: Optional[BlockchainAnchorClient] = None,
    ) -> AnchorReceipt:
        """Anchors an ImpactRecord domain model or dictionary on-chain.

        Args:
            impact_record: SQLAlchemy ImpactRecord, Pydantic schema, or dict
                           conforming to the impact_records schema.
            anchor_client: Optional client override for this specific anchor operation.

        Returns:
            AnchorReceipt: Contains tx_hash, block_number, record_index, etc.
                           If on-chain anchor fails or is not configured, returns
                           a fallback receipt with block_number=-1.
        """
        record_obj = impact_record if impact_record is not None else self.default_record
        if record_obj is None:
            raise ValueError("No impact_record provided to AnchorService.anchor_record().")

        # Convert domain model or schema object to dictionary
        record_dict: Dict[str, Any]
        if isinstance(record_obj, dict):
            record_dict = record_obj
        elif hasattr(record_obj, "to_dict") and callable(record_obj.to_dict):
            record_dict = record_obj.to_dict()
        elif hasattr(record_obj, "model_dump") and callable(record_obj.model_dump):
            record_dict = record_obj.model_dump()
        elif hasattr(record_obj, "__dict__"):
            record_dict = {
                k: v for k, v in record_obj.__dict__.items() if not k.startswith("_")
            }
        else:
            raise TypeError(
                f"Unsupported impact_record type: {type(record_obj)}. Expected dict or object with attributes."
            )

        lot_id = str(record_dict.get("lot_id", ""))
        event_type = str(record_dict.get("event_type", "verified_recovered"))

        # 1. Compute canonical SHA-256 evidence hash
        evidence_hash = compute_evidence_hash(record_dict)

        # 2. Select client
        client = anchor_client or self.anchor_client or BlockchainAnchorClient()

        # 3. Anchor impact event
        receipt = await client.anchor_impact_event(
            evidence_hash_hex=evidence_hash,
            lot_id=lot_id,
            event_type=event_type,
        )

        # 4. Log receipt at INFO level (tx_hash, block_number, lot_id)
        logger.info(
            "Impact record anchored. tx_hash=%s block_number=%s lot_id=%s",
            receipt.tx_hash,
            receipt.block_number,
            lot_id,
        )

        return receipt

    # Aliases to maximize ergonomics across caller styles
    async def anchor(
        self,
        impact_record: Optional[Union[Dict[str, Any], Any]] = None,
        anchor_client: Optional[BlockchainAnchorClient] = None,
    ) -> AnchorReceipt:
        """Alias for anchor_record."""
        return await self.anchor_record(impact_record=impact_record, anchor_client=anchor_client)

    async def __call__(
        self,
        impact_record: Optional[Union[Dict[str, Any], Any]] = None,
        anchor_client: Optional[BlockchainAnchorClient] = None,
    ) -> AnchorReceipt:
        """Allows AnchorService instances to be called directly as an async callable."""
        return await self.anchor_record(impact_record=impact_record, anchor_client=anchor_client)
