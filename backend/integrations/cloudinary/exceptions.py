"""Cloudinary-specific exceptions."""

from __future__ import annotations

from backend.core.exceptions import IntegrationException


class CloudinaryAPIError(IntegrationException):
    error_code = "CLOUDINARY_API_ERROR"
    detail = "Cloudinary API returned an error."


class CloudinaryUploadError(IntegrationException):
    error_code = "CLOUDINARY_UPLOAD_ERROR"
    detail = "Cloudinary file upload failed."
