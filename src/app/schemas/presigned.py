"""Schemas for presigned URL endpoints."""

from pydantic import BaseModel, Field


class PresignedUrlRequest(BaseModel):
    """Request parameters for generating a presigned upload URL.

    Used as query parameters for GET /presigned-url.
    """

    purpose: str = Field(
        ...,
        description="Purpose of the upload (e.g., 'login_voice', 'mfa_voice')",
        min_length=1,
        max_length=64,
        examples=["login_voice"],
    )
    content_type: str = Field(
        ...,
        description="MIME type of the file to upload",
        examples=["audio/wav"],
    )
    ext: str = Field(
        ...,
        description="File extension (without dot)",
        min_length=1,
        max_length=10,
        examples=["wav"],
    )


class PresignedUrlResponse(BaseModel):
    """Response containing the presigned upload URL and metadata."""

    upload_url: str = Field(
        ...,
        description="Presigned PUT URL for uploading the file",
    )
    bucket: str = Field(
        ...,
        description="S3 bucket name",
    )
    object_key: str = Field(
        ...,
        description="Object key where the file will be stored",
    )
    evidence_ref: str = Field(
        ...,
        description="Reference to use in verify requests (bucket/object_key format)",
    )
    expires_in: int = Field(
        ...,
        description="Seconds until the presigned URL expires",
    )
