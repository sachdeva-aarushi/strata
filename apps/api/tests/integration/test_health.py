from fastapi.testclient import TestClient


def test_root_health_check(client: TestClient):
    """Verifies the root /health endpoint responds with healthy status and standard envelope."""
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert body["data"]["status"] == "healthy"
    assert body["data"]["service"] == "STRATA"
    assert body["data"]["database"] == "connected"


def test_api_v1_health_check(client: TestClient):
    """Verifies the versioned /api/v1/health endpoint behaves identically."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["status"] == "healthy"
    assert body["data"]["database"] == "connected"
