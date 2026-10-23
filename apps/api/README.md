# STRATA API — Backend Foundation & Material Registry

Backend service for STRATA, the industrial circularity operating system. Built with FastAPI, Pydantic v2, and SQLAlchemy.

---

## 1. Architecture & Persistence Strategy

* **Authoritative Decision Engine**: FastAPI remains strictly responsible for domain logic, proof path evaluation, and multi-tenant authorization.
* **Primary Durable Store**: Supabase PostgreSQL is the primary persistent database.
* **Database Migrations**: Managed via Alembic (`apps/api/migrations`), ensuring schema synchronization across local development and cloud Supabase environments.
* **Zero Silent Fallback**: The backend connects directly to the configured `DATABASE_URL`. If the database is unreachable, requests fail explicitly with error status rather than silently falling back to in-memory persistence.
* **Future Supabase Integration Points**:
  - *Supabase Auth*: Currently mocked via tenant headers (`X-Org-Id`, `X-User-Id`) for isolated development; future slices can integrate Supabase JWT validation into FastAPI's authentication dependency.
  - *Supabase Storage*: Future document management slices will store raw physical assay PDFs, SDS documents, and lab certificates in private Supabase Storage buckets, referencing them via `document_ref` in `evidence_records`.

---

## 2. Quick Start & Setup

### 2.1 Prerequisites
- Python 3.10+
- (Optional) Active Supabase project or Docker for local PostgreSQL

### 2.2 Environment Configuration

Copy `.env.example` to `.env` in the repository root:
```bash
cp .env.example .env
```

#### Supabase Dashboard Settings
In your Supabase project dashboard, locate the following configuration values:
1. **Database Connection URI**: Go to **Project Settings -> Database -> Connection String -> URI**. Select Mode: `URI`.
   Set this as `DATABASE_URL`:
   ```bash
   DATABASE_URL=postgresql://postgres:<YOUR-DATABASE-PASSWORD>@db.<YOUR-PROJECT-REF>.supabase.co:5432/postgres?sslmode=require
   ```
   *(Alternatively, for pooled connections, use port `6543` with transaction pooler).*
2. **API Credentials**: Go to **Project Settings -> API**:
   - `Project URL`: Copy to `SUPABASE_URL`
   - `anon / public key`: Copy to `SUPABASE_PUBLISHABLE_KEY`
   - `service_role key`: Copy to `SUPABASE_SERVICE_ROLE_KEY` *(Backend only — never expose to frontend)*

*Note: For zero-setup local offline development, keep the default `DATABASE_URL=sqlite:///./strata.db`.*

### 2.3 Applying Migrations

Run database migrations to initialize or update all tables (`organizations`, `facilities`, `material_lots`, `evidence_records`, `investigations`, `qualification_assessments`):

From repository root:
```bash
python -m alembic upgrade head
```
Or from `apps/api`:
```bash
alembic upgrade head
```

### 2.4 Running the Development Server

Start the FastAPI application:
```bash
uvicorn strata.main:app --reload --host 0.0.0.0 --port 8000
```
Or from `apps/api`:
```bash
python -m uvicorn strata.main:app --reload
```

The interactive OpenAPI docs will be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Health check: `http://localhost:8000/api/v1/health`

---

## 3. Running Automated Tests

Run the full pytest suite from the repository root:
```bash
python -m pytest apps/api/tests -v
```

* **Unit & Integration Tests**: Run in ~0.5s against an isolated in-memory SQLite database without requiring live cloud credentials or external services.
* **Live Supabase Verification Test**: To verify live connectivity against an active Supabase project:
  ```bash
  $env:STRATA_TEST_LIVE_SUPABASE="1"
  python -m pytest apps/api/tests/integration/test_persistence.py -k test_live_supabase_connectivity -v
  ```

---

## 4. Implemented Endpoints (`/api/v1`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` or `/api/v1/health` | Liveness and database connectivity health check |
| `GET` | `/api/v1/materials/types` | Lists the authoritative circularity material taxonomy |
| `POST` | `/api/v1/materials/lots` | Registers a new material lot scoped to the authenticated tenant organization |
| `GET` | `/api/v1/materials/lots/{lot_id}` | Retrieves a single material lot by UUID (tenant-enforced) |
| `GET` | `/api/v1/materials/lots` | Lists registered material lots with pagination and filters |
| `POST` | `/api/v1/evidence` | Records immutable audit-grade evidence for a material lot |
| `GET` | `/api/v1/lots/{lot_id}/evidence` | Lists evidence claims for a lot |
| `POST` | `/api/v1/investigations` | Executes deterministic ProofPath qualification assessment |
| `GET` | `/api/v1/investigations/{id}` | Retrieves qualification investigation details and outcomes |
| `GET` | `/api/v1/lots/{lot_id}/routes` | Retrieves candidate route assessments for a lot |

For complete payload schemas, enums, and response envelopes, see [`docs/architecture/frontend-backend-contract.md`](../../docs/architecture/frontend-backend-contract.md).
