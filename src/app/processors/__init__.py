"""Media processors implementing the Strategy pattern."""

from app.processors.base import MediaProcessor, VerificationResult
from app.processors.registry import ProcessorRegistry, get_processor_registry

__all__ = [
    "MediaProcessor",
    "VerificationResult",
    "ProcessorRegistry",
    "get_processor_registry",
]
