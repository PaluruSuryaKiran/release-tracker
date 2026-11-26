from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from package_service.db import get_session
from package_service.main import app

PROBLEM_FIELDS = {"type", "title", "status", "detail", "instance"}
TYPE_BASE = "https://github.com/PaluruSuryaKiran/release-tracker#"


def assert_problem(response, status):
    assert response.status_code == status
    assert response.headers["content-type"] == "application/problem+json"
    body = response.json()
    assert PROBLEM_FIELDS <= body.keys()
    assert body["status"] == status
    return body


def test_package_not_found(client):
    body = assert_problem(client.get("/v1/packages/nope"), 404)
    assert body["type"] == TYPE_BASE + "package-not-found"
    assert body["title"] == "Package not found"
    assert "nope" in body["detail"]
    assert body["instance"] == "/v1/packages/nope"


def test_release_not_found(client, add_package):
    add_package("hello-world")
    body = assert_problem(client.get("/v1/packages/hello-world/releases/9.9.9"), 404)
    assert body["type"] == TYPE_BASE + "release-not-found"


def test_package_exists(client, add_package):
    add_package("hello-world")
    body = assert_problem(client.post("/v1/packages", json={"name": "hello-world"}), 409)
    assert body["type"] == TYPE_BASE + "package-exists"


def test_release_exists(client, add_package):
    add_package("hello-world", ["1.0.0"])
    response = client.post(
        "/v1/packages/hello-world/releases", json={"version": "1.0.0"}
    )
    body = assert_problem(response, 409)
    assert body["type"] == TYPE_BASE + "release-exists"


def test_validation_error_lists_each_field(client):
    response = client.post("/v1/packages", json={"name": "Bad_Name", "id": 5})
    body = assert_problem(response, 422)
    assert body["type"] == TYPE_BASE + "invalid-request"
    fields = {error["field"] for error in body["errors"]}
    assert fields == {"name", "id"}
    assert all(error["message"] for error in body["errors"])


def test_unknown_route_uses_about_blank(client):
    body = assert_problem(client.get("/v1/nothing-here"), 404)
    assert body["type"] == "about:blank"
    assert body["title"] == "Not Found"


def test_wrong_method_keeps_allow_header(client):
    response = client.delete("/v1/packages/hello-world")
    body = assert_problem(response, 405)
    assert body["type"] == "about:blank"
    assert "GET" in response.headers["allow"]


def test_unexpected_error_returns_500_without_leaking_details():
    broken_session = MagicMock()
    broken_session.scalar.side_effect = RuntimeError("confidential information")
    app.dependency_overrides[get_session] = lambda: broken_session
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/v1/packages/hello-world")
    finally:
        app.dependency_overrides.clear()

    body = assert_problem(response, 500)
    assert body["type"] == "about:blank"
    assert "confidential information" not in response.text