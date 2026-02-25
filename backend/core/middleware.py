import uuid
from contextvars import ContextVar
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.logging_config import get_correlation_filter

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation IDs to all requests for distributed tracing.

    The correlation ID is:
    1. Extracted from X-Request-ID header if present
    2. Generated as a new UUID if not present
    3. Added to response headers as X-Request-ID
    4. Available via correlation_id_var context variable
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        correlation_id = request.headers.get("X-Request-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        correlation_id_var.set(correlation_id)
        get_correlation_filter().set_correlation_id(correlation_id)

        response = await call_next(request)

        response.headers["X-Request-ID"] = correlation_id

        return response


def get_correlation_id() -> str | None:
    """Get the current correlation ID from context."""
    return correlation_id_var.get()
