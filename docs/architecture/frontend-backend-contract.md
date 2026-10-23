# STRATA — Frontend-Backend API Contract

> Version: 0.1 (pre-implementation — agreed design, not yet validated against live code)
> Contract coordinator: Aarushi Sachdeva
> Frontend owner: Saishree
> Exchange/cluster/municipal owner: Hitendra
>
> Any change to this document that alters entity shapes, status enums, or error formats
> MUST be announced to all owners before implementation and reflected in a coordinated PR.
> Update the version and date when any field or semantic changes.

---

## 1. API conventions

### 1.1 Base path and versioning

All API calls use the prefix:

```
/api/v1
```

Breaking changes increment the version to v2. Additive (non-breaking) changes may be added to v1 with a contract note and date.

### 1.2 Request and response format

- All bodies: `application/json`
- All dates and timestamps: ISO 8601 UTC — `2026-10-23T10:00:00Z`
- All quantities: numeric value + unit sent as separate fields (not a combined string)
- Empty optional fields: omit the key entirely; do not send `null` unless explicitly documented
- IDs: UUIDs (string), e.g. `"lot_id": "550e8400-e29b-41d4-a716-446655440000"`

### 1.3 Standard envelope

All responses (success and error) use this top-level shape:

**Success:**
```json
{
  "data": { ... },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-10-23T10:00:00Z"
  }
}
```

**Paginated list:**
```json
{
  "data": [ ... ],
  "pagination": {
    "total": 84,
    "page": 1,
    "page_size": 20,
    "has_next": true
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-10-23T10:00:00Z"
  }
}
```

**Error:**
```json
{
  "error": {
    "code": "MATERIAL_LOT_NOT_FOUND",
    "message": "No material lot with ID 550e8400 exists for this organization.",
    "details": {}
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "2026-10-23T10:00:00Z"
  }
}
```

### 1.4 HTTP status codes

| Code | When to use |
|------|-------------|
| 200 | Successful read or update |
| 201 | Resource created |
| 202 | Async job accepted; use job polling endpoint to check progress |
| 400 | Validation failure or malformed request |
| 401 | Missing or invalid authentication token |
| 403 | Authenticated but not authorized for this resource or action |
| 404 | Resource not found within the authenticated tenant scope |
| 409 | State conflict (e.g. duplicate event, invalid transition) |
| 422 | Request body structurally valid but semantically rejected |
| 500 | Internal server error; do not expose internals to client |

### 1.5 Idempotency

POST requests that create workflow events (RFQ sends, offer acceptances, shipment records)
MUST include an `idempotency_key` UUID in the request body. The server rejects duplicate
keys with 409 and returns the original result. Clients may retry on 5xx using the same key.

### 1.6 Tenant authorization

All resources are tenant-scoped. The authenticated user's organization context is resolved
server-side from the JWT. The frontend MUST NOT filter or hide resources by duplicating
authorization logic — the backend enforces boundaries.

---

## 2. Authentication

### 2.1 Token format

Bearer JWT in the `Authorization` header:

```
Authorization: Bearer <token>
```

### 2.2 Token claims (agreed minimum shape)

```json
{
  "sub": "user-uuid",
  "org_id": "org-uuid",
  "role": "facility_operator",
  "cluster_ids": ["cluster-uuid"],
  "exp": 1761264000
}
```

### 2.3 Roles (agreed enumeration)

| Role value | Description |
|------------|-------------|
| `facility_operator` | Facility-level operations and material records |
| `marketplace_participant` | Listings, RFQs, and quote management |
| `cluster_operator` | Cluster-level permissioned view and administration |
| `municipal_planner` | Approved aggregate view only |
| `platform_admin` | Platform operations and audit |

Frontend must read the role from the decoded token and render appropriate navigation.
Backend enforces the role on every endpoint.

---

## 3. Canonical entity IDs and shapes

These are the agreed object shapes that frontend TypeScript types and backend Pydantic schemas
MUST both conform to. Changes to these shapes require a coordinated update to both.

### 3.1 MaterialLot

