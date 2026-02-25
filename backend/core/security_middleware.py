"""
Security middleware for Network Guardian AI.

This module provides:
- Security headers middleware
- HTTPS enforcement
- CORS security enhancements

Integration in backend/main.py:
    from backend.core.security_middleware import SecurityHeadersMiddleware, HTTPSRedirectMiddleware

    if settings.ENABLE_SECURITY_HEADERS:
        app.add_middleware(SecurityHeadersMiddleware)

    if settings.ENABLE_HTTPS_REDIRECT:
        app.add_middleware(HTTPSRedirectMiddleware, enabled=True)
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable

from backend.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Security headers include:
    - Strict-Transport-Security (HSTS) - Forces HTTPS
    - X-Content-Type-Options - Prevents MIME sniffing
    - X-Frame-Options - Prevents clickjacking
    - Content-Security-Policy - Restricts content sources
    - Referrer-Policy - Controls referrer information
    - Permissions-Policy - Restricts browser features

    Only applies headers if settings.ENABLE_SECURITY_HEADERS is True.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        if not settings.ENABLE_SECURITY_HEADERS:
            return response

        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        csp = "default-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com; object-src 'none'; style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com; connect-src 'self' https://cdn.tailwindcss.com"
        response.headers["Content-Security-Policy"] = csp

        response.headers["X-XSS-Protection"] = "1; mode=block"

        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )

        return response


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """
    Middleware to redirect HTTP requests to HTTPS.

    Disabled by default in development mode.
    Enable via settings.ENABLE_HTTPS_REDIRECT in production.
    """

    def __init__(self, app, enabled: bool = False):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if self.enabled and request.url.scheme == "http":
            https_url = request.url.replace(scheme="https")
            from fastapi.responses import RedirectResponse

            return RedirectResponse(url=str(https_url), status_code=301)

        return await call_next(request)


def get_security_middleware(app, enable_https_redirect: bool = False):
    """
    Add security middleware to the FastAPI app.

    Args:
        app: FastAPI application instance
        enable_https_redirect: Whether to enable HTTPS redirection

    Returns:
        The app with security middleware added

    Usage:
        from backend.core.security_middleware import get_security_middleware
        app = get_security_middleware(app, enable_https_redirect=settings.ENABLE_HTTPS_REDIRECT)
    """
    if settings.ENABLE_SECURITY_HEADERS:
        app.add_middleware(SecurityHeadersMiddleware)

    if enable_https_redirect:
        app.add_middleware(HTTPSRedirectMiddleware, enabled=True)

    return app
