from sqlalchemy import text

from package_service import db


def test_engine_can_connect():
    with db.engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar() == 1

def test_session_factory_settings():
    assert db.session_local.kw["expire_on_commit"] is False

def test_get_session_yields_working_session_and_closes_it():
    session_generator = db.get_session()
    session = next(session_generator)
    assert session.execute(text("SELECT 1")).scalar() == 1
    assert session.in_transaction()
    session_generator.close()
    assert not session.in_transaction()