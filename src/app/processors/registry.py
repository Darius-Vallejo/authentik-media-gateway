"""Processor registry for routing verification requests by profile."""

from functools import lru_cache
from typing import TYPE_CHECKING

from app.processors.base import MediaProcessor
from app.processors.face_stub import FaceProcessor
from app.processors.ocr_stub import OCRProcessor
from app.processors.voice_bio import VoiceBioProcessor

if TYPE_CHECKING:
    pass


class InvalidProfileError(Exception):
    """Raised when a profile doesn't match any registered processor."""

    def __init__(self, profile: str, available_prefixes: list[str]) -> None:
        self.profile = profile
        self.available_prefixes = available_prefixes
        super().__init__(
            f"Invalid profile '{profile}'. "
            f"Profile must start with one of: {', '.join(available_prefixes)}"
        )


class ProcessorRegistry:
    """Registry mapping profile prefixes to processor instances.

    The registry uses prefix matching to route verification requests
    to the appropriate processor. For example:
    - 'voice.login.default' -> VoiceBioProcessor
    - 'ocr.id_card.passport' -> OCRProcessor
    - 'face.login.selfie' -> FaceProcessor

    To add a new processor:
    1. Create a class that inherits from MediaProcessor
    2. Register it in _build_registry() with its prefix(es)
    """

    def __init__(self) -> None:
        """Initialize the registry with default processors."""
        self._processors: dict[str, MediaProcessor] = {}
        self._build_registry()

    def _build_registry(self) -> None:
        """Build the processor registry with prefix mappings.

        Add new processors here by mapping their profile prefix
        to an instance of the processor.
        """
        # Voice biometrics processor
        voice_processor = VoiceBioProcessor()
        self._processors["voice."] = voice_processor

        # OCR processor (stub)
        ocr_processor = OCRProcessor()
        self._processors["ocr."] = ocr_processor

        # Face recognition processor (stub)
        face_processor = FaceProcessor()
        self._processors["face."] = face_processor

    def get_processor(self, profile: str) -> MediaProcessor:
        """Get the processor for a given profile.

        Args:
            profile: The verification profile string.

        Returns:
            The MediaProcessor instance for this profile.

        Raises:
            InvalidProfileError: If no processor matches the profile prefix.
        """
        for prefix, processor in self._processors.items():
            if profile.startswith(prefix):
                return processor

        raise InvalidProfileError(
            profile=profile,
            available_prefixes=list(self._processors.keys()),
        )

    @property
    def available_prefixes(self) -> list[str]:
        """Get list of registered profile prefixes."""
        return list(self._processors.keys())

    def is_valid_profile(self, profile: str) -> bool:
        """Check if a profile matches any registered processor.

        Args:
            profile: The profile to validate.

        Returns:
            True if a processor exists for this profile.
        """
        return any(profile.startswith(prefix) for prefix in self._processors)


@lru_cache
def get_processor_registry() -> ProcessorRegistry:
    """Get the cached processor registry singleton.

    Returns:
        The ProcessorRegistry instance.
    """
    return ProcessorRegistry()
