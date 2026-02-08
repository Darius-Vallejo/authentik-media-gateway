"""S3 client configuration and factory."""

from functools import lru_cache
from typing import TYPE_CHECKING

import boto3
from botocore.config import Config

from app.config import get_settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


@lru_cache
def get_s3_client() -> "S3Client":
    """Get a cached S3 client instance.

    The client is configured with the settings from environment variables
    and includes timeout configuration for reliability.

    Returns:
        S3Client: A configured boto3 S3 client.
    """
    settings = get_settings()

    config = Config(
        connect_timeout=settings.s3_timeout_seconds,
        read_timeout=settings.s3_timeout_seconds,
        retries={"max_attempts": 3, "mode": "adaptive"},
        signature_version="s3v4",
    )

    client: S3Client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        config=config,
    )

    return client


def download_object(bucket: str, key: str, max_bytes: int) -> bytes:
    """Download an object from S3 with size limit enforcement.

    Args:
        bucket: The S3 bucket name.
        key: The object key.
        max_bytes: Maximum allowed size in bytes.

    Returns:
        The object contents as bytes.

    Raises:
        ValueError: If the object exceeds max_bytes.
        botocore.exceptions.ClientError: If the S3 operation fails.
    """
    client = get_s3_client()

    # First, check the object size via HEAD request
    head_response = client.head_object(Bucket=bucket, Key=key)
    content_length = head_response.get("ContentLength", 0)

    if content_length > max_bytes:
        raise ValueError(
            f"Object size ({content_length} bytes) exceeds maximum allowed "
            f"({max_bytes} bytes)"
        )

    # Download the object
    response = client.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read()

    # Double-check size after download (in case of streaming issues)
    if len(body) > max_bytes:
        raise ValueError(
            f"Downloaded size ({len(body)} bytes) exceeds maximum allowed "
            f"({max_bytes} bytes)"
        )

    return body


def upload_object(bucket: str, key: str, body: bytes, content_type: str) -> None:
    """Upload an object to S3.

    Args:
        bucket: The S3 bucket name.
        key: The object key.
        body: The object content as bytes.
        content_type: The MIME type of the object (e.g. 'audio/wav').

    Raises:
        botocore.exceptions.ClientError: If the S3 operation fails.
    """
    client = get_s3_client()
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=body,
        ContentType=content_type,
    )
