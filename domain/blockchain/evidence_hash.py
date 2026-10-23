"""Pure Python canonical evidence serialization and cryptographic hashing utility.

Generates deterministic SHA-256 and Keccak-256 digests over STRATA Verified Impact Ledger
records for non-repudiation and off-chain / on-chain verification.
"""

from datetime import datetime
import hashlib
import json
from typing import Any, Dict


CANONICAL_FIELDS = (
    "lot_id",
    "organization_id",
    "facility_id",
    "event_type",
    "mass_kg",
    "co2e_avoided_kg",
    "created_at",
)


def canonical_evidence_payload(impact_record: Dict[str, Any]) -> Dict[str, Any]:
    """Extracts and normalizes the canonical evidence fields from an impact record.

    Excludes non-canonical attributes (such as record primary keys, internal database IDs,
    or volatile blockchain transaction metadata) to ensure deterministic hash generation.

    Args:
        impact_record: Dictionary containing impact record fields.

    Returns:
        Deterministic dictionary containing only the canonical fields sorted alphabetically.
    """
    raw_created_at = impact_record.get("created_at")
    if isinstance(raw_created_at, datetime):
        created_at_str = raw_created_at.isoformat()
    elif raw_created_at is not None:
        created_at_str = str(raw_created_at)
    else:
        created_at_str = ""

    payload = {
        "co2e_avoided_kg": float(impact_record.get("co2e_avoided_kg", 0.0)),
        "created_at": created_at_str,
        "event_type": str(impact_record.get("event_type", "")),
        "facility_id": str(impact_record.get("facility_id", "")),
        "lot_id": str(impact_record.get("lot_id", "")),
        "mass_kg": float(impact_record.get("mass_kg", 0.0)),
        "organization_id": str(impact_record.get("organization_id", "")),
    }

    # Return dictionary with canonical keys sorted
    return {k: payload[k] for k in sorted(payload.keys())}


def serialize_canonical_payload(impact_record: Dict[str, Any]) -> bytes:
    """Serializes canonical evidence payload to compact, sorted UTF-8 JSON bytes."""
    payload = canonical_evidence_payload(impact_record)
    json_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return json_str.encode("utf-8")


def compute_evidence_hash(impact_record: Dict[str, Any]) -> str:
    """Computes deterministic SHA-256 evidence hash prefixed with 'sha256:'.

    Args:
        impact_record: Dictionary or mapping containing impact record attributes.

    Returns:
        Lowercase hex SHA-256 digest string prefixed with 'sha256:'.
    """
    data = serialize_canonical_payload(impact_record)
    digest = hashlib.sha256(data).hexdigest().lower()
    return f"sha256:{digest}"


def compute_keccak256_hash(impact_record: Dict[str, Any]) -> str:
    """Computes deterministic Keccak-256 evidence hash prefixed with 'keccak256:'.

    Gracefully attempts to use eth_hash, web3, or pycryptodome if installed. If no Keccak-256
    provider is available in the environment, raises a descriptive NotImplementedError.

    Args:
        impact_record: Dictionary containing impact record attributes.

    Returns:
        Lowercase hex Keccak-256 digest string prefixed with 'keccak256:'.

    Raises:
        NotImplementedError: If no Keccak-256 implementation is installed.
    """
    data = serialize_canonical_payload(impact_record)

    # 1. Try eth_hash
    try:
        from eth_hash.auto import keccak as eth_keccak  # type: ignore
        digest = eth_keccak(data).hex().lower()
        return f"keccak256:{digest}"
    except (ImportError, Exception):
        pass

    # 2. Try web3
    try:
        from web3 import Web3  # type: ignore
        digest = Web3.keccak(data).hex().lower()
        if digest.startswith("0x"):
            digest = digest[2:]
        return f"keccak256:{digest}"
    except (ImportError, Exception):
        pass

    # 3. Try pycryptodome (Crypto.Hash.keccak)
    try:
        from Crypto.Hash import keccak as crypto_keccak  # type: ignore
        k = crypto_keccak.new(digest_bits=256)
        k.update(data)
        return f"keccak256:{k.hexdigest().lower()}"
    except (ImportError, Exception):
        pass

    # 4. Try sha3 module
    try:
        import sha3  # type: ignore
        digest = sha3.keccak_256(data).hexdigest().lower()
        return f"keccak256:{digest}"
    except (ImportError, Exception):
        pass

    raise NotImplementedError(
        "Keccak-256 digest calculation requires an installed EVM crypto provider "
        "(such as 'eth-hash', 'web3', or 'pycryptodome'). "
        "Please install via: pip install eth-hash[pycryptodome]"
    )


if __name__ == "__main__":
    sample_record = {
        "id": "imp-12345-uuid-to-ignore",
        "lot_id": "lot-e4b2d9a1-8711-4f92-911c-2f96e47b3109",
        "organization_id": "org-11111111-1111-1111-1111-111111111111",
        "facility_id": "fac-00000000-0000-0000-0000-000000000001",
        "event_type": "verified_recovered",
        "mass_kg": 5000.0,
        "co2e_avoided_kg": 71000.0,
        "created_at": "2026-10-24T02:00:00Z",
        "blockchain_tx_hash": "0xignore_this_volatile_field",
        "block_number": 19283746,
    }

    print("Canonical payload:")
    print(json.dumps(canonical_evidence_payload(sample_record), indent=2))
    sha_hash = compute_evidence_hash(sample_record)
    print(f"\nEvidence Hash (SHA-256): {sha_hash}")

    try:
        k_hash = compute_keccak256_hash(sample_record)
        print(f"Evidence Hash (Keccak-256): {k_hash}")
    except NotImplementedError as err:
        print(f"Evidence Hash (Keccak-256): [DEGRADED] {err}")
