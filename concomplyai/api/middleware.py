"""Production middleware for authentication, rate limiting, and error handling."""

from __future__ import annotations

import json
import logging
import time
import uuid
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from concomplyai.config.settings import get_settings

logger = logging.getLogger(__name__)

_AUTH_SKIP_PATHS = frozenset({"/health", "/docs", "/openapi.json"})


class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Validates ``Authorization: Bearer <token>`` against the configured auth token.

    Requests to health-check, docs, and OpenAPI schema paths are exempt.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if request.url.path in _AUTH_SKIP_PATHS:
            return await call_next(request)

        settings = get_settings()
        expected = settings.auth_token.get_secret_value()

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer ") or auth_header[7:] != expected:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing authentication token"},
            )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """In-memory per-IP rate limiter using a sliding window of one minute."""

    def __init__(self, app: object) -> None:  # noqa: ANN001
        super().__init__(app)  # type: ignore[arg-type]
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._last_cleanup: float = time.monotonic()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        settings = get_settings()
        limit = settings.rate_limit_per_minute

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()

        self._maybe_cleanup(now)

        window = self._requests[client_ip]
        cutoff = now - 60.0
        self._requests[client_ip] = [ts for ts in window if ts > cutoff]
        window = self._requests[client_ip]

        if len(window) >= limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
            )

        window.append(now)
        return await call_next(request)

    def _maybe_cleanup(self, now: float) -> None:
        """Purge stale entries every 60 seconds to prevent memory growth."""
        if now - self._last_cleanup < 60.0:
            return
        self._last_cleanup = now
        cutoff = now - 60.0
        stale_keys = [
            ip for ip, timestamps in self._requests.items()
            if not timestamps or timestamps[-1] <= cutoff
        ]
        for key in stale_keys:
            del self._requests[key]


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Catches unhandled exceptions and returns a structured JSON 500 response."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = str(uuid.uuid4())
        try:
            return await call_next(request)
        except Exception:
            logger.exception(
                '{"action":"unhandled_exception","request_id":"%s","path":"%s","method":"%s"}',
                request_id,
                request.url.path,
                request.method,
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "request_id": request_id,
                },
            )
