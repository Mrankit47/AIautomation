"""Cloudinary-specific Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel


class CloudinaryUploadResponse(BaseModel):
    """Response from a Cloudinary upload."""

    public_id: str
    url: str
    secure_url: str
    format: str
    bytes: int
    width: int | None = None
    height: int | None = None
    resource_type: str = "image"


class CloudinaryTransformation(BaseModel):
    """Cloudinary transformation parameters."""

    width: int | None = None
    height: int | None = None
    crop: str | None = None
    quality: str | None = None
    format: str | None = None
    effect: str | None = None
