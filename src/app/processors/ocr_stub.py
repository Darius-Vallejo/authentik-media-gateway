"""OCR processor stub for document text extraction.

This is a placeholder that raises NotImplementedError.
Implement with Tesseract, AWS Textract, or similar OCR service.
"""

from typing import Any

from app.processors.base import MediaProcessor, VerificationResult


class OCRProcessor(MediaProcessor):
    """OCR processor for document verification.

    This is a stub implementation. To implement:
    1. Add OCR library (e.g., pytesseract, boto3 for Textract)
    2. Implement document text extraction
    3. Add validation logic based on profile requirements
    """

    @property
    def name(self) -> str:
        """Return the processor name."""
        return "ocr"

    async def verify(
        self,
        media_bytes: bytes,
        subject_id: str,
        profile: str,
        metadata: dict[str, Any] | None = None,
    ) -> VerificationResult:
        """Extract and verify text from document image.

        Args:
            media_bytes: Image file content (PNG, JPEG, etc.).
            subject_id: The user identifier for the document.
            profile: Verification profile (e.g., 'ocr.id_card.passport').
            metadata: Optional context (e.g., expected fields, document type).

        Raises:
            NotImplementedError: This processor is not yet implemented.
        """
        raise NotImplementedError(
            f"OCR processor is not implemented. "
            f"Profile '{profile}' requires OCR capabilities. "
            f"To implement: Add pytesseract or AWS Textract integration."
        )
