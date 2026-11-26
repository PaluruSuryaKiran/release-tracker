from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

from package_service import db
from package_service.db import get_session
from package_service.main import app

TYPE_BASE = "https://github.com/PaluruSuryaKiran/release-tracker#"


def test_engine_sets_statement_timeout_on_every_connection(engine):
    with db.engine.connect() as conn:
        value = conn.execute(text("SHOW statement_timeout")).scalar()
    assert value == f"{db.DB_STATEMENT_TIMEOUT_MS // 1000}s"


def test_slow_query_is_cancelled_by_postgres(engine):
    with db.engine.connect() as conn:
        conn.execute(text("SET LOCAL statement_timeout = 100"))
        with pytest.raises(OperationalError, match="statement timeout"):
            conn.execute(text("SELECT pg_sleep(1)"))


@pytest.mark.parametrize(
    "error",
    [
        OperationalError("SELECT ...", {}, Exception("connection refused")),
        PoolTimeoutError("QueuePool limit reached"),
    ],
)
def test_database_outage_returns_503(error):
    broken_session = MagicMock()
    broken_session.scalar.side_effect = error
    app.dependency_overrides[get_session] = lambda: broken_session
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/v1/packages/hello-world")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.headers["content-type"] == "application/problem+json"
    assert response.headers["retry-after"] == "5"
    assert response.json()["type"] == TYPE_BASE + "database-unavailable"
    assert "connection refused" not in response.text
    assert "SELECT" not in response.text
    assert "QueuePool" not in response.text