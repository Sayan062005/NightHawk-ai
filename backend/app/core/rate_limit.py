"""Small per-process rate limiter for authentication endpoints.

For multi-worker or multi-instance deployments, enforce the same limits at the
reverse proxy/API gateway or replace this store with Redis-backed buckets.
"""

from __future__ import annotations

from collections import deque
from time import monotonic

from fastapi import HTTPException, Request, status

_BUCKETS: dict[str, deque[float]] = {}


def reset_rate_limits() -> None:
    """Clear in-memory buckets; intended for deterministic automated tests."""
    _BUCKETS.clear()


async def enforce_rate_limit(
    request: Request,
    action: str,
    *,
    limit: int,
    window_seconds: int,
) -> None:
    """Limit attempts by client IP and endpoint without trusting forwarded headers."""
    host = request.client.host if request.client else "unknown"
    key = f"{action}:{host}"
    now = monotonic()
    bucket = _BUCKETS.setdefault(key, deque())

    while bucket and now - bucket[0] >= window_seconds:
        bucket.popleft()

    if len(bucket) >= limit:
        retry_after = max(1, int(window_seconds - (now - bucket[0])))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    bucket.append(now)

    # Bound memory use if a server receives many unique source addresses.
    if len(_BUCKETS) > 10000:
        expired_before = now - window_seconds
        stale = [name for name, entries in _BUCKETS.items() if not entries or entries[-1] < expired_before]
        for name in stale[:5000]:
            _BUCKETS.pop(name, None)
