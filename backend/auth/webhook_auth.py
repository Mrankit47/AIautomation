"""Webhook API key authentication for the ingestion endpoint.

Verifies the X-API-KEY header against the configured WEBHOOK_API_KEY.
Uses constant-time comparison to prevent timing attacks.
"""

from __future__ import annotations

import hmac

from fastapi import Header

from backend.config.settings import get_settings
from backend.core.exceptions import AuthenticationException


async def verify_webhook_api_key(
    x_api_key: str = Header(..., alias="X-API-KEY"),
) -> str:
    """Verify the webhook API key from X-API-KEY header.

    Args:
        x_api_key: The API key from the request header.

    Returns:
        The verified API key string.

    Raises:
        AuthenticationException: If the API key is missing or invalid.
    """
    settings = get_settings()

    if not settings.webhook_api_key:
        raise AuthenticationException(
            detail="Webhook API key is not configured on the server.",
            error_code="WEBHOOK_KEY_NOT_CONFIGURED",
        )

    if not hmac.compare_digest(x_api_key, settings.webhook_api_key):
        raise AuthenticationException(
            detail="Invalid API key.",
            error_code="INVALID_API_KEY",
        )

    return x_api_key
