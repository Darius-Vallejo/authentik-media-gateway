"""Face recognition processor stub for facial verification.

This is a placeholder that raises NotImplementedError.
Implement with face_recognition, AWS Rekognition, or similar service.
"""

from typing import Any

from app.processors.base import MediaProcessor, VerificationResult


class FaceProcessor(MediaProcessor):
    """Face recognition processor for identity verification.

    This is a stub implementation. To implement:
    1. Add face recognition library (e.g., face_recognition, dlib)
    2. Implement face detection and embedding extraction
    3. Add comparison logic against stored face templates
    """

    @property
    def name(self) -> str:
        """Return the processor name."""
        return "face"

    async def verify(
        self,
        media_bytes: bytes,
        subject_id: str,
        profile: str,
        metadata: dict[str, Any] | None = None,
    ) -> VerificationResult:
        """Verify identity from facial image.

        Args:
            media_bytes: Image file content (PNG, JPEG, etc.).
            subject_id: The user identifier to verify against.
            profile: Verification profile (e.g., 'face.login.selfie').
            metadata: Optional context (e.g., liveness check requirements).

        Raises:
            NotImplementedError: This processor is not yet implemented.
        """
        raise NotImplementedError(
            f"Face recognition processor is not implemented. "
            f"Profile '{profile}' requires face recognition capabilities. "
            f"To implement: Add face_recognition or AWS Rekognition integration."
        )
