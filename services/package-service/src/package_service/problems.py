# Error Formatting and Handling for the Package Service API

import logging

from http import HTTPStatus
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, TimeoutError as PoolTimeoutError
from starlette.exceptions import HTTPException as StarletteHTTPException

from package_service.logging import REQUEST_ID_HEADER, request_id_var


logger = logging.getLogger(__name__)

PROBLEM_TYPE_BASE = "https://github.com/PaluruSuryaKiran/release-tracker#"
PROBLEM_CONTENT_TYPE = "application/problem+json"


class ProblemError(Exception):

    def __init__(self, status: int, slug: str, title: str, detail: str):
        super().__init__(detail)
        self.status = status
        self.slug = slug
        self.title = title
        self.detail = detail


def problem_response(request: Request, status: int, title: str, detail: str,
                      type_: str = "about:blank", headers: dict | None = None, **extra,) -> JSONResponse:
    body = {
        "type": type_,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": request.url.path,
        **extra,
    }
    return JSONResponse(
        body, status_code=status, headers=headers, media_type=PROBLEM_CONTENT_TYPE
    )


async def handle_problem_error(request: Request, exc: ProblemError) -> JSONResponse:
    return problem_response(
        request, exc.status, exc.title, exc.detail, PROBLEM_TYPE_BASE + exc.slug
    )


async def handle_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    title = HTTPStatus(exc.status_code).phrase
    detail = exc.detail if isinstance(exc.detail, str) else title
    return problem_response(
        request, exc.status_code, title, detail, headers=getattr(exc, "headers", None)
    )


async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"][1:]) or error["loc"][0],
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return problem_response(
        request,
        422,
        "Invalid request",
        "The request is invalid. See errors for each field.",
        PROBLEM_TYPE_BASE + "invalid-request",
        errors=errors,
    )


async def handle_database_unavailable(request: Request, exc: Exception) -> JSONResponse:
    reason = getattr(exc, "orig", None) or exc
    logger.warning(
        f"Database unavailable on {request.method} {request.url.path}: {reason}"
    )
    return problem_response(
        request,
        503,
        "Database unavailable",
        "The service cannot reach its database right now. Try again shortly.",
        type_=PROBLEM_TYPE_BASE + "database-unavailable",
        headers={"Retry-After": "5"},
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    request_id = request_id_var.get()
    return problem_response(
        request,
        500, 
        "Internal Server Error", 
        "An unexpected error occurred.",
        headers={REQUEST_ID_HEADER: request_id} if request_id else None,
    )


def register_problem_handlers(app) -> None:
    app.add_exception_handler(ProblemError, handle_problem_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(OperationalError, handle_database_unavailable)
    app.add_exception_handler(PoolTimeoutError, handle_database_unavailable)
    app.add_exception_handler(Exception, handle_unexpected_error)