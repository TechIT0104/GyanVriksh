"""Security hardening: response headers, login brute-force rate limiting, and
weak-secret detection. Kept intentionally dependency-free (in-memory) so the
demo runs anywhere; a production deployment would back the limiter with Redis."""
import logging
import time
from collections import defaultdict

from fastapi import HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("gyanvriksh.security")

# Hardening headers applied to every response.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-XSS-Protection": "1; mode=block",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=(self)",
    # HSTS is a no-op over plain HTTP but protects any HTTPS deployment.
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Cache-Control": "no-store",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        for k, v in SECURITY_HEADERS.items():
            response.headers.setdefault(k, v)
        return response


# ---- login brute-force protection (per client IP, sliding window) ----
_attempts: dict[str, list[float]] = defaultdict(list)
_WINDOW_SEC = 300      # 5 minutes
_MAX_ATTEMPTS = 10     # per window per IP


def check_login_rate(ip: str) -> None:
    now = time.time()
    recent = [t for t in _attempts[ip] if now - t < _WINDOW_SEC]
    _attempts[ip] = recent
    if len(recent) >= _MAX_ATTEMPTS:
        logger.warning("Login rate limit hit for %s", ip)
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Too many login attempts. Please wait a few minutes.")
    recent.append(now)


def is_weak_secret(secret: str) -> bool:
    s = (secret or "")
    return len(s) < 32 or "change" in s.lower() or "replace" in s.lower()


def warn_if_insecure(settings) -> None:
    """Log loud warnings for demo-grade secrets so they aren't shipped to prod."""
    if is_weak_secret(settings.jwt_secret):
        logger.warning("JWT_SECRET is weak/default — set a strong 32+ char secret before any real deployment.")
    if "CHANGE" in (settings.neo4j_password or "") or settings.minio_secret_key == "minioadmin":
        logger.warning("Default database/object-store credentials in use — change them outside local demo.")
