# ADR-0001: Initial Application Architecture — Modular Monolith with Asynchronous Workers

- **Status:** Accepted
- **Date:** 2026-10-23
- **Deciders:** Aarushi Sachdeva (Backend/AI), Saishree (Frontend), Hitendra (Exchange/Cluster)
- **Consulted:** STRATA Product Design Document, Work Distribution and Parallel Implementation Plan

---

## 1. Context and Problem Statement

STRATA is an industrial circularity operating system designed to evaluate material recovery opportunities, qualify reuse and recycling pathways, orchestrate industrial exchange workflows, and calculate audit-grade environmental and economic impacts.

The engineering challenge requires:
1. Supporting multiple interconnected functional modules (Material Registry, ProofPath Qualification, Industrial Exchange, Prevention Intelligence, Evidence Graph, Impact Ledger, and Municipal/Cluster Intelligence).
2. Enabling three parallel engineering streams (Foundations/AI, Frontend, and Marketplace/Logistics) without continuous merge conflicts or cross-team blocking.
3. Ensuring regulatory defensibility, strict multi-tenant data boundaries, and auditability.
4. Handling asynchronous, long-running evidence-gathering tasks (TinyFish discovery, document extraction, route evaluations) without degrading synchronous API responsiveness.

A decision is required regarding the top-level architectural style, the distribution of responsibilities between synchronous API and asynchronous workers, and the governance of AI-generated insights versus deterministic business logic.

---

## 2. Decision Drivers

- **Simplicity and velocity:** Rapid iteration during Phase 1 without the distributed operational overhead of microservices (distributed tracing, network partitions, multi-repo versioning).
- **Domain encapsulation:** Clean separation of concerns between core domains to enable parallel feature development by Aarushi, Saishree, and Hitendra.
- **Evidence provenance and determinism:** Industrial qualification and carbon accounting require reproducible calculations and auditable claims. LLM outputs must never bypass deterministic qualification rules or make unapproved financial/marketplace commitments.
- **Responsive user experience:** Scraping, document processing, and multi-step route evaluations can take seconds or minutes and must run asynchronously via job queues.

---

## 3. Considered Options

1. **Distributed Microservices:** Separate deployable services for Materials, Qualification, Marketplace, Impact, and Municipal.
2. **Standard Monolith (Synchronous):** Single web service running all operations synchronously in-process.
3. **Modular Monolith with Asynchronous Task Workers:** Single unified FastAPI codebase organized into explicit domain modules sharing a transactional database, paired with Redis-backed background workers for long-running workflows.

---

## 4. Decision Outcome

**Chosen Option:** **Option 3: Modular Monolith with Asynchronous Task Workers**.

### 4.1 Architecture Overview

- **Core Backend (`apps/api`):** FastAPI application structured as a modular monolith.
  - Domain packages: `domain/materials`, `domain/qualification`, `domain/marketplace`, `domain/prevention`, `domain/impact`, `domain/municipal`.
  - Shared infrastructure: `core/config.py`, `core/auth.py`, `db/`.
  - Canonical contracts: `schemas/` defining Pydantic models shared across domains.
- **Frontend (`apps/web`):** Next.js 14 (App Router) with TypeScript.
  - Decoupled via `docs/architecture/frontend-backend-contract.md`.
  - Supports local mock adapter toggled via `NEXT_PUBLIC_USE_MOCK_DATA`.
- **Background Workers (`services/` and `apps/api/src/strata/workers/`):**
  - Redis queue backed task workers for TinyFish web discovery, unstructured document extraction, deep qualification pipeline evaluations, and lifecycle impact computations.
- **Persistence:**
  - Primary Relational Database: PostgreSQL 16 (with JSONB for flexible material specifications and Alembic for schema migrations).
  - Cache & Message Broker: Redis 7.

### 4.2 Core Principles and Constraints

1. **Domain Encapsulation:**
   - Modules communicate through defined service interfaces or schema contracts, not direct cross-module table mutations.
   - Circular Exchange (`domain/marketplace`) queries the qualification service interface to evaluate route eligibility rather than embedding duplicate logic.
2. **Deterministic Rules & Advisory AI:**
   - All regulatory, threshold, and hard gate evaluations (e.g. hazardous contamination thresholds, transport permit checks) are evaluated by deterministic rule functions.
   - LLM agents and web search (TinyFish) serve strictly as evidence gatherers and extractors. LLM outputs must carry source attribution and provenance labels (`verified`, `source_supported`, `user_supplied`, `inferred`, `synthetic_demo`).
   - A qualification assessment cannot be marked `supported` if any hard constraint fails, regardless of any probabilistic scoring.
3. **Human-in-the-Loop Marketplace Governance:**
   - Critical commercial actions (sending an RFQ, accepting a quote, approving dispatch/receipt) require explicit user authorization. Automated agents cannot commit transactions without human sign-off.
4. **Tenant Isolation:**
   - All material and commercial records are partitioned by `org_id`. Cross-tenant discovery is mediated exclusively through published exchange listings or approved aggregated cluster/municipal views.

---

## 5. Consequences

### Positive Consequences
- Low operational complexity: local development requires only Docker Compose (Postgres + Redis) and standard package managers.
- Shared transactional consistency across lot registration and initial qualification logging.
- Clear team ownership:
  - Aarushi: Backend foundations, schemas, `materials`, `qualification`, worker orchestrations.
  - Saishree: Frontend components, app shell, mock layer, design system.
  - Hitendra: `marketplace`, RFQ workflows, event logging, cluster/municipal aggregation.
- Eliminates distributed transaction failures and network latency between internal domains.

### Negative Consequences / Risks
- In-process module boundaries can blur if developers import internal repositories or models directly across domains instead of using schema boundaries.
- Database migrations require coordination across domain owners.

---

## 6. Compliance and Review

- Linting and test rules will enforce domain boundary separation.
- Database migrations touching shared entities must be reviewed by the contract coordinator (Aarushi).
- Future architectural transitions to independent microservices can be executed if specific worker domains (e.g., TinyFish discovery or heavy document OCR) demand isolated scaling profiles.
