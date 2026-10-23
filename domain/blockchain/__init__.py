"""STRATA Blockchain Anchor Module.

Provides cryptographic canonical evidence hashing, an asynchronous EVM blockchain client,
and the service layer AnchorService entry point for anchoring verified impact events on-chain.
"""

from .evidence_hash import (
    CANONICAL_FIELDS,
    canonical_evidence_payload,
    compute_evidence_hash,
    compute_keccak256_hash,
)
from .anchor_client import (
    AnchorReceipt,
    BlockchainAnchorClient,
    BlockchainAnchorConfig,
    FallbackAnchorReceipt,
)
from .anchor_service import AnchorService

__all__ = [
    "CANONICAL_FIELDS",
    "canonical_evidence_payload",
    "compute_evidence_hash",
    "compute_keccak256_hash",
    "AnchorReceipt",
    "BlockchainAnchorClient",
    "BlockchainAnchorConfig",
    "FallbackAnchorReceipt",
    "AnchorService",
]
