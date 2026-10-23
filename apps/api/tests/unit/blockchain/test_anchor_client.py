"""Unit tests for the asynchronous blockchain anchor client and service hook."""

import asyncio
from datetime import datetime, timezone
import logging
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

try:
    from strata.domain.blockchain.anchor_client import (
        AnchorReceipt,
        BlockchainAnchorClient,
        BlockchainAnchorConfig,
    )
    from strata.domain.blockchain.anchor_service import AnchorService
except ImportError:
    from domain.blockchain.anchor_client import (
        AnchorReceipt,
        BlockchainAnchorClient,
        BlockchainAnchorConfig,
    )
    from domain.blockchain.anchor_service import AnchorService


@pytest.fixture
def fake_sample_record() -> dict:
    return {
        "id": "rec-001",
        "lot_id": "lot-e4b2d9a1-8711-4f92-911c-2f96e47b3109",
        "organization_id": "org-11111111-1111-1111-1111-111111111111",
        "facility_id": "fac-22222222-2222-2222-2222-222222222222",
        "event_type": "verified_recovered",
        "mass_kg": 5000.0,
        "co2e_avoided_kg": 12000.0,
        "created_at": "2026-10-24T02:00:00+00:00",
    }


@pytest.mark.asyncio
async def test_fallback_fires_when_rpc_url_is_none():
    """Tests the fallback path fires when rpc_url is None."""
    client = BlockchainAnchorClient(
        rpc_url=None,
        contract_address="0x" + "1" * 40,
        private_key="0x" + "a" * 64,
        chain_id=137,
    )

    receipt = await client.anchor_impact_event(
        evidence_hash_hex="sha256:" + "0" * 64,
        lot_id="lot-12345",
        event_type="verified_recovered",
    )

    assert receipt.block_number == -1, "Fallback receipt must have block_number -1"
    assert receipt.tx_hash.startswith("local:"), "Fallback receipt tx_hash must start with 'local:'"
    assert receipt.is_fallback is True
    assert "No RPC URL configured" in (receipt.fallback_reason or "")


@pytest.mark.asyncio
async def test_fallback_fires_when_contract_address_or_key_is_none():
    """Tests that missing contract address or private key triggers local fallback safely."""
    client_no_contract = BlockchainAnchorClient(
        rpc_url="http://127.0.0.1:8545",
        contract_address=None,
        private_key="0x" + "a" * 64,
    )
    receipt1 = await client_no_contract.anchor_impact_event("sha256:" + "0" * 64, "lot-1", "verified_recovered")
    assert receipt1.block_number == -1
    assert "No contract address configured" in (receipt1.fallback_reason or "")

    client_no_key = BlockchainAnchorClient(
        rpc_url="http://127.0.0.1:8545",
        contract_address="0x" + "1" * 40,
        private_key=None,
    )
    # Ensure environment variable is not silently populating private_key
    client_no_key.config.private_key = None
    receipt2 = await client_no_key.anchor_impact_event("sha256:" + "0" * 64, "lot-1", "verified_recovered")
    assert receipt2.block_number == -1
    assert "No signing key configured" in (receipt2.fallback_reason or "")


@pytest.mark.asyncio
async def test_fallback_fires_when_rpc_mock_raises_connection_error():
    """Tests the fallback path fires when the RPC mock raises ConnectionError after retries."""
    config = BlockchainAnchorConfig(
        rpc_url="http://mock-rpc-node.internal:8545",
        contract_address="0x" + "2" * 40,
        private_key="0x" + "b" * 64,
        max_retries=2,
        backoff_base_seconds=0.01,  # Short delay for fast unit tests
    )
    client = BlockchainAnchorClient(config=config)

    # Mock the internal raw execution method to raise ConnectionError
    with patch.object(
        client,
        "_execute_on_chain_anchor",
        side_effect=ConnectionError("RPC peer unreachable / connection reset"),
    ) as mock_exec, patch.object(
        logging.getLogger("strata.blockchain.anchor_client"),
        "warning",
    ) as mock_warn:
        receipt = await client.anchor_impact_event(
            evidence_hash_hex="sha256:" + "c" * 64,
            lot_id="lot-test-connection-error",
            event_type="verified_recovered",
        )

        # 1 initial attempt + 2 retries = 3 calls
        assert mock_exec.call_count == 3
        assert receipt.block_number == -1
        assert receipt.tx_hash.startswith("local:")
        assert receipt.is_fallback is True
        assert "ConnectionError" in (receipt.fallback_reason or "") or "RPC peer unreachable" in (receipt.fallback_reason or "")

        # Verify a warning was logged with the exception
        assert mock_warn.called, "Fallback must log at WARNING level"
        warn_str = " ".join(str(call) for call in mock_warn.call_args_list)
        assert "fallback" in warn_str.lower() or "failed" in warn_str.lower()