```
lot_id            string (UUID)         Stable canonical identifier
material_type     string                From the agreed material taxonomy
quantity          number
unit              string                "kg" | "tonne" | "litre" | "m3" | "unit"
facility_id       string (UUID)
org_id            string (UUID)
status            MaterialLotStatus     See enum below
availability_from string (ISO date)
availability_to   string (ISO date)     Optional
declared_attributes object              Composition, contamination, physical form etc.
provenance_label  EvidenceStatus        How the declared attributes were established
created_at        string (ISO datetime)
updated_at        string (ISO datetime)
```

**MaterialLotStatus enum:**
```
draft
available
under_qualification
listed
matched
rfq_in_progress
order_confirmed
dispatched
received
outcome_recorded
withdrawn
```

### 3.2 QualificationAssessment

```
assessment_id      string (UUID)
lot_id             string (UUID)
candidate_route_id string (UUID)        Refers to a processor/route record
status             AssessmentStatus     See enum below
hard_gate_results  HardGateResult[]     One entry per evaluated hard constraint
missing_facts      MissingFact[]        Facts required before status can improve
rationale          string               Human-readable explanation; never expose raw LLM output
next_action        string               Specific recommended step
evidence_refs      EvidenceRef[]        Source records used in this assessment
rule_version       string               Version of the qualification rule set applied
assessed_at        string (ISO datetime)
```

**AssessmentStatus enum:**
```
supported          No blocking rule; required evidence meets threshold
conditional        One or more facts missing or uncertain; route is possible pending verification
unsupported        Hard incompatibility; this status CANNOT be overridden by a score
pending            Assessment job is running
failed             Assessment job failed; see error field
```

> The frontend MUST display `unsupported` assessments with a blocking indicator.
> A route with status `unsupported` MUST NOT advance to RFQ preparation.

**HardGateResult shape:**
```
gate_id            string
gate_name          string
outcome            "pass" | "fail" | "unknown"
material_value     any                  Observed value used in the check
required_value     any                  Processor requirement
evidence_ref_id    string (UUID)        Optional link to supporting evidence
```

**MissingFact shape:**
```
fact_id            string
description        string               What is needed and why
acquisition_method string               "lab_test" | "document" | "user_confirmation" | "external_source"
```

### 3.3 EvidenceRecord

```
evidence_id        string (UUID)
claim_text         string
source_url         string
source_title       string
retrieved_at       string (ISO datetime)
extraction_method  string               "tinyfish_fetch" | "user_upload" | "erp_import" | "manual_entry"
evidence_status    EvidenceStatus       See enum below
claim_subject      string               What the claim is about
supporting_passage string               Optional excerpt from source
verified_by        string               Optional user ID or system identifier
contradicted_by    string[]             IDs of contradicting evidence records
```

**EvidenceStatus enum (canonical provenance labels):**
```
verified              Independently confirmed through a defined verification process
source_supported      Supported by an identified external source; not independently confirmed
user_supplied         Entered or asserted by an authorized user
inferred              Derived from available information; not directly observed
estimated             Calculated or approximated; not measured
synthetic_demo        Generated for testing or demonstration; MUST be labeled as such in UI
stale                 Source freshness policy exceeded; requires recheck
```

> The frontend MUST display the evidence status label alongside any claim.
> `synthetic_demo` content MUST be visually distinct and never presented as real data.

### 3.4 ExchangeListing

```
listing_id         string (UUID)
lot_id             string (UUID)
org_id             string (UUID)
quantity           number
unit               string
status             ListingStatus        See enum below
visibility         "private" | "cluster" | "public"
commercial_terms   object               Optional indicative price/terms
availability_from  string (ISO date)
availability_to    string (ISO date)    Optional
created_at         string (ISO datetime)
updated_at         string (ISO datetime)
```

**ListingStatus enum:**
```
draft
published
under_qualification
qualified_candidate
needs_evidence
not_suitable
rfq_prepared
awaiting_approval
rfq_sent
quote_received
quote_reviewed
order_approved
dispatched
received
processing_confirmed
outcome_recorded
cancelled
```

### 3.5 RFQ

```
rfq_id             string (UUID)
listing_id         string (UUID)
lot_id             string (UUID)
sender_org_id      string (UUID)
recipient_org_id   string (UUID)
status             RFQStatus            See enum below
quantity           number
unit               string
message            string               Optional context
idempotency_key    string (UUID)        Required for POST
approved_by        string               User ID of approving actor
approved_at        string (ISO datetime)
created_at         string (ISO datetime)
updated_at         string (ISO datetime)
```

