"""Presigned URL endpoint for media uploads."""

import logging

from fastapi import APIRouter, HTTPException, Query

from app.schemas.presigned import PresignedUrlResponse
from app.storage.presigned import generate_presigned_upload_url

logger = logging.getLogger(__name__)

router = APIRouter(tags=["storage"])


@router.get("/presigned-url", response_model=PresignedUrlResponse)
async def get_presigned_url(
    purpose: str = Query(
        ...,
        description="Purpose of the upload (e.g., 'login_voice')",
        min_length=1,
        max_length=64,
    ),
    content_type: str = Query(
        ...,
        description="MIME type of the file (e.g., 'audio/wav')",
    ),
    ext: str = Query(
        ...,
        description="File extension without dot (e.g., 'wav')",
        min_length=1,
        max_length=10,
    ),
) -> PresignedUrlResponse:
    """Generate a presigned PUT URL for uploading media to S3.

    The returned URL can be used to upload a file directly to S3/MinIO
    without exposing credentials. The upload must be completed before
    the URL expires (default: 5 minutes).

    Args:
        purpose: Descriptive purpose for organizing uploads.
        content_type: MIME type that must match the upload.
        ext: File extension for the object key.

    Returns:
        PresignedUrlResponse with upload URL and metadata.

    Raises:
        HTTPException 400: If content_type is not allowed.
    """
    try:
        result = generate_presigned_upload_url(
            purpose=purpose,
            content_type=content_type,
            extension=ext,
        )

        logger.info(
            f"Generated presigned URL for {purpose}",
            extra={
                "purpose": purpose,
                "content_type": content_type,
                "object_key": result.object_key,
            },
        )

        return PresignedUrlResponse(
            upload_url=result.upload_url,
            bucket=result.bucket,
            object_key=result.object_key,
            evidence_ref=result.evidence_ref,
            expires_in=result.expires_in,
        )

    except ValueError as e:
        logger.warning(f"Presigned URL request rejected: {e}")
        raise HTTPException(
            status_code=400,
            detail={
                "detail": str(e),
                "code": "INVALID_CONTENT_TYPE",
            },
        ) from e
