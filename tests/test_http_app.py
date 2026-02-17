"""Unit tests for HTTP application endpoints.

Tests use Starlette TestClient for fast, synchronous testing without
spawning real servers or opening sockets.
"""

import pytest
from starlette.testclient import TestClient

from punie.agent.adapter import PunieAgent
from punie.http import HttpAppFactory, create_app


@pytest.fixture
def agent():
    """Create test agent."""
    return PunieAgent(model="test", name="test-agent")


def test_create_app_satisfies_http_app_factory() -> None:
    """Verify create_app satisfies HttpAppFactory protocol."""
    assert isinstance(create_app, HttpAppFactory)


def test_health_returns_ok(agent) -> None:
    """GET /health returns 200 with status ok."""
    client = TestClient(create_app(agent))
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_echo_returns_request_body(agent) -> None:
    """POST /echo returns the request body under 'echo' key."""
    client = TestClient(create_app(agent))
    test_data = {"message": "hello", "count": 42}
    response = client.post("/echo", json=test_data)
    assert response.status_code == 200
    assert response.json() == {"echo": test_data}


def test_echo_with_empty_body(agent) -> None:
    """POST /echo with empty JSON object returns empty echo."""
    client = TestClient(create_app(agent))
    response = client.post("/echo", json={})
    assert response.status_code == 200
    assert response.json() == {"echo": {}}


def test_echo_rejects_get(agent) -> None:
    """GET /echo returns 405 Method Not Allowed."""
    client = TestClient(create_app(agent))
    response = client.get("/echo")
    assert response.status_code == 405


def test_unknown_route_returns_404(agent) -> None:
    """Unknown routes return 404 Not Found."""
    client = TestClient(create_app(agent))
    response = client.get("/nonexistent")
    assert response.status_code == 404