**RFQStatus enum:**
```
draft
awaiting_approval
sent
quote_received
accepted
rejected
withdrawn
expired
```

### 3.6 WorkflowEvent

```
event_id           string (UUID)
event_type         WorkflowEventType    See enum below
entity_id          string (UUID)        ID of the lot, listing, RFQ, or order
entity_type        string               "lot" | "listing" | "rfq" | "order" | "shipment"
actor_id           string (UUID)        User or system that created the event
quantity           number               Optional; for shipment/receipt events
unit               string               Optional
document_ref       string               Optional object-storage reference
notes              string               Optional
idempotency_key    string (UUID)        Required for POST
occurred_at        string (ISO datetime)
recorded_at        string (ISO datetime)
```

**WorkflowEventType enum:**
```
lot_registered
lot_updated
lot_listed
qualification_started
qualification_completed
rfq_created
rfq_approved
rfq_sent
quote_received
quote_accepted
order_confirmed
shipment_dispatched
shipment_received
processing_confirmed
outcome_recorded
event_cancelled
```

### 3.7 ImpactCalculation

```
calculation_id     string (UUID)
lot_id             string (UUID)
linked_event_ids   string[]             WorkflowEvent IDs that support this calculation
lifecycle_stage    ImpactStage          See enum below
method_id          string               Versioned methodology identifier
method_version     string
quantity           number               Verified quantity this calculation applies to
unit               string
metric_type        string               "co2e_kg" | "water_litres" | "disposal_kg_avoided"
metric_value       number               Calculated result
assumptions        object               Key-value pairs of inputs and factor sources
uncertainty_pct    number               Optional
verification_state string               "estimated" | "verified"
calculated_at      string (ISO datetime)
```

**ImpactStage enum — these are NOT interchangeable and MUST remain distinct in the UI:**
```
material_listed
material_matched
material_offered
material_dispatched
material_received
material_confirmed_processed
environmental_benefit_estimated
environmental_benefit_verified
```

> The frontend MUST display the lifecycle stage label on every impact figure.
> It MUST NOT aggregate across stages as if they represent the same thing.

---

## 4. API Endpoints (Phase 1 Scope & Status)

Endpoints marked **IMPLEMENTED & TESTED** are active in `apps/api` and covered by automated test suites.

| Method | Path | Purpose | Owner | Status |
|--------|------|---------|-------|--------|
| GET | /health | Liveness check & DB connectivity; no auth required | Aarushi | IMPLEMENTED & TESTED |
| GET | /api/v1/health | Versioned health check | Aarushi | IMPLEMENTED & TESTED |
| GET | /api/v1/materials/types | Retrieve authoritative material taxonomy | Aarushi | IMPLEMENTED & TESTED |
| POST | /api/v1/materials/lots | Create a material lot (tenant-scoped) | Aarushi | IMPLEMENTED & TESTED |
| GET | /api/v1/materials/lots/{lot_id} | Retrieve single lot (tenant-scoped) | Aarushi | IMPLEMENTED & TESTED |
| GET | /api/v1/materials/lots | List lots with pagination & filtering | Aarushi | IMPLEMENTED & TESTED |
| POST | /api/v1/facilities/{facility_id}/waste-imports | Import CSV waste records | Aarushi | MISSING |
| POST | /api/v1/investigations | Start a qualification/discovery job | Aarushi | MISSING |
| GET | /api/v1/investigations/{investigation_id} | Poll job status and partial results | Aarushi | MISSING |
| GET | /api/v1/lots/{lot_id}/routes | Retrieve qualification assessments | Aarushi | MISSING |
| POST | /api/v1/verification-actions | Record an action or test result | Aarushi | MISSING |
| POST | /api/v1/exchange/listings | Create an exchange listing | Hitendra | MISSING |
| GET | /api/v1/exchange/listings | Search listings (buyer view) | Hitendra | MISSING |
| GET | /api/v1/exchange/listings/{listing_id} | Retrieve a listing | Hitendra | MISSING |
| POST | /api/v1/exchange/rfqs | Create an RFQ (approval required before send) | Hitendra | MISSING |
| POST | /api/v1/exchange/events | Record a workflow event | Hitendra | MISSING |
| GET | /api/v1/cluster/indicators | Aggregated cluster supply/demand | Hitendra | MISSING |
| GET | /api/v1/city/indicators | Approved aggregate city indicators | Hitendra | MISSING |
| POST | /api/v1/impact/calculations | Create a versioned impact calculation | Hitendra (Aarushi reviews) | MISSING |

