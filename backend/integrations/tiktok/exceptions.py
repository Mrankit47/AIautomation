"""TikTok-specific exceptions."""

from __future__ import annotations

from backend.core.exceptions import IntegrationException


class TikTokAPIError(IntegrationException):
    error_code = "TIKTOK_API_ERROR"
    detail = "TikTok API returned an error."


class TikTokRateLimitError(IntegrationException):
    status_code = 429
    error_code = "TIKTOK_RATE_LIMIT"
    detail = "TikTok API rate limit exceeded."


class TikTokAuthError(IntegrationException):
    status_code = 401
    error_code = "TIKTOK_AUTH_ERROR"
    detail = "TikTok authentication failed."
