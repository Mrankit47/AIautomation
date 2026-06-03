"""YouTube-specific exceptions."""

from __future__ import annotations

from backend.core.exceptions import IntegrationException


class YouTubeAPIError(IntegrationException):
    error_code = "YOUTUBE_API_ERROR"
    detail = "YouTube API returned an error."


class YouTubeQuotaExceededError(IntegrationException):
    status_code = 429
    error_code = "YOUTUBE_QUOTA_EXCEEDED"
    detail = "YouTube API quota exceeded."


class YouTubeAuthError(IntegrationException):
    status_code = 401
    error_code = "YOUTUBE_AUTH_ERROR"
    detail = "YouTube authentication failed."
