import os

from dotenv import load_dotenv

load_dotenv()

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is not set. Copy .env.example to .env and fill it in.")
if TEST_DATABASE_URL == os.environ.get("DATABASE_URL"):
    raise RuntimeError("TEST_DATABASE_URL must differ from DATABASE_URL: the tests drop all tables.")

# Must happen before anything imports package_service, because db.py reads
# DATABASE_URL at import time. Keep the imports below this line.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import pytest  
from fastapi.testclient import TestClient  
from sqlalchemy import create_engine  
from sqlalchemy.orm import Session  

from package_service.db import Base  
from package_service.main import app  
from package_service.models import Package, Release  
from package_service.versions import parse_version  


@pytest.fixture
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(engine):
    return TestClient(app)


@pytest.fixture
def add_package(session):
    """Return a helper that inserts a package and its releases, bypassing the API."""

    def _add(name, versions=()):
        package = Package(name=name)
        for text in versions:
            v = parse_version(text)
            package.releases.append(
                Release(version=text, major=v.major, minor=v.minor, patch=v.patch)
            )
        session.add(package)
        session.commit()
        return package

    return _add