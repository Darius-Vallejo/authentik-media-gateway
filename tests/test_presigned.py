"""Tests for presigned URL endpoint."""

import pytest
from fastapi.testclient import TestClient


class TestPresignedUrlEndpoint:
    """Test suite for GET /presigned-url endpoint."""

    def test_presigned_url_returns_expected_fields(
        self,
        client: TestClient,
    ) -> None:
        """Test that presigned URL response contains all expected fields."""
        response = client.get(
            "/presigned-url",
            params={
                "purpose": "login_voice",
                "content_type": "audio/wav",
                "ext": "wav",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "upload_url" in data
        assert "bucket" in data
        assert "object_key" in data
        assert "evidence_ref" in data
        assert "expires_in" in data

    def test_object_key_under_uploads_prefix(
        self,
        client: TestClient,
    ) -> None:
        """Test that generated object_key starts with uploads/."""
        response = client.get(
            "/presigned-url",
            params={
                "purpose": "login_voice",
                "content_type": "audio/wav",
                "ext": "wav",
            },
        )

        data = response.json()
        assert data["object_key"].startswith("uploads/")

    def test_object_key_includes_purpose(
        self,
        client: TestClient,
    ) -> None:
        """Test that object_key includes the purpose."""
        purpose = "mfa_voice"
        response = client.get(
            "/presigned-url",
            params={
                "purpose": purpose,
                "content_type": "audio/wav",
                "ext": "wav",
            },
        )

        data = response.json()
        assert purpose in data["object_key"]

    def test_object_key_has_correct_extension(
        self,
        client: TestClient,
    ) -> None:
        """Test that object_key ends with the specified extension."""
        response = client.get(
            "/presigned-url",
            params={
                "purpose": "login_voice",
                "content_type": "audio/wav",
                "ext": "wav",
            },
        )

        data = response.json()
        assert data["object_key"].endswith(".wav")

    def test_evidence_ref_format(
        self,
        client: TestClient,
    ) -> None:
        """Test that evidence_ref is in bucket/key format."""
        response = client.get(
            "/presigned-url",
            params={
                "purpose": "login_voice",
                "content_type": "audio/wav",
                "ext": "wav",
            },
        )

        data = response.json()
        evidence_ref = data["evidence_ref"]

        # Should be bucket/object_key
        assert "/" in evidence_ref
        assert data["bucket"] in evidence_ref
        assert data["object_key"] in evidence_ref

    def test_expires_in_matches_config(
        self,
        client: TestClient,
    ) -> None:
        """Test that expires_in matches configured TTL."""
        response = client.get(
            "/presigned-url",
            params={
                "purpose": "login_voice",
                "content_type": "audio/wav",
                "ext": "wav",
            },
        )

        data = response.json()
        # Default is 300 seconds
        assert data["expires_in"] == 300


class TestPresignedUrlValidation:
    """Test suite for presigned URL validation."""

    def test_invalid_content_type_returns_400(
        self,
        client: TestClient,
    ) -> None:
        """Test that unsupported content types return 400 error."""
        response = client.get(
            "/presigned-url",
            params={
                "purpose": "login_voice",
                "content_type": "video/mp4",
                "ext": "mp4",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "INVALID_CONTENT_TYPE"

    def test_audio_wav_content_type_allowed(
        self,
        client: TestClient,
    ) -> None:
        """Test that audio/wav is an allowed content type."""
        response = client.get(
            "/presigned-url",
            params={
                "purpose": "test",
                "content_type": "audio/wav",
                "ext": "wav",
            },
        )

        assert response.status_code == 200

    def test_audio_webm_content_type_allowed(
        self,
        client: TestClient,
    ) -> None:
        """Test that audio/webm is an allowed content type."""
        response = client.get(
            "/presigned-url",
            params={
                "purpose": "test",
                "content_type": "audio/webm",
                "ext": "webm",
            },
        )

        assert response.status_code == 200

    def test_missing_purpose_returns_validation_error(
        self,
        client: TestClient,
    ) -> None:
        """Test that missing purpose parameter returns 422."""
        response = client.get(
            "/presigned-url",
            params={
                "content_type": "audio/wav",
                "ext": "wav",
            },
        )

        assert response.status_code == 422

    def test_missing_content_type_returns_validation_error(
        self,
        client: TestClient,
    ) -> None:
        """Test that missing content_type parameter returns 422."""
        response = client.get(
            "/presigned-url",
            params={
                "purpose": "login_voice",
                "ext": "wav",
            },
        )

        assert response.status_code == 422

    def test_missing_ext_returns_validation_error(
        self,
        client: TestClient,
    ) -> None:
        """Test that missing ext parameter returns 422."""
        response = client.get(
            "/presigned-url",
            params={
                "purpose": "login_voice",
                "content_type": "audio/wav",
            },
        )

        assert response.status_code == 422

    def test_purpose_too_long_returns_validation_error(
        self,
        client: TestClient,
    ) -> None:
        """Test that purpose exceeding max length returns 422."""
        response = client.get(
            "/presigned-url",
            params={
                "purpose": "a" * 100,  # Max is 64
                "content_type": "audio/wav",
                "ext": "wav",
            },
        )

        assert response.status_code == 422

    def test_extension_sanitized(
        self,
        client: TestClient,
    ) -> None:
        """Test that extension with leading dot is handled correctly."""
        response = client.get(
            "/presigned-url",
            params={
                "purpose": "test",
                "content_type": "audio/wav",
                "ext": ".wav",  # With leading dot
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Should not have double dots
        assert ".." not in data["object_key"]
        assert data["object_key"].endswith(".wav")


class TestPresignedUrlUniqueness:
    """Test that presigned URLs generate unique keys."""

    def test_consecutive_requests_generate_unique_keys(
        self,
        client: TestClient,
    ) -> None:
        """Test that multiple requests generate different object keys."""
        params = {
            "purpose": "login_voice",
            "content_type": "audio/wav",
            "ext": "wav",
        }

        response1 = client.get("/presigned-url", params=params)
        response2 = client.get("/presigned-url", params=params)

        key1 = response1.json()["object_key"]
        key2 = response2.json()["object_key"]

        assert key1 != key2
