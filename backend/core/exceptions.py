"""Application-wide exception hierarchy.

Every custom exception carries a structured payload so the error-handling
middleware can return consistent JSON responses with correlation IDs.
"""

from __future__ import annotations

from typing import Any


class AppException(Exception):
    """Base exception for all application errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    detail: str = "An unexpected error occurred."

    def __init__(
        self,
        detail: str | None = None,
        *,
        error_code: str | None = None,
        status_code: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        self.detail = detail or self.__class__.detail
        self.error_code = error_code or self.__class__.error_code
        self.status_code = status_code or self.__class__.status_code
        self.context = context or {}
        super().__init__(self.detail)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "error_code": self.error_code,
            "detail": self.detail,
        }
        if self.context:
            payload["context"] = self.context
        return payload


class NotFoundException(AppException):
    status_code = 404
    error_code = "NOT_FOUND"
    detail = "The requested resource was not found."


class ValidationException(AppException):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    detail = "The request payload failed validation."


class AuthenticationException(AppException):
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"
    detail = "Authentication credentials are missing or invalid."


class AuthorizationException(AppException):
    status_code = 403
    error_code = "AUTHORIZATION_ERROR"
    detail = "You do not have permission to perform this action."


class StorageException(AppException):
    status_code = 500
    error_code = "STORAGE_ERROR"
    detail = "A file storage operation failed."


class AIProviderException(AppException):
    status_code = 502
    error_code = "AI_PROVIDER_ERROR"
    detail = "The AI provider returned an error."


class WorkflowException(AppException):
    status_code = 500
    error_code = "WORKFLOW_ERROR"
    detail = "The workflow execution encountered an error."


class IntegrationException(AppException):
    status_code = 502
    error_code = "INTEGRATION_ERROR"
    detail = "An external integration returned an error."


class RateLimitException(AppException):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    detail = "Rate limit exceeded. Please try again later."


class TaskException(AppException):
    status_code = 500
    error_code = "TASK_ERROR"
    detail = "A background task encountered an error."
