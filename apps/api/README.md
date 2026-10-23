# STRATA API — Backend Foundation & Material Registry

Backend service for STRATA, the industrial circularity operating system. Built with FastAPI, Pydantic v2, and SQLAlchemy.

---

## 1. Quick Start

### 1.1 Prerequisites
- Python 3.10+
- (Optional) Docker & Docker Compose for local PostgreSQL and Redis

### 1.2 Local Setup

1. **Environment Configuration**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   Or editable install:
   ```bash
   pip install -e ".[dev]"
   ```

3. **(Optional) Start PostgreSQL and Redis via Docker Compose**:
   ```bash
   docker compose -f infra/docker-compose.yml up -d
   ```
   *Note: By default, `DATABASE_URL` is set to `sqlite:///./strata.db` so the API is immediately runnable without Docker.*

4. **Run the Development Server**:
   ```bash
   uvicorn strata.main:app --reload --host 0.0.0.0 --port 8000
   ```
   The interactive OpenAPI docs will be available at:
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

---

## 2. Running Automated Tests

Run the full pytest suite from the repository root or `apps/api`:
```bash
python -m pytest apps/api/tests -v
```

Tests run automatically against an isolated, fast in-memory SQLite database without requiring external services.

---

## 3. Implemented Endpoints (`/api/v1`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` or `/api/v1/health` | Liveness and database connectivity health check |
| `GET` | `/api/v1/materials/types` | Lists the authoritative circularity material taxonomy |
| `POST` | `/api/v1/materials/lots` | Registers a new material lot scoped to the authenticated tenant organization |
| `GET` | `/api/v1/materials/lots/{lot_id}` | Retrieves a single material lot by UUID (tenant-enforced) |
| `GET` | `/api/v1/materials/lots` | Lists registered material lots with pagination and filters |

For complete payload schemas, enums, and response envelopes, see [`docs/architecture/frontend-backend-contract.md`](../../docs/architecture/frontend-backend-contract.md).
