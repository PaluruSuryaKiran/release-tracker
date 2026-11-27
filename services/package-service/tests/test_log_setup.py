import json
import logging
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from package_service.db import get_session
from package_service.main import app
from package_service.log_setup import JsonFormatter, request_id_var


def test_response_gets_a_new_request_id(client):
    response = client.get("/livez")
    request_id = response.headers["X-Request-ID"]
    assert len(request_id) == 32
    assert client.get("/livez").headers["X-Request-ID"] != request_id


def test_valid_incoming_request_id_is_kept(client):
    response = client.get("/livez", headers={"X-Request-ID": "abc-123"})
    assert response.headers["X-Request-ID"] == "abc-123"


def test_invalid_incoming_request_id_is_replaced(client):
    for bad in ["has spaces", "x" * 129, "bad/char"]:
        response = client.get("/livez", headers={"X-Request-ID": bad})
        assert response.headers["X-Request-ID"] != bad


def test_error_responses_have_request_id(client):
    response = client.get("/v1/packages/nope", headers={"X-Request-ID": "trace-404"})
    assert response.status_code == 404
    assert response.headers["X-Request-ID"] == "trace-404"


def test_unexpected_error_response_has_request_id():
    broken_session = MagicMock()
    broken_session.scalar.side_effect = RuntimeError("boom")
    app.dependency_overrides[get_session] = lambda: broken_session
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/v1/packages/x", headers={"X-Request-ID": "trace-500"})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "trace-500"


def test_access_log_line_has_request_details(client, caplog):
    with caplog.at_level(logging.INFO, logger="package_service.access"):
        client.get("/v1/packages/nope", headers={"X-Request-ID": "trace-log"})
    [record] = [r for r in caplog.records if r.name == "package_service.access"]
    assert record.method == "GET"
    assert record.path == "/v1/packages/nope"
    assert record.status == 404
    assert record.duration_ms >= 0


def test_json_formatter_writes_one_json_object_with_request_id():
    record = logging.makeLogRecord(
        {"name": "test", "levelname": "INFO", "msg": "hello %s", "args": ("world",),
         "status": 200}
    )
    token = request_id_var.set("trace-json")
    try:
        line = JsonFormatter().format(record)
    finally:
        request_id_var.reset(token)

    assert "\n" not in line
    entry = json.loads(line)
    assert entry["message"] == "hello world"
    assert entry["level"] == "INFO"
    assert entry["request_id"] == "trace-json"
    assert entry["status"] == 200
    assert entry["time"].endswith("+00:00")