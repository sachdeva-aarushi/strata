// SPDX-License-Identifier: Apache-2.0
pragma solidity ^0.8.20;

/**
 * @title StrataImpactLedger
 * @notice Immutable, append-only anchor registry for STRATA verified circularity and impact events.
 * @dev Anchors canonical Keccak-256 evidence digests from STRATA's Verified Impact Ledger onto an EVM-compatible chain.
 *
 * Architecture Principles:
 *   - Minimal and auditable: holds zero user funds, zero custody, and has no upgradeability proxy risk.
 *   - Cryptographic non-repudiation: guarantees that a material recovery or prevention claim cannot be back-dated.
 *   - Duplicate prevention: strictly disallows registering the exact same evidence hash twice.
 */
contract StrataImpactLedger {
    // -------------------------------------------------------------------------
    // Structs
    // -------------------------------------------------------------------------

    /**
     * @notice Represents an anchored material lifecycle impact record.
     * @param evidenceHash Keccak-256 digest of the canonical off-chain impact record payload.
     * @param anchoredBy Address of the wallet / relayer that committed this event on-chain.
     * @param timestamp Unix timestamp (seconds) when the block containing this anchor was mined.
     * @param lotId STRATA canonical material lot UUID (off-chain reference identifier).
     * @param eventType Canonical lifecycle event classification (e.g. "verified_recovered").
     */
    struct ImpactEvent {
        bytes32 evidenceHash;
        address anchoredBy;
        uint256 timestamp;
        string lotId;
        string eventType;
    }

    // -------------------------------------------------------------------------
    // Storage
    // -------------------------------------------------------------------------

    /// @notice Ordered list of all anchored impact events.
    ImpactEvent[] private _impactEvents;

    /// @notice Tracks anchored evidence hashes to strictly prevent duplicate registrations.
    mapping(bytes32 => bool) private _anchoredHashes;

    // -------------------------------------------------------------------------
    // Events
    // -------------------------------------------------------------------------

    /**
     * @notice Emitted whenever a new circularity impact event is anchored to the blockchain.
     * @param recordIndex Zero-based chronological index of the anchored record.
     * @param evidenceHash Indexed Keccak-256 digest of the canonical evidence payload.
     * @param anchoredBy Indexed address that submitted the anchor transaction.
     * @param timestamp Block timestamp at the time of anchoring.
     * @param lotId Off-chain reference material lot UUID.
     * @param eventType Lifecycle stage outcome (e.g. "verified_recovered").
     */
    event ImpactEventAnchored(
        uint256 indexed recordIndex,
        bytes32 indexed evidenceHash,
        address indexed anchoredBy,
        uint256 timestamp,
        string lotId,
        string eventType
    );

    // -------------------------------------------------------------------------
    // Custom Errors
    // -------------------------------------------------------------------------

    /// @notice Thrown when attempting to anchor a zero bytes32 evidence hash.
    error ZeroEvidenceHash();

    /// @notice Thrown when lotId string is empty.
    error EmptyLotId();

    /// @notice Thrown when eventType string is empty.
    error EmptyEventType();

    /// @notice Thrown when attempting to register an evidence hash that has already been anchored.
    /// @param evidenceHash The duplicate evidence hash.
    error DuplicateEvidenceHash(bytes32 evidenceHash);

    /// @notice Thrown when querying a record index that does not exist.
    /// @param requestedIndex The out-of-bounds index requested.
    /// @param totalRecords The current total record count.
    error IndexOutOfBounds(uint256 requestedIndex, uint256 totalRecords);

    // -------------------------------------------------------------------------
    // Public Functions
    // -------------------------------------------------------------------------

    /**
     * @notice Anchors a verified impact evidence hash on-chain.
     * @dev Reverts if evidenceHash is zero, if lotId or eventType is empty, or if evidenceHash was already anchored.
     * @param evidenceHash Keccak-256 digest of canonical impact record payload.
     * @param lotId STRATA material lot UUID (non-empty string).
     * @param eventType Impact lifecycle stage identifier (non-empty string, e.g. "verified_recovered").
     * @return recordIndex The index assigned to this new anchored record.
     */
    function anchorImpactEvent(
        bytes32 evidenceHash,
        string calldata lotId,
        string calldata eventType
    ) external returns (uint256 recordIndex) {
        if (evidenceHash == bytes32(0)) {
            revert ZeroEvidenceHash();
        }
        if (bytes(lotId).length == 0) {
            revert EmptyLotId();
        }
        if (bytes(eventType).length == 0) {
            revert EmptyEventType();
        }
        if (_anchoredHashes[evidenceHash]) {
            revert DuplicateEvidenceHash(evidenceHash);
        }

        recordIndex = _impactEvents.length;

        _anchoredHashes[evidenceHash] = true;
        _impactEvents.push(
            ImpactEvent({
                evidenceHash: evidenceHash,
                anchoredBy: msg.sender,
                timestamp: block.timestamp,
                lotId: lotId,
                eventType: eventType
            })
        );

        emit ImpactEventAnchored(
            recordIndex,
            evidenceHash,
            msg.sender,
            block.timestamp,
            lotId,
            eventType
        );

        return recordIndex;
    }

    /**
     * @notice Retrieves an anchored impact record by its chronological index.
     * @param index The zero-based index of the record to retrieve.
     * @return The ImpactEvent struct stored at the specified index.
     */
    function getImpactEvent(uint256 index) external view returns (ImpactEvent memory) {
        if (index >= _impactEvents.length) {
            revert IndexOutOfBounds(index, _impactEvents.length);
        }
        return _impactEvents[index];
    }

    /**
     * @notice Returns the total count of impact events anchored in this ledger.
     * @return Total count of anchored impact events.
     */
    function getImpactEventCount() external view returns (uint256) {
        return _impactEvents.length;
    }

    /**
     * @notice Checks whether an evidence hash has already been anchored.
     * @param evidenceHash The bytes32 hash to query.
     * @return True if the evidence hash has already been registered, false otherwise.
     */
    function isEvidenceHashAnchored(bytes32 evidenceHash) external view returns (bool) {
        return _anchoredHashes[evidenceHash];
    }
}
