"""Schemas for verification endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class VerificationRequest(BaseModel):
    """Request body for POST /verify endpoint."""

    evidence_ref: str = Field(
        ...,
        description=(
            "Reference to the uploaded media. "
            "Formats: 's3://bucket/key', 'bucket/key', or just 'key' (uses default bucket)"
        ),
        min_length=1,
        examples=["media-bucket/uploads/login_voice/20240101_120000_abc123.wav"],
    )
    profile: str = Field(
        ...,
        description=(
            "Verification profile determining which processor to use. "
            "Format: 'type.category.variant' (e.g., 'voice.login.default')"
        ),
        min_length=3,
        examples=["voice.login.default"],
    )
    subject_id: str = Field(
        ...,
        description="Identifier for the subject being verified (e.g., user ID)",
        min_length=1,
        examples=["user_123"],
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional additional context for the verification processor",
    )


class VerificationResponse(BaseModel):
    """Response from POST /verify endpoint."""

    valid: bool = Field(
        ...,
        description="Whether the verification passed",
    )
    confidence: float = Field(
        ...,
        description="Confidence score between 0.0 and 1.0",
        ge=0.0,
        le=1.0,
    )
    reason: str = Field(
        ...,
        description="Human-readable explanation of the result",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional processor-specific information",
    )


class ErrorResponse(BaseModel):
    """Standard error response format."""

    detail: str = Field(
        ...,
        description="Human-readable error message",
    )
    code: str = Field(
        ...,
        description="Machine-readable error code",
    )
