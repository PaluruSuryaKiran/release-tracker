from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from package_service.db import get_session
from package_service.main import app


def broken_session():
    session = MagicMock()
    session.execute.side_effect = OperationalError(
        "SELECT 1", {}, Exception("connection refused")
    )
    return session


def test_livez_returns_200(client):
    response = client.get("/livez")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_is_an_alias_of_livez(client):
    assert client.get("/health").json() == client.get("/livez").json()


def test_readyz_returns_200_when_database_answers(client):
    response = client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readyz_returns_503_when_database_is_down():
    app.dependency_overrides[get_session] = broken_session
    try:
        response = TestClient(app).get("/readyz")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["type"].endswith("#not-ready")
    assert "connection refused" not in response.text


def test_livez_ignores_database_outage():
    app.dependency_overrides[get_session] = broken_session
    try:
        response = TestClient(app).get("/livez")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200