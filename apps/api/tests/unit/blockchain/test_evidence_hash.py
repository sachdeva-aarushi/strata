"""Unit tests for pure Python evidence payload canonicalization and hashing."""

import copy
from datetime import datetime, timezone
import pytest

try:
    from strata.domain.blockchain.evidence_hash import (
        CANONICAL_FIELDS,
        canonical_evidence_payload,
        compute_evidence_hash,
        compute_keccak256_hash,
    )
except ImportError:
    from domain.blockchain.evidence_hash import (
        CANONICAL_FIELDS,
        canonical_evidence_payload,
        compute_evidence_hash,
        compute_keccak256_hash,
    )


@pytest.fixture
def base_impact_record() -> dict:
    """Fixture providing a standard impact record dictionary."""
    return {
        "id": "rec-550e8400-e29b-41d4-a716-446655440000",
        "lot_id": "lot-e4b2d9a1-8711-4f92-911c-2f96e47b3109",
        "organization_id": "org-11111111-1111-1111-1111-111111111111",
        "facility_id": "fac-22222222-2222-2222-2222-222222222222",
        "event_type": "verified_recovered",
        "mass_kg": 12500.5,
        "co2e_avoided_kg": 45200.75,
        "created_at": "2026-10-24T02:30:00+00:00",
        "blockchain_tx_hash": "0x" + "a" * 64,
        "block_number": 19283746,
        "arbitrary_metadata": {"operator": "Aarushi", "shift": "morning"},
    }


def test_evidence_hash_determinism(base_impact_record):
    """Verifies that compute_evidence_hash is deterministic across two calls with identical input."""
    hash1 = compute_evidence_hash(base_impact_record)
    hash2 = compute_evidence_hash(base_impact_record)
    assert hash1 == hash2, "Repeated hashing of identical inputs must yield identical digests"


def test_evidence_hash_sha256_prefix(base_impact_record):
    """Verifies the output starts with 'sha256:' and is followed by 64 hexadecimal characters."""
    digest = compute_evidence_hash(base_impact_record)
    assert digest.startswith("sha256:"), "Evidence hash digest must be prefixed with 'sha256:'"

    raw_hex = digest.split(":", 1)[1]
    assert len(raw_hex) == 64, "SHA-256 digest must be exactly 64 hexadecimal characters"
    assert all(c in "0123456789abcdef" for c in raw_hex), "SHA-256 digest must be lowercase hex"


def test_changing_any_single_canonical_field_changes_hash(base_impact_record):
    """Verifies that changing any single canonical field changes the resulting evidence hash."""
    original_hash = compute_evidence_hash(base_impact_record)

    mutations = {
        "lot_id": "lot-mutated-different-lot-uuid",
        "organization_id": "org-99999999-9999-9999-9999-999999999999",
        "facility_id": "fac-88888888-8888-8888-8888-888888888888",
        "event_type": "diverted_landfill",
        "mass_kg": 99999.0,
        "co2e_avoided_kg": 123.45,
        "created_at": "2026-10-25T12:00:00+00:00",
    }

    for field_name, mutated_value in mutations.items():
        record_copy = copy.deepcopy(base_impact_record)
        record_copy[field_name] = mutated_value
        mutated_hash = compute_evidence_hash(record_copy)

        assert mutated_hash != original_hash, (
            f"Mutating canonical field '{field_name}' must change the hash. "
            f"Original: {original_hash}, Mutated: {mutated_hash}"
        )


def test_canonical_payload_excludes_non_canonical_fields(base_impact_record):
    """Verifies the canonical payload excludes non-canonical fields (e.g. id, blockchain_tx_hash)."""
    clean_record = {
        "lot_id": base_impact_record["lot_id"],
        "organization_id": base_impact_record["organization_id"],
        "facility_id": base_impact_record["facility_id"],
        "event_type": base_impact_record["event_type"],
        "mass_kg": base_impact_record["mass_kg"],
        "co2e_avoided_kg": base_impact_record["co2e_avoided_kg"],
        "created_at": base_impact_record["created_at"],
    }

    polluted_record = copy.deepcopy(base_impact_record)
    polluted_record["id"] = "id-should-be-ignored-completely"
    polluted_record["blockchain_tx_hash"] = "0x" + "b" * 64
    polluted_record["block_number"] = 999999
    polluted_record["extra_custom_metadata"] = "volatile_data"

    canonical_clean = canonical_evidence_payload(clean_record)
    canonical_polluted = canonical_evidence_payload(polluted_record)

    assert canonical_clean == canonical_polluted, (
        "Canonical payload must exclude non-canonical fields (id, blockchain_tx_hash, block_number, etc.)"
    )

    clean_hash = compute_evidence_hash(clean_record)
    polluted_hash = compute_evidence_hash(polluted_record)

    assert clean_hash == polluted_hash, (
        "Evidence hash must be strictly identical regardless of non-canonical fields"
    )

    # Check exact keys in canonical payload
    expected_keys = sorted(CANONICAL_FIELDS)
    assert list(canonical_polluted.keys()) == expected_keys


def test_created_at_datetime_object_normalization(base_impact_record):
    """Verifies that datetime objects in created_at are formatted consistently as ISO-8601 strings."""
    record_with_dt = copy.deepcopy(base_impact_record)
    dt_val = datetime(2026, 10, 24, 2, 30, 0, tzinfo=timezone.utc)
    record_with_dt["created_at"] = dt_val

    payload = canonical_evidence_payload(record_with_dt)
    assert isinstance(payload["created_at"], str)
    assert payload["created_at"] == dt_val.isoformat()


def test_keccak256_hash_graceful_handling(base_impact_record):
    """Verifies that compute_keccak256_hash either succeeds with keccak256: or raises NotImplementedError."""
    try:
        digest = compute_keccak256_hash(base_impact_record)
        assert digest.startswith("keccak256:"), "Keccak-256 hash must start with 'keccak256:'"
        raw_hex = digest.split(":", 1)[1]
        assert len(raw_hex) == 64
    except NotImplementedError as err:
        assert "Keccak-256 digest calculation requires" in str(err)
