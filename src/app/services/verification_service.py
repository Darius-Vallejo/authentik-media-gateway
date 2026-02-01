"""Verification service orchestrating the Claim Check flow."""

import logging
import re
from dataclasses import dataclass
from typing import Any

from app.config import get_settings
from app.processors.base import VerificationResult
from app.processors.registry import get_processor_registry
from app.storage.s3_client import download_object

logger = logging.getLogger(__name__)


class InvalidEvidenceRefError(Exception):
    """Raised when the evidence reference is invalid or unsafe."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class MediaTooLargeError(Exception):
    """Raised when the media file exceeds the size limit."""

    def __init__(self, size: int, max_size: int) -> None:
        self.size = size
        self.max_size = max_size
        super().__init__(
            f"Media file size ({size} bytes) exceeds maximum allowed ({max_size} bytes)"
        )


@dataclass
class ParsedEvidenceRef:
    """Parsed components of an evidence reference."""

    bucket: str
    key: str


class VerificationService:
    """Service for processing verification requests.

    Implements the Claim Check pattern:
    1. Parse the evidence reference to extract bucket/key
    2. Validate the object key is within allowed prefix
    3. Download the object from S3
    4. Route to the appropriate processor based on profile
    5. Return the verification result
    """

    def __init__(self) -> None:
        """Initialize the verification service."""
        self.settings = get_settings()
        self.registry = get_processor_registry()

    def parse_evidence_ref(self, evidence_ref: str) -> ParsedEvidenceRef:
        """Parse an evidence reference into bucket and key components.

        Supports multiple formats:
        - s3://bucket/path/to/object
        - bucket/path/to/object
        - path/to/object (uses default bucket from settings)

        Args:
            evidence_ref: The evidence reference string.

        Returns:
            ParsedEvidenceRef with bucket and key.

        Raises:
            InvalidEvidenceRefError: If the reference is malformed or unsafe.
        """
        if not evidence_ref or not evidence_ref.strip():
            raise InvalidEvidenceRefError("Evidence reference cannot be empty")

        evidence_ref = evidence_ref.strip()

        # Handle s3:// URI format
        s3_uri_match = re.match(r"^s3://([^/]+)/(.+)$", evidence_ref)
        if s3_uri_match:
            bucket = s3_uri_match.group(1)
            key = s3_uri_match.group(2)
        else:
            # Handle bucket/key or just key format
            parts = evidence_ref.split("/", 1)
            if len(parts) == 1:
                # Just the key, use default bucket
                bucket = self.settings.s3_bucket
                key = parts[0]
            else:
                # Could be bucket/key or prefix/key
                # Heuristic: if first part looks like a bucket name (no dots in path structure)
                # and second part starts with the configured prefix, treat first as bucket
                first_part, rest = parts
                if rest.startswith(self.settings.s3_key_prefix):
                    bucket = first_part
                    key = rest
                elif first_part == self.settings.s3_bucket:
                    bucket = first_part
                    key = rest
                else:
                    # Treat entire string as key with default bucket
                    bucket = self.settings.s3_bucket
                    key = evidence_ref

        # Validate the key is within allowed prefix
        self._validate_key(key)

        return ParsedEvidenceRef(bucket=bucket, key=key)

    def _validate_key(self, key: str) -> None:
        """Validate that the object key is within the allowed prefix.

        Args:
            key: The S3 object key.

        Raises:
            InvalidEvidenceRefError: If the key is outside the allowed prefix.
        """
        required_prefix = self.settings.s3_key_prefix

        if not key.startswith(required_prefix):
            raise InvalidEvidenceRefError(
                f"Object key must start with '{required_prefix}'. "
                f"Got: '{key}'. This is a security restriction."
            )

        # Prevent path traversal
        if ".." in key:
            raise InvalidEvidenceRefError(
                "Object key contains path traversal sequence '..'"
            )

        # Prevent absolute paths
        if key.startswith("/"):
            raise InvalidEvidenceRefError("Object key cannot start with '/'")

    async def verify(
        self,
        evidence_ref: str,
        profile: str,
        subject_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> VerificationResult:
        """Execute the verification flow.

        Args:
            evidence_ref: Reference to the uploaded media.
            profile: Verification profile for processor routing.
            subject_id: Identifier for the subject being verified.
            metadata: Optional additional context.

        Returns:
            VerificationResult with the outcome.

        Raises:
            InvalidEvidenceRefError: If the evidence reference is invalid.
            InvalidProfileError: If no processor matches the profile.
            MediaTooLargeError: If the file exceeds size limits.
            NotImplementedError: If the processor is a stub.
        """
        # Parse and validate evidence reference
        parsed = self.parse_evidence_ref(evidence_ref)

        logger.info(
            "Processing verification request",
            extra={
                "bucket": parsed.bucket,
                "key": parsed.key,
                "profile": profile,
                "subject_id": subject_id,
            },
        )

        # Get the appropriate processor
        processor = self.registry.get_processor(profile)

        logger.debug(
            f"Routing to processor: {processor.name}",
            extra={"processor": processor.name, "profile": profile},
        )

        # Download the media file
        try:
            media_bytes = download_object(
                bucket=parsed.bucket,
                key=parsed.key,
                max_bytes=self.settings.max_download_bytes,
            )
        except ValueError as e:
            # Size limit exceeded
            raise MediaTooLargeError(
                size=0,  # Unknown at this point
                max_size=self.settings.max_download_bytes,
            ) from e

        logger.info(
            f"Downloaded media file: {len(media_bytes)} bytes",
            extra={
                "size_bytes": len(media_bytes),
                "bucket": parsed.bucket,
                "key": parsed.key,
            },
        )

        # Execute verification
        result = await processor.verify(
            media_bytes=media_bytes,
            subject_id=subject_id,
            profile=profile,
            metadata=metadata,
        )

        logger.info(
            f"Verification complete: valid={result.valid}, confidence={result.confidence}",
            extra={
                "valid": result.valid,
                "confidence": result.confidence,
                "processor": processor.name,
            },
        )

        return result
