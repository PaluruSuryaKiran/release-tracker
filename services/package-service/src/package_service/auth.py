import os
import secrets
from typing import Annotated

from dotenv import load_dotenv
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from package_service.problems import ProblemError
from package_service.settings import secret

load_dotenv()

API_KEY = secret("API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY is not set. Copy .env.example to .env and fill it in.")

# auto_error=False: return None instead of FastAPI's own 403
_bearer = HTTPBearer(
    auto_error=False,
    description="The service's API key, sent as `Authorization: Bearer <key>`.",
)


def require_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> None:
    """Allow the request only if it carries the right API key."""
    if credentials is None or not secrets.compare_digest(
        credentials.credentials.encode(), API_KEY.encode()
    ):
        raise ProblemError(
            401, "unauthorized", "Unauthorized",
            "A valid API key is required. Send it as 'Authorization: Bearer <key>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )