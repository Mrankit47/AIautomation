"""ASGI middleware for error handling, request logging, and correlation IDs."""

from __future__ import annotations

import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from backend.core.exceptions import AppException
from backend.core.logging import (
    correlation_id_ctx,
    get_logger,
    request_id_ctx,
)

logger = get_logger(__name__)

CORRELATION_ID_HEADER = "X-Correlation-ID"
REQUEST_ID_HEADER = "X-Request-ID"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Extract or generate a correlation ID and bind it to the logging context."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Use the incoming header or generate a new UUID
        corr_id = request.headers.get(CORRELATION_ID_HEADER, str(uuid.uuid4()))
        req_id = str(uuid.uuid4())

        # Bind to context variables so structlog picks them up
        correlation_id_ctx.set(corr_id)
        request_id_ctx.set(req_id)

        response = await call_next(request)

        # Echo IDs back in response headers
        response.headers[CORRELATION_ID_HEADER] = corr_id
        response.headers[REQUEST_ID_HEADER] = req_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status code, and duration."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        logger.info(
            "request_completed",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else None,
        )
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Catch exceptions and return structured JSON error responses."""

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        try:
            return await call_next(request)
        except AppException as exc:
            logger.warning(
                "app_exception",
                error_code=exc.error_code,
                detail=exc.detail,
                status_code=exc.status_code,
                context=exc.context,
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    **exc.to_dict(),
                    "correlation_id": correlation_id_ctx.get(),
                },
            )
        except Exception as exc:
            logger.exception(
                "unhandled_exception",
                error_type=type(exc).__name__,
                detail=str(exc),
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error_code": "INTERNAL_ERROR",
                    "detail": "An unexpected internal error occurred.",
                    "correlation_id": correlation_id_ctx.get(),
                },
            )
