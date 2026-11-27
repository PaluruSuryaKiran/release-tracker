from limits import parse

from package_service import rate_limit

TYPE_BASE = "https://github.com/PaluruSuryaKiran/release-tracker#"


def test_api_returns_429_when_limit_is_reached(client, monkeypatch):
    monkeypatch.setattr(rate_limit, "RATE", parse("2/minute"))
    assert client.get("/v1/packages/nope").status_code == 404
    assert client.get("/v1/packages/nope").status_code == 404

    response = client.get("/v1/packages/nope")
    assert response.status_code == 429
    assert response.headers["content-type"] == "application/problem+json"
    assert 1 <= int(response.headers["Retry-After"]) <= 60
    assert response.json()["type"] == TYPE_BASE + "rate-limited"


def test_health_checks_are_not_rate_limited(client, monkeypatch):
    monkeypatch.setattr(rate_limit, "RATE", parse("1/minute"))
    for _ in range(5):
        assert client.get("/livez").status_code == 200