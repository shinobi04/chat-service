import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from app.core.config import settings

logger = logging.getLogger(__name__)

# Parse the comma-separated whitelist once at startup
_allowed_ips: set[str] = set()
if settings.ALLOWED_IPS.strip():
    _allowed_ips = {ip.strip() for ip in settings.ALLOWED_IPS.split(",") if ip.strip()}
    logger.info("IP whitelist enabled — allowed IPs: %s", _allowed_ips)
else:
    logger.warning("IP whitelist is DISABLED (ALLOWED_IPS is empty). All IPs can access the API.")

# Paths that bypass the IP check (health probes, docs)
_exempt_paths = {"/health", "/docs", "/openapi.json", "/redoc"}


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """Rejects requests from IPs not in the ALLOWED_IPS whitelist."""

    async def dispatch(self, request: Request, call_next):
        # If no whitelist is configured, allow everything (dev mode)
        if not _allowed_ips:
            return await call_next(request)

        # Always let health checks through for load balancers / uptime monitors
        if request.url.path in _exempt_paths:
            return await call_next(request)

        client_ip = request.client.host if request.client else None

        if client_ip not in _allowed_ips:
            logger.warning("Blocked request from unauthorized IP: %s → %s %s", client_ip, request.method, request.url.path)
            return JSONResponse(
                status_code=403,
                content={"detail": "Forbidden: your IP is not whitelisted."},
            )

        return await call_next(request)
