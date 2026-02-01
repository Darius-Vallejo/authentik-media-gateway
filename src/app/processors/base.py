"""Base class for media verification processors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class VerificationResult:
    """Result of a media verification operation.

    Attributes:
        valid: Whether the verification passed.
        confidence: Confidence score between 0.0 and 1.0.
        reason: Human-readable explanation of the result.
        metadata: Additional processor-specific metadata.
    """

    valid: bool
    confidence: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the confidence score is in valid range."""
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0 and 1, got {self.confidence}")


class MediaProcessor(ABC):
    """Abstract base class for media verification processors.

    Implementations of this class handle specific types of media verification
    (e.g., voice biometrics, OCR, face recognition). The processor is selected
    based on the profile prefix in the verification request.

    To add a new processor:
    1. Create a new class that inherits from MediaProcessor
    2. Implement the verify() method
    3. Register it in the ProcessorRegistry with appropriate profile prefixes
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the processor name for logging and identification."""
        ...

    @abstractmethod
    async def verify(
        self,
        media_bytes: bytes,
        subject_id: str,
        profile: str,
        metadata: dict[str, Any] | None = None,
    ) -> VerificationResult:
        """Verify the media content.

        Args:
            media_bytes: The raw media file content.
            subject_id: Identifier for the subject being verified.
            profile: The full verification profile string.
            metadata: Optional additional context for verification.

        Returns:
            VerificationResult with the outcome of verification.

        Raises:
            NotImplementedError: If the processor is a stub.
            ValueError: If the media format is invalid.
        """
        ...

    def supports_profile(self, profile: str) -> bool:
        """Check if this processor supports the given profile.

        Default implementation returns True. Override for more specific checks.

        Args:
            profile: The verification profile to check.

        Returns:
            True if this processor can handle the profile.
        """
        return True
