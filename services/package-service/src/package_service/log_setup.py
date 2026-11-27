"""Request IDs and structured JSON logs."""

import json
import logging
import os
import re
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone

from fastapi import FastAPI, Request

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

access_logger = logging.getLogger("package_service.access")

_STANDARD_FIELDS = set(vars(logging.makeLogRecord({}))) | {"message", "color_message"}


class JsonFormatter(logging.Formatter):
    """Format each log record as one line of JSON."""

    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_var.get()
        if request_id:
            entry["request_id"] = request_id
        for key, value in vars(record).items():
            if key not in _STANDARD_FIELDS and key not in entry:
                entry[key] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


def configure_logging() -> None:
    """Send every log, ours and uvicorn's, to stdout as JSON."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())

    # removing uvicorn's handlers and letting our root logger handle.
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True

    logging.getLogger("uvicorn.access").disabled = True


def add_request_id_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_id_and_access_log(request: Request, call_next):
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        if _VALID_REQUEST_ID.fullmatch(incoming):
            request_id = incoming
        else:
            request_id = uuid.uuid4().hex
        request_id_var.set(request_id)

        start = time.perf_counter()
        status_code = 500  # stays 500 if the app raises
        try:
            response = await call_next(request)
            status_code = response.status_code
        finally:
            access_logger.info(
                "%s %s %s",
                request.method,
                request.url.path,
                status_code,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                },
            )
        response.headers[REQUEST_ID_HEADER] = request_id
        return response