@pytest.mark.asyncio
async def test_fallback_fires_when_web3_not_installed():
    """Tests fallback when web3 or eth_account is not installed."""
    client = BlockchainAnchorClient(
        rpc_url="http://mock-node:8545",
        contract_address="0x" + "1" * 40,
        private_key="0x" + "a" * 64,
    )
    with patch.object(
        client,
        "_execute_on_chain_anchor",
        side_effect=ImportError("No module named 'web3'"),
    ):
        receipt = await client.anchor_impact_event("sha256:" + "0" * 64, "lot-1", "verified_recovered")
        assert receipt.block_number == -1
        assert receipt.tx_hash.startswith("local:")
        assert "Web3 dependency not installed" in (receipt.fallback_reason or "")


@pytest.mark.asyncio
async def test_anchor_impact_event_returns_valid_receipt_on_success():
    """Tests that anchor_impact_event returns a valid AnchorReceipt when mocked RPC succeeds."""
    expected_tx_hash = "0x" + "a" * 64
    expected_block = 19283746
    expected_index = 42

    client = BlockchainAnchorClient(
        rpc_url="http://mock-node:8545",
        contract_address="0x" + "3" * 40,
        private_key="0x" + "c" * 64,
    )

    mock_receipt = AnchorReceipt(
        tx_hash=expected_tx_hash,
        block_number=expected_block,
        record_index=expected_index,
        anchored_at=datetime.now(timezone.utc),
        chain_id=137,
        contract_address="0x" + "3" * 40,
        fallback_reason=None,
        is_fallback=False,
    )

    with patch.object(client, "_execute_on_chain_anchor", new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_receipt

        receipt = await client.anchor_impact_event(
            evidence_hash_hex="sha256:" + "d" * 64,
            lot_id="lot-success-vector",
            event_type="verified_recovered",
        )

        mock_exec.assert_awaited_once_with(
            evidence_hash_hex="sha256:" + "d" * 64,
            lot_id="lot-success-vector",
            event_type="verified_recovered",
        )
        assert receipt.tx_hash == expected_tx_hash
        assert receipt.block_number == expected_block
        assert receipt.record_index == expected_index
        assert receipt.is_fallback is False
        assert receipt.fallback_reason is None


@pytest.mark.asyncio
async def test_anchor_service_integration(fake_sample_record):
    """Verifies AnchorService provides the decoupled entry point, logs INFO, and returns receipt."""
    client = BlockchainAnchorClient(
        rpc_url="http://mock-node:8545",
        contract_address="0x" + "4" * 40,
        private_key="0x" + "e" * 64,
    )

    mock_receipt = AnchorReceipt(
        tx_hash="0x" + "f" * 64,
        block_number=20485900,
        record_index=7,
        anchored_at=datetime.now(timezone.utc),
        chain_id=137,
        contract_address="0x" + "4" * 40,
    )

    with patch.object(client, "anchor_impact_event", new_callable=AsyncMock) as mock_anchor, \
         patch.object(logging.getLogger("strata.blockchain.anchor_service"), "info") as mock_info:
        mock_anchor.return_value = mock_receipt

        service = AnchorService(anchor_client=client)
        receipt = await service.anchor_record(fake_sample_record)

        assert receipt.tx_hash == "0x" + "f" * 64
        assert receipt.block_number == 20485900
        mock_anchor.assert_awaited_once()

        # Check call arguments: canonical hash should be passed
        call_kwargs = mock_anchor.call_args.kwargs
        assert call_kwargs["evidence_hash_hex"].startswith("sha256:")
        assert call_kwargs["lot_id"] == fake_sample_record["lot_id"]
        assert call_kwargs["event_type"] == fake_sample_record["event_type"]

        # Check INFO log contains tx_hash, block_number, and lot_id
        assert mock_info.called, "AnchorService must log at INFO level"
        info_str = " ".join(str(call) for call in mock_info.call_args_list)
        assert fake_sample_record["lot_id"] in info_str
        assert "0x" + "f" * 64 in info_str
        assert "20485900" in info_str


def test_private_key_never_leaked_in_repr():
    """Guarantees that private keys are never exposed in string representations or dataclass repr."""
    secret_key = "0x" + "d" * 64
    config = BlockchainAnchorConfig(
        rpc_url="http://127.0.0.1:8545",
        contract_address="0x" + "1" * 40,
        private_key=secret_key,
    )

    repr_str = repr(config)
    assert secret_key not in repr_str, "Private key must never appear in BlockchainAnchorConfig repr"
    assert "private_key" not in repr_str or secret_key not in repr_str
