import pytest
from fastapi.testclient import TestClient

from package_service.main import app

TYPE_BASE = "https://github.com/PaluruSuryaKiran/release-tracker#"

WRITES = [
    ("/v1/packages", {"name": "hello-world"}),
    ("/v1/packages/hello-world/releases", {"version": "1.0.0"}),
]


@pytest.fixture
def anonymous(engine):
    """A client that sends no API key."""
    return TestClient(app)


@pytest.mark.parametrize("url, body", WRITES)
def test_write_without_key_returns_401(anonymous, url, body):
    response = anonymous.post(url, json=body)
    assert response.status_code == 401
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json()["type"] == TYPE_BASE + "unauthorized"


@pytest.mark.parametrize(
    "header", ["Bearer wrong-key", "Bearer test-api-key-extra", "Basic test-api-key"]
)
def test_write_with_wrong_key_returns_401(anonymous, header):
    response = anonymous.post(
        "/v1/packages", json={"name": "hello-world"}, headers={"Authorization": header}
    )
    assert response.status_code == 401


def test_write_with_right_key_succeeds(client):
    assert client.post("/v1/packages", json={"name": "hello-world"}).status_code == 201


def test_reads_do_not_need_a_key(anonymous, add_package):
    add_package("hello-world")
    assert anonymous.get("/v1/packages/hello-world").status_code == 200
    assert anonymous.get("/livez").status_code == 200