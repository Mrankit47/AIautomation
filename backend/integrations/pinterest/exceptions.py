"""Pinterest-specific exceptions."""

from __future__ import annotations

from backend.core.exceptions import IntegrationException


class PinterestAPIError(IntegrationException):
    error_code = "PINTEREST_API_ERROR"
    detail = "Pinterest API returned an error."


class PinterestRateLimitError(IntegrationException):
    status_code = 429
    error_code = "PINTEREST_RATE_LIMIT"
    detail = "Pinterest API rate limit exceeded."


class PinterestAuthError(IntegrationException):
    status_code = 401
    error_code = "PINTEREST_AUTH_ERROR"
    detail = "Pinterest authentication failed."
