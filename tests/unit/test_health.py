from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint_returns_healthy() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    body = response.json()

    assert body["status"] == "healthy"
    assert body["service"] == "Asta"
    assert body["version"] == "0.1.0"
    assert body["environment"] == "development"


def test_health_endpoint_returns_request_id() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers

def test_request_id_is_preserved_when_provided() -> None:
    request_id = "asta-test-request-123"

    response = client.get(
        "/api/v1/health",
        headers={
            "X-Request-ID": request_id,
        },
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id