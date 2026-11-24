import pytest


def test_create_release_returns_201_and_body(client, add_package):
    add_package("curl")
    response = client.post("/v1/packages/curl/releases", json={"version": "8.5.0"})
    assert response.status_code == 201
    body = response.json()
    assert body["version"] == "8.5.0"
    assert "released_at" in body
    assert "id" not in body
    assert "package_id" not in body


def test_create_release_updates_latest_version(client, add_package):
    add_package("curl", ["1.9.0"])
    client.post("/v1/packages/curl/releases", json={"version": "1.10.0"})
    assert client.get("/v1/packages/curl").json()["latest_version"] == "1.10.0"


def test_create_release_for_unknown_package_returns_404(client):
    response = client.post("/v1/packages/nope/releases", json={"version": "1.0.0"})
    assert response.status_code == 404
    assert "nope" in response.json()["detail"]


def test_create_same_release_twice_returns_409(client, add_package):
    add_package("curl")
    client.post("/v1/packages/curl/releases", json={"version": "1.0.0"})
    response = client.post("/v1/packages/curl/releases", json={"version": "1.0.0"})
    assert response.status_code == 409
    assert "1.0.0" in response.json()["detail"]


def test_same_version_on_different_packages_is_allowed(client, add_package):
    add_package("curl")
    add_package("wget")
    assert client.post("/v1/packages/curl/releases", json={"version": "1.0.0"}).status_code == 201
    assert client.post("/v1/packages/wget/releases", json={"version": "1.0.0"}).status_code == 201


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"version": 1},
        {"version": "1.2"},
        {"version": "1.2.3.4"},
        {"version": "v1.2.3"},
        {"version": "01.2.3"},
        {"version": "1.2.3 "},
        {"version": "12345678.12345.1"},
        {"version": "99999999999.0.0"},
        {"version": "1.0.0", "package_id": 5},
    ],
)
def test_create_release_invalid_body_returns_422(client, add_package, payload):
    add_package("curl")
    response = client.post("/v1/packages/curl/releases", json=payload)
    assert response.status_code == 422