### 4.1 Implemented Endpoint Examples

#### `GET /api/v1/health`
**Response (200 OK):**
```json
{
  "data": {
    "status": "healthy",
    "service": "STRATA",
    "environment": "development",
    "version": "0.1.0",
    "database": "connected"
  },
  "meta": {
    "request_id": "7b5879ea-0677-4b71-9c60-a8d67eead942",
    "timestamp": "2026-10-23T10:45:00Z"
  }
}
```

#### `GET /api/v1/materials/types`
**Response (200 OK):**
```json
{
  "data": [
    {
      "type_id": "aluminum-scrap",
      "name": "Aluminum Scrap / Offcuts",
      "category": "metallics",
      "standard_units": ["kg", "tonne"],
      "is_hazardous": false,
      "description": "Clean secondary aluminum stamping offcuts, extrusions, and swarf with known alloy designation."
    },
    {
      "type_id": "spent-isopropanol",
      "name": "Spent Isopropanol (IPA)",
      "category": "chemicals",
      "standard_units": ["litre", "m3"],
      "is_hazardous": true,
      "description": "Used industrial solvent from electronics or optical cleaning baths, >70% IPA purity."
    }
  ],
  "meta": {
    "request_id": "f516a2fa-13f5-46eb-a430-81f7ba7cfa55",
    "timestamp": "2026-10-23T10:45:00Z"
  }
}
```

#### `POST /api/v1/materials/lots`
**Request Headers:**
```
Authorization: Bearer <token> (or X-Org-Id, X-User-Id, X-Role in mock mode)
```
**Request Body:**
```json
{
  "material_type": "aluminum-scrap",
  "quantity": 1250.5,
  "unit": "kg",
  "facility_id": "fac-00000000-0000-0000-0000-000000000001",
  "availability_from": "2026-11-01",
  "availability_to": "2026-12-01",
  "declared_attributes": {
    "alloy": "6061-T6",
    "physical_form": "stamping_offcuts",
    "oil_contamination_pct": 0.2
  },
  "provenance_label": "user_supplied"
}
```
**Response (201 Created):**
```json
{
  "data": {
    "lot_id": "893c5240-8b1b-417f-b883-99fa41098bca",
    "org_id": "11111111-1111-1111-1111-111111111111",
    "facility_id": "fac-00000000-0000-0000-0000-000000000001",
    "material_type": "aluminum-scrap",
    "quantity": 1250.5,
    "unit": "kg",
    "status": "draft",
    "availability_from": "2026-11-01",
    "availability_to": "2026-12-01",
    "declared_attributes": {
      "alloy": "6061-T6",
      "physical_form": "stamping_offcuts",
      "oil_contamination_pct": 0.2
    },
    "provenance_label": "user_supplied",
    "created_at": "2026-10-23T10:46:00Z",
    "updated_at": "2026-10-23T10:46:00Z"
  },
  "meta": {
    "request_id": "4e73cba3-21c8-4796-bbdf-a29d661414e2",
    "timestamp": "2026-10-23T10:46:00Z"
  }
}
```

