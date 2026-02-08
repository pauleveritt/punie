"""Unit tests for HTTP application endpoints.

Tests use Starlette TestClient for fast, synchronous testing without
spawning real servers or opening sockets.
"""

from starlette.testclient import TestClient

from punie.http import HttpAppFactory, create_app


def test_create_app_satisfies_http_app_factory() -> None:
    """Verify create_app satisfies HttpAppFactory protocol."""
    assert isinstance(create_app, HttpAppFactory)


def test_health_returns_ok() -> None:
    """GET /health returns 200 with status ok."""
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_echo_returns_request_body() -> None:
    """POST /echo returns the request body under 'echo' key."""
    client = TestClient(create_app())
    test_data = {"message": "hello", "count": 42}
    response = client.post("/echo", json=test_data)
    assert response.status_code == 200
    assert response.json() == {"echo": test_data}


def test_echo_with_empty_body() -> None:
    """POST /echo with empty JSON object returns empty echo."""
    client = TestClient(create_app())
    response = client.post("/echo", json={})
    assert response.status_code == 200
    assert response.json() == {"echo": {}}


def test_echo_rejects_get() -> None:
    """GET /echo returns 405 Method Not Allowed."""
    client = TestClient(create_app())
    response = client.get("/echo")
    assert response.status_code == 405


def test_unknown_route_returns_404() -> None:
    """Unknown routes return 404 Not Found."""
    client = TestClient(create_app())
    response = client.get("/nonexistent")
    assert response.status_code == 404
