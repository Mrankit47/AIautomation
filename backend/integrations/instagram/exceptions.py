"""Instagram-specific exceptions."""

from __future__ import annotations

from backend.core.exceptions import IntegrationException


class InstagramAPIError(IntegrationException):
    error_code = "INSTAGRAM_API_ERROR"
    detail = "Instagram API returned an error."


class InstagramRateLimitError(IntegrationException):
    status_code = 429
    error_code = "INSTAGRAM_RATE_LIMIT"
    detail = "Instagram API rate limit exceeded."


class InstagramAuthError(IntegrationException):
    status_code = 401
    error_code = "INSTAGRAM_AUTH_ERROR"
    detail = "Instagram authentication failed."
