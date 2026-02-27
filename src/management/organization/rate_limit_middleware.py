"""Organization request-per-minute middleware."""

from src.management.organization.factories import getOrgService

import re
import time
import asyncio
from collections import deque, defaultdict
from collections.abc import Callable

from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware


_ORG_PATH_RE = re.compile(r"^/v1/organizations/([^/]+)")
_WINDOW_SECONDS = 60.0
_MAX_TRACKED_ORGS = 10_000
_CLEANUP_EVERY_N_REQUESTS = 256


class OrgRateLimitMiddleware(BaseHTTPMiddleware):
    """Apply organization-level RPM limit for management org endpoints."""

    def __init__(self, app):
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._last_seen: dict[str, float] = {}
        self._request_count = 0

    def _cleanup_stale_orgs(self, now: float) -> None:
        stale_cutoff = now - _WINDOW_SECONDS
        for tracked_org_id, last_seen in list(self._last_seen.items()):
            if last_seen < stale_cutoff:
                self._last_seen.pop(tracked_org_id, None)
                self._hits.pop(tracked_org_id, None)
                self._locks.pop(tracked_org_id, None)

        if len(self._last_seen) <= _MAX_TRACKED_ORGS:
            return

        # Guard against unbounded growth when many unique org IDs are probed.
        overflow = len(self._last_seen) - _MAX_TRACKED_ORGS
        for tracked_org_id, _ in sorted(
            self._last_seen.items(),
            key=lambda item: item[1],
        )[:overflow]:
            self._last_seen.pop(tracked_org_id, None)
            self._hits.pop(tracked_org_id, None)
            self._locks.pop(tracked_org_id, None)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        match = _ORG_PATH_RE.match(request.url.path)
        if not match:
            return await call_next(request)

        org_id = match.group(1)
        limit = await getOrgService().get_limit(org_id)
        if limit is None or limit <= 0:
            return await call_next(request)

        now = time.monotonic()
        self._last_seen[org_id] = now
        self._request_count += 1
        if self._request_count % _CLEANUP_EVERY_N_REQUESTS == 0:
            self._cleanup_stale_orgs(now)

        lock = self._locks[org_id]
        async with lock:
            q = self._hits[org_id]
            while q and now - q[0] >= _WINDOW_SECONDS:
                q.popleft()
            if len(q) >= limit:
                retry_after = int(max(1, _WINDOW_SECONDS - (now - q[0])))
                return JSONResponse(
                    status_code=429,
                    content={
                        "status": 429,
                        "title": "Rate Limit Exceeded",
                        "code": "org_rate_limit_exceeded",
                        "detail": (
                            "Organization rate limit exceeded. "
                            f"Try again in {retry_after}s."
                        ),
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            q.append(now)

        return await call_next(request)
