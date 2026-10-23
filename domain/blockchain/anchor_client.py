"""Asynchronous EVM blockchain client for anchoring verified impact records.

Implements resilient on-chain transactions with automatic retry, exponential backoff,
and a seamless fallback mode that guarantees the host application never crashes or halts
even if Web3 is missing or the RPC network is unreachable.

SECURITY MANDATE:
  * Private keys are strictly loaded from environment variables and NEVER logged,
    printed, or leaked into error payloads.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import inspect
import logging
import os
from typing import Any, Dict, Optional, Union

logger = logging.getLogger("strata.blockchain.anchor_client")

# Contract ABI minimal interface matching StrataImpactLedger.sol
STRATA_IMPACT_LEDGER_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
            {"internalType": "string", "name": "lotId", "type": "string"},
            {"internalType": "string", "name": "eventType", "type": "string"},
        ],
        "name": "anchorImpactEvent",
        "outputs": [{"internalType": "uint256", "name": "recordIndex", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "uint256", "name": "recordIndex", "type": "uint256"},
            {"indexed": True, "internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
            {"indexed": True, "internalType": "address", "name": "anchoredBy", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"indexed": False, "internalType": "string", "name": "lotId", "type": "string"},
            {"indexed": False, "internalType": "string", "name": "eventType", "type": "string"},
        ],
        "name": "ImpactEventAnchored",
        "type": "event",
    },
]


@dataclass
class BlockchainAnchorConfig:
    """Configuration for connecting to an EVM blockchain anchor ledger."""
    rpc_url: Optional[str] = None
    contract_address: Optional[str] = None
    private_key: Optional[str] = field(default=None, repr=False)
    chain_id: int = 137  # Default Polygon PoS
    max_retries: int = 2
    backoff_base_seconds: float = 0.5
    timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.private_key is None:
            self.private_key = os.getenv("STRATA_BLOCKCHAIN_PRIVATE_KEY")
        if self.rpc_url is None:
            self.rpc_url = os.getenv("STRATA_BLOCKCHAIN_RPC_URL")
        if self.contract_address is None:
            self.contract_address = os.getenv("STRATA_BLOCKCHAIN_CONTRACT_ADDRESS")


@dataclass
class AnchorReceipt:
    """Receipt returned following an on-chain or local fallback anchor operation."""
    tx_hash: str
    block_number: int
    record_index: int
    anchored_at: datetime
    chain_id: int
    contract_address: str
    fallback_reason: Optional[str] = None
    is_fallback: bool = False


# Type alias for clarity
FallbackAnchorReceipt = AnchorReceipt


def _to_bytes32(hash_str: str) -> bytes:
    """Converts a prefixed or raw hex hash string to exactly 32 bytes."""
    clean = hash_str.strip()
    if ":" in clean:
        clean = clean.split(":", 1)[1]
    if clean.startswith("0x") or clean.startswith("0X"):
        clean = clean[2:]

    # Pad or truncate to 32 bytes (64 hex characters)
    if len(clean) < 64:
        clean = clean.zfill(64)
    elif len(clean) > 64:
        clean = clean[:64]

    return bytes.fromhex(clean)


class BlockchainAnchorClient:
    """Async EVM blockchain client for anchoring verified circularity impact events."""

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        contract_address: Optional[str] = None,
        private_key: Optional[str] = None,
        chain_id: int = 137,
        config: Optional[BlockchainAnchorConfig] = None,
        **kwargs: Any,
    ) -> None:
        """Initializes the blockchain client.

        Accepts either an explicit config dataclass or direct keyword arguments.
        Falls back to environment variables (STRATA_BLOCKCHAIN_PRIVATE_KEY, etc.)
        when parameters are omitted.
        """
        if config is not None:
            self.config = config
        else:
            self.config = BlockchainAnchorConfig(
                rpc_url=rpc_url,
                contract_address=contract_address,
                private_key=private_key,
                chain_id=chain_id,
                **kwargs,
            )

    def _create_fallback_receipt(self, evidence_hash_hex: str, reason: str) -> AnchorReceipt:
        """Constructs a deterministic local fallback receipt when on-chain anchoring is skipped."""
        local_hash = hashlib.sha256(evidence_hash_hex.encode("utf-8")).hexdigest()
        logger.warning(
            "Blockchain anchor fallback engaged for hash %s... Reason: %s",
            evidence_hash_hex[:16],
            reason,
        )
        return AnchorReceipt(
            tx_hash=f"local:{local_hash}",
            block_number=-1,
            record_index=-1,
            anchored_at=datetime.now(timezone.utc),
            chain_id=self.config.chain_id,
            contract_address=self.config.contract_address or "0x0000000000000000000000000000000000000000",
            fallback_reason=reason,
            is_fallback=True,
        )

    async def anchor_impact_event(
        self,
        evidence_hash_hex: str,
        lot_id: str,
        event_type: str,
    ) -> AnchorReceipt:
        """Anchors an evidence hash on-chain with automatic retries and safe fallback.

        Guarantees:
          - Never raises an uncaught exception to the caller. Always returns an AnchorReceipt.
          - Returns an AnchorReceipt with valid tx_hash and block_number on success.
          - Returns a FallbackAnchorReceipt (block_number=-1) on RPC failure, missing configuration,
            or absent Web3 dependencies.
        """
        # 1. Pre-flight check: ensure required configuration is present
        if not self.config.rpc_url:
            return self._create_fallback_receipt(
                evidence_hash_hex, "No RPC URL configured (STRATA_BLOCKCHAIN_RPC_URL is unset)."
            )
        if not self.config.contract_address:
            return self._create_fallback_receipt(
                evidence_hash_hex, "No contract address configured (STRATA_BLOCKCHAIN_CONTRACT_ADDRESS is unset)."
            )
        if not self.config.private_key:
            return self._create_fallback_receipt(
                evidence_hash_hex, "No signing key configured (STRATA_BLOCKCHAIN_PRIVATE_KEY is unset)."
            )

        # 2. Attempt on-chain anchor with exponential backoff retry loop
        last_exception: Optional[Exception] = None
        for attempt in range(self.config.max_retries + 1):
            try:
                receipt = await self._execute_on_chain_anchor(
                    evidence_hash_hex=evidence_hash_hex,
                    lot_id=lot_id,
                    event_type=event_type,
                )
                return receipt
            except ImportError as import_err:
                # If web3 or eth_account is not installed, degrade immediately without retry
                logger.warning(
                    "Web3 dependency not installed: %s. Running in local fallback mode.",
                    import_err,
                )
                return self._create_fallback_receipt(
                    evidence_hash_hex,
                    f"Web3 dependency not installed: {import_err}. Running in local fallback mode.",
                )
            except Exception as exc:
                last_exception = exc
                if attempt < self.config.max_retries:
                    delay = self.config.backoff_base_seconds * (2 ** attempt)
                    logger.warning(
                        "On-chain anchor attempt %d failed: %s. Retrying in %.2fs...",
                        attempt + 1,
                        str(exc),
                        delay,
                    )
                    await asyncio.sleep(delay)

        # 3. Exceeded retries: degrade gracefully to fallback receipt
        logger.warning(
            "On-chain anchor failed after %d retries with exception: %s",
            self.config.max_retries,
            last_exception,
            exc_info=last_exception,
        )
        return self._create_fallback_receipt(
            evidence_hash_hex,
            f"On-chain anchor failed after {self.config.max_retries + 1} attempts: {last_exception}",
        )

    async def _execute_on_chain_anchor(
        self,
        evidence_hash_hex: str,
        lot_id: str,
        event_type: str,
    ) -> AnchorReceipt:
        """Executes the raw Web3 EVM transaction."""
        try:
            from web3 import AsyncHTTPProvider, AsyncWeb3
            from eth_account import Account
        except ImportError as exc:
            raise ImportError(f"Web3 or eth_account dependency missing: {exc}") from exc

        w3 = AsyncWeb3(AsyncHTTPProvider(self.config.rpc_url, request_kwargs={"timeout": self.config.timeout_seconds}))
        account = Account.from_key(self.config.private_key)
        contract = w3.eth.contract(
            address=AsyncWeb3.to_checksum_address(self.config.contract_address),
            abi=STRATA_IMPACT_LEDGER_ABI,
        )

        b32_hash = _to_bytes32(evidence_hash_hex)
        nonce_coro = w3.eth.get_transaction_count(account.address)
        nonce = await nonce_coro if inspect.isawaitable(nonce_coro) else nonce_coro

        # Prepare transaction
        tx_call = contract.functions.anchorImpactEvent(
            b32_hash,
            lot_id,
            event_type,
        ).build_transaction({
            "from": account.address,
            "nonce": nonce,
            "chainId": self.config.chain_id,
        })
        tx = await tx_call if inspect.isawaitable(tx_call) else tx_call

        # Sign and broadcast
        signed_tx = account.sign_transaction(tx)
        raw_tx = getattr(signed_tx, "raw_transaction", getattr(signed_tx, "rawTransaction", signed_tx))
        send_coro = w3.eth.send_raw_transaction(raw_tx)
        tx_hash_bytes = await send_coro if inspect.isawaitable(send_coro) else send_coro

        if isinstance(tx_hash_bytes, (bytes, bytearray)):
            tx_hash_hex = tx_hash_bytes.hex()
        else:
            tx_hash_hex = str(tx_hash_bytes)

        if not tx_hash_hex.startswith("0x"):
            tx_hash_hex = "0x" + tx_hash_hex

        # Await receipt
        wait_coro = w3.eth.wait_for_transaction_receipt(tx_hash_bytes, timeout=self.config.timeout_seconds)
        tx_receipt = await wait_coro if inspect.isawaitable(wait_coro) else wait_coro

        # Parse record index from logs or default to block number
        record_idx = 0
        try:
            event_obj = contract.events.ImpactEventAnchored()
            proc_call = event_obj.process_receipt(tx_receipt) if hasattr(event_obj, "process_receipt") else None
            logs = await proc_call if inspect.isawaitable(proc_call) else proc_call
            if logs:
                record_idx = logs[0]["args"]["recordIndex"]
        except Exception:
            record_idx = tx_receipt.get("blockNumber", 0) if isinstance(tx_receipt, dict) else getattr(tx_receipt, "blockNumber", 0)

        block_number = tx_receipt.get("blockNumber", -1) if isinstance(tx_receipt, dict) else getattr(tx_receipt, "blockNumber", -1)

        return AnchorReceipt(
            tx_hash=tx_hash_hex,
            block_number=block_number,
            record_index=record_idx,
            anchored_at=datetime.now(timezone.utc),
            chain_id=self.config.chain_id,
            contract_address=str(self.config.contract_address),
            fallback_reason=None,
            is_fallback=False,
        )
