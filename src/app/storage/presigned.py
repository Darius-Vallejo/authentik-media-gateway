"""Presigned URL generation for S3 uploads."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.config import get_settings
from app.storage.s3_client import get_s3_client


@dataclass
class PresignedUploadResult:
    """Result of generating a presigned upload URL."""

    upload_url: str
    bucket: str
    object_key: str
    evidence_ref: str
    expires_in: int


def generate_presigned_upload_url(
    purpose: str,
    content_type: str,
    extension: str,
) -> PresignedUploadResult:
    """Generate a presigned PUT URL for uploading media to S3.

    The object key is generated using a UUID and timestamp to ensure uniqueness
    and prevent collisions.

    Args:
        purpose: A descriptive purpose for the upload (e.g., 'login_voice').
        content_type: The MIME type of the file to be uploaded.
        extension: The file extension (without the dot).

    Returns:
        PresignedUploadResult containing the upload URL and metadata.

    Raises:
        ValueError: If the content_type is not in the allowed list.
    """
    settings = get_settings()

    # Validate content type
    if content_type not in settings.allowed_content_types:
        raise ValueError(
            f"Content type '{content_type}' is not allowed. "
            f"Allowed types: {settings.allowed_content_types}"
        )

    # Generate a unique object key
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    unique_id = uuid.uuid4().hex[:12]
    sanitized_purpose = "".join(c if c.isalnum() or c == "_" else "_" for c in purpose)
    clean_extension = extension.lstrip(".")

    object_key = f"{settings.s3_key_prefix}{sanitized_purpose}/{timestamp}_{unique_id}.{clean_extension}"

    # Generate presigned URL
    client = get_s3_client()
    upload_url = client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.s3_bucket,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=settings.s3_presigned_ttl_seconds,
    )

    # Create evidence reference (can be used in verify requests)
    evidence_ref = f"{settings.s3_bucket}/{object_key}"

    return PresignedUploadResult(
        upload_url=upload_url,
        bucket=settings.s3_bucket,
        object_key=object_key,
        evidence_ref=evidence_ref,
        expires_in=settings.s3_presigned_ttl_seconds,
    )
