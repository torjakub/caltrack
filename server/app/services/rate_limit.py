"""Minimal in-memory sliding-window rate limiter.

Deliberately not Redis/backed — this server targets a single-process
household deployment where brute-force throttling on the auth endpoints is
the only requirement. Counters are keyed by (bucket, client IP).
"""

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

_MAX_ATTEMPTS = 10
_WINDOW_SECONDS = 300

_attempts: dict[tuple[str, str], deque[float]] = defaultdict(deque)


def enforce_rate_limit(request: Request, *, bucket: str) -> None:
    client_ip = request.client.host if request.client else "unknown"
    key = (bucket, client_ip)
    hits = _attempts[key]
    now = time.monotonic()

    while hits and now - hits[0] > _WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts, try again in a few minutes",
        )
    hits.append(now)
