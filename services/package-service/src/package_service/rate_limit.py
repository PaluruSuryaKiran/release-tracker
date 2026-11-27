"""Per-client rate limiting"""

import math
import os
import time

from fastapi import Request
from limits import parse, storage, strategies

from package_service.problems import ProblemError

RATE = parse(f"{int(os.environ.get('RATE_LIMIT_PER_MINUTE', '60'))}/minute")

_storage = storage.storage_from_string(os.environ.get("RATE_LIMIT_STORAGE", "memory://"))
_limiter = strategies.MovingWindowRateLimiter(_storage)


def rate_limit(request: Request) -> None:
    """Reject the request with 429 if this client has used up its requests."""
    client = request.client.host if request.client else "unknown"
    if not _limiter.hit(RATE, client):
        reset_at = _limiter.get_window_stats(RATE, client).reset_time
        seconds = max(1, math.ceil(reset_at - time.time()))
        raise ProblemError(
            429, "rate-limited", "Too many requests",
            f"Too many requests from this client. Try again in {seconds} seconds.",
            headers={"Retry-After": str(seconds)},
        )


def reset() -> None:
    """Forget every client's count. Used by the tests."""
    _storage.reset()