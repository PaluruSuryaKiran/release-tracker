import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv() 

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Copy .env.example to .env and fill it in."
    )

DB_CONNECT_TIMEOUT = int(os.environ.get("DB_CONNECT_TIMEOUT", "5"))
DB_STATEMENT_TIMEOUT_MS = int(os.environ.get("DB_STATEMENT_TIMEOUT_MS", "5000"))
DB_POOL_TIMEOUT = int(os.environ.get("DB_POOL_TIMEOUT", "5"))

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_timeout=DB_POOL_TIMEOUT,
    connect_args = {
        "connect_timeout": DB_CONNECT_TIMEOUT,
        "options": f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}",
    },
)
session_local = sessionmaker(bind=engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

def get_session():
    session = session_local()
    try:
        yield session
    finally:
        session.close()