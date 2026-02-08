"""Shared test fixtures and configuration."""

import os
from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# Torchaudio 2.1+ removed list_audio_backends(); SpeechBrain still expects it. Patch before app load.
@pytest.fixture(scope="session")
def patch_torchaudio_backends() -> Generator[None, None, None]:
    """Add list_audio_backends to torchaudio if missing (compat with torchaudio 2.1+)."""
    try:
        import torchaudio

        if not hasattr(torchaudio, "list_audio_backends"):
            torchaudio.list_audio_backends = lambda: ["soundfile"]
    except ImportError:
        pass
    yield


# Set test environment variables before importing app modules
@pytest.fixture(scope="session", autouse=True)
def setup_test_env() -> Generator[None, None, None]:
    """Set up test environment variables."""
    test_env = {
        "S3_ENDPOINT_URL": "http://localhost:9000",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY_ID": "test_access_key",
        "S3_SECRET_ACCESS_KEY": "test_secret_key",
        "S3_BUCKET": "test-bucket",
        "S3_KEY_PREFIX": "uploads/",
        "S3_PRESIGNED_TTL_SECONDS": "300",
        "MAX_DOWNLOAD_BYTES": "10485760",
        "ALLOWED_CONTENT_TYPES": '["audio/wav", "audio/webm"]',
        "LOG_LEVEL": "DEBUG",
    }

    with patch.dict(os.environ, test_env, clear=False):
        # Clear cached settings
        from app.config.settings import get_settings

        get_settings.cache_clear()
        yield
        get_settings.cache_clear()


@pytest.fixture
def mock_s3_client() -> Generator[MagicMock, None, None]:
    """Mock the S3 client for testing without real S3 access."""
    mock_client = MagicMock()

    # Mock generate_presigned_url
    mock_client.generate_presigned_url.return_value = (
        "https://minio:9000/test-bucket/uploads/test_key.wav?signature=abc123"
    )

    # Mock head_object
    mock_client.head_object.return_value = {"ContentLength": 1000}

    # Mock get_object with a simple WAV file
    wav_header = _create_minimal_wav()
    mock_body = MagicMock()
    mock_body.read.return_value = wav_header
    mock_client.get_object.return_value = {"Body": mock_body}

    with patch("app.storage.s3_client.get_s3_client", return_value=mock_client):
        with patch("app.storage.presigned.get_s3_client", return_value=mock_client):
            yield mock_client


@pytest.fixture
def client(mock_s3_client: MagicMock, patch_torchaudio_backends: None) -> TestClient:
    """Create a test client with mocked dependencies."""
    from app.main import app

    return TestClient(app)


@pytest.fixture
def client_no_mock(patch_torchaudio_backends: None) -> TestClient:
    """Create a test client without S3 mocking (for health checks)."""
    from app.main import app

    return TestClient(app)


def _create_minimal_wav() -> bytes:
    """Create a minimal valid WAV file for testing.

    Returns:
        Bytes representing a valid WAV file header with minimal audio data.
    """
    import struct

    # WAV file parameters
    num_channels = 1
    sample_rate = 16000
    bits_per_sample = 16
    num_samples = 16000  # 1 second of audio

    bytes_per_sample = bits_per_sample // 8
    block_align = num_channels * bytes_per_sample
    byte_rate = sample_rate * block_align
    data_size = num_samples * block_align

    # Build WAV header
    header = bytearray()

    # RIFF header
    header.extend(b"RIFF")
    header.extend(struct.pack("<I", 36 + data_size))  # File size - 8
    header.extend(b"WAVE")

    # fmt chunk
    header.extend(b"fmt ")
    header.extend(struct.pack("<I", 16))  # Chunk size
    header.extend(struct.pack("<H", 1))  # Audio format (PCM)
    header.extend(struct.pack("<H", num_channels))
    header.extend(struct.pack("<I", sample_rate))
    header.extend(struct.pack("<I", byte_rate))
    header.extend(struct.pack("<H", block_align))
    header.extend(struct.pack("<H", bits_per_sample))

    # data chunk
    header.extend(b"data")
    header.extend(struct.pack("<I", data_size))

    # Add full 1 second of silence (ECAPA-TDNN needs minimum ~1s of audio)
    header.extend(b"\x00" * data_size)

    return bytes(header)


@pytest.fixture
def minimal_wav() -> bytes:
    """Provide a minimal valid WAV file for testing."""
    return _create_minimal_wav()


@pytest.fixture
def invalid_audio() -> bytes:
    """Provide invalid audio data for testing."""
    return b"This is not audio data"