#### `GET /api/v1/materials/lots/{lot_id}`
**Response (200 OK):** returns single `MaterialLotRead` inside `ResponseEnvelope`.
**Response (404 Not Found):**
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Material lot with ID '00000000-0000-0000-0000-999999999999' was not found in your organization scope.",
    "details": {
      "lot_id": "00000000-0000-0000-0000-999999999999"
    }
  },
  "meta": {
    "request_id": "d04e5436-1e9b-449e-bc43-29a3eefc6655",
    "timestamp": "2026-10-23T10:46:05Z"
  }
}
```

#### `GET /api/v1/materials/lots?page=1&page_size=2`
**Response (200 OK):**
```json
{
  "data": [
    {
      "lot_id": "893c5240-8b1b-417f-b883-99fa41098bca",
      "org_id": "11111111-1111-1111-1111-111111111111",
      "facility_id": "fac-00000000-0000-0000-0000-000000000001",
      "material_type": "aluminum-scrap",
      "quantity": 1250.5,
      "unit": "kg",
      "status": "draft",
      "availability_from": "2026-11-01",
      "availability_to": "2026-12-01",
      "declared_attributes": { ... },
      "provenance_label": "user_supplied",
      "created_at": "2026-10-23T10:46:00Z",
      "updated_at": "2026-10-23T10:46:00Z"
    }
  ],
  "pagination": {
    "total": 5,
    "page": 1,
    "page_size": 2,
    "has_next": true
  },
  "meta": {
    "request_id": "b962770d-f215-4ba2-b364-7729ee94285d",
    "timestamp": "2026-10-23T10:46:10Z"
  }
}
```

---

## 5. Error codes

All error responses include a machine-readable `code` field. Frontend uses this to
render specific messages rather than parsing the `message` string.

| Code | HTTP status | Meaning |
|------|-------------|---------|
| UNAUTHORIZED | 401 | No valid token |
| FORBIDDEN | 403 | Authenticated but not permitted for this resource |
| RESOURCE_NOT_FOUND | 404 | Resource does not exist in this tenant scope |
| VALIDATION_ERROR | 400 | Field-level validation failed; see `details` |
| DUPLICATE_EVENT | 409 | Idempotency key already used |
| INVALID_STATE_TRANSITION | 409 | Requested transition is not permitted from current state |
| QUALIFICATION_HARD_BLOCK | 422 | Cannot advance to RFQ; assessment status is `unsupported` |
| APPROVAL_REQUIRED | 403 | Action requires explicit approval before execution |
| JOB_FAILED | 500 | Background job failed; check investigation status |
| INTERNAL_ERROR | 500 | Unexpected server error |

The frontend MUST handle all codes above and render a user-appropriate message.
It MUST NOT surface raw server error messages to end users.

---

## 6. Mock service contract (frontend development)

While backend endpoints are MISSING, Saishree's frontend uses a mock service layer
controlled by the environment variable:

```
NEXT_PUBLIC_USE_MOCK_DATA=true
```

Rules:
- Mock responses MUST conform to the exact shapes in Section 3
- Mock data MUST use synthetic_demo provenance labels on all EvidenceRecord entries
- Mock data MUST be visually labeled "Sample data — not real" in the UI
- The typed API client MUST accept a service adapter; mock and real adapters are interchangeable
- When NEXT_PUBLIC_USE_MOCK_DATA is false, production API failures MUST show an error state;
  the frontend MUST NOT silently fall back to mock data

---

## 7. Shared files requiring coordinated changes

Changes to these files affect multiple owners. Announce before editing and name a reviewer.

| File / area | Primary owner | Who must be notified |
|-------------|--------------|---------------------|
| apps/api/src/strata/schemas/ | Aarushi | Saishree (frontend types), Hitendra (exchange) |
| apps/api/src/strata/core/auth.py | Aarushi | Hitendra, Saishree |
| apps/api/src/strata/db/ (migrations) | Aarushi | Hitendra |
| apps/api/src/strata/core/config.py | Aarushi | Hitendra, Saishree |
| packages/contracts/ | Aarushi coordinates | All owners |
| apps/api/src/strata/domain/materials/ | Aarushi | Hitendra (exchange references lots) |
| apps/api/src/strata/domain/qualification/ | Aarushi | Hitendra (eligibility integration) |
| apps/api/src/strata/domain/marketplace/ | Hitendra | Aarushi (qualification hook) |
| This document | Aarushi coordinates | All owners |

---

## 8. Qualification integration rule

Hitendra's exchange module MUST call the qualification service, not re-implement eligibility logic.

The boundary is:
- Aarushi publishes: `POST /api/v1/investigations` and `GET /api/v1/lots/{id}/routes`
- Hitendra's listing/RFQ flow reads the assessment status from `GET /lots/{id}/routes`
- A listing/RFQ targeting a route with `AssessmentStatus = unsupported` MUST be blocked server-side
- The frontend enforces the same block visually but MUST NOT rely solely on frontend filtering

---

## 9. Change log

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-10-23 | 0.1 | Initial draft — canonical entities, enums, conventions, error codes | Aarushi |
