import pytest

def test_create_package_returns_201_and_body(client):
    response = client.post(
        "/v1/packages", json={"name": "curl", "description": "transfer tool"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "curl"
    assert body["description"] == "transfer tool"
    assert body["latest_version"] is None
    assert "created_at" in body
    assert "id" not in body


def test_create_package_twice_returns_409(client):
    client.post("/v1/packages", json={"name": "curl"})
    response = client.post("/v1/packages", json={"name": "curl"})
    assert response.status_code == 409


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": "Curl"},
        {"name": "1curl"},
        {"name": "c"},
        {"name": "my_tool"},
        {"name": "curl", "id": 5},
        {"name": "curl", "description": "x" * 501},
    ],
)
def test_create_package_invalid_body_returns_422(client, payload):
    response = client.post("/v1/packages", json=payload)
    assert response.status_code == 422


def test_get_package_returns_200_and_body(client):
    client.post("/v1/packages", json={"name": "curl", "description": "transfer tool"})
    response = client.get("/v1/packages/curl")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "curl"
    assert body["description"] == "transfer tool"
    assert "created_at" in body
    assert "latest_version" in body


def test_get_package_without_releases_has_null_latest(client, add_package):
    add_package("curl")
    response = client.get("/v1/packages/curl")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "curl"
    assert body["latest_version"] is None
    assert "id" not in body


def test_get_package_latest_is_numeric_not_text_order(client, add_package):
    add_package("curl", ["1.2.0", "1.9.0", "1.10.0"])
    response = client.get("/v1/packages/curl")
    assert response.json()["latest_version"] == "1.10.0"


def test_get_package_latest_is_highest_not_newest(client, add_package):
    add_package("curl", ["2.0.0", "1.5.0"])
    response = client.get("/v1/packages/curl")
    assert response.json()["latest_version"] == "2.0.0"


def test_get_package_ignores_other_packages_releases(client, add_package):
    add_package("curl", ["8.5.0"])
    add_package("wget", ["1.21.0", "1.24.5"])
    assert client.get("/v1/packages/curl").json()["latest_version"] == "8.5.0"
    assert client.get("/v1/packages/wget").json()["latest_version"] == "1.24.5"


def test_get_package_matches_create_response_shape(client):
    created = client.post("/v1/packages", json={"name": "curl"}).json()
    fetched = client.get("/v1/packages/curl").json()
    assert created == fetched


def test_get_unknown_package_returns_404(client):
    response = client.get("/v1/packages/nope")
    assert response.status_code == 404
    assert "nope" in response.json()["detail"]


def test_get_package_name_is_case_sensitive(client, add_package):
    add_package("curl")
    assert client.get("/v1/packages/Curl").status_code == 404


def test_package_endpoints_are_only_under_v1(client):
    assert client.post("/packages", json={"name": "curl"}).status_code == 404
    assert client.get("/packages/curl").status_code == 404


def test_create_package_sets_location_header(client):
    response = client.post("/v1/packages", json={"name": "hello-world"})
    assert response.status_code == 201
    assert response.headers["Location"] == "/v1/packages/hello-world"
    assert client.get(response.headers["Location"]).status_code == 200


def test_failed_create_has_no_location_header(client):
    client.post("/v1/packages", json={"name": "hello-world"})
    response = client.post("/v1/packages", json={"name": "hello-world"})
    assert response.status_code == 409
    assert "Location" not in response.headers