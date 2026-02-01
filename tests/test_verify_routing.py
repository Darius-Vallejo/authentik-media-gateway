"""Tests for verification endpoint and processor routing."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestVerifyRouting:
    """Test suite for POST /verify processor routing."""

    def test_voice_profile_routes_to_voice_processor(
        self,
        client: TestClient,
    ) -> None:
        """Test that voice.* profiles route to VoiceBioProcessor."""
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "test-bucket/uploads/login_voice/test.wav",
                "profile": "voice.login.default",
                "subject_id": "user_123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["metadata"]["processor"] == "voice_bio"

    def test_voice_mfa_profile_routes_correctly(
        self,
        client: TestClient,
    ) -> None:
        """Test that voice.mfa.* profiles also route to VoiceBioProcessor."""
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "test-bucket/uploads/mfa_voice/test.wav",
                "profile": "voice.mfa.high",
                "subject_id": "user_456",
            },
        )

        assert response.status_code == 200
        assert response.json()["metadata"]["processor"] == "voice_bio"

    def test_ocr_profile_returns_not_implemented(
        self,
        client: TestClient,
    ) -> None:
        """Test that ocr.* profiles return 501 Not Implemented."""
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "test-bucket/uploads/id_scan/test.png",
                "profile": "ocr.id_card.passport",
                "subject_id": "user_123",
            },
        )

        assert response.status_code == 501
        data = response.json()
        assert data["detail"]["code"] == "PROCESSOR_NOT_IMPLEMENTED"
        assert "OCR processor is not implemented" in data["detail"]["detail"]

    def test_face_profile_returns_not_implemented(
        self,
        client: TestClient,
    ) -> None:
        """Test that face.* profiles return 501 Not Implemented."""
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "test-bucket/uploads/selfie/test.jpg",
                "profile": "face.login.selfie",
                "subject_id": "user_123",
            },
        )

        assert response.status_code == 501
        data = response.json()
        assert data["detail"]["code"] == "PROCESSOR_NOT_IMPLEMENTED"
        assert "Face recognition processor is not implemented" in data["detail"]["detail"]

    def test_invalid_profile_returns_400(
        self,
        client: TestClient,
    ) -> None:
        """Test that unknown profile prefix returns 400 error."""
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "test-bucket/uploads/unknown/test.bin",
                "profile": "unknown.type.variant",
                "subject_id": "user_123",
            },
        )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "INVALID_PROFILE"
        assert "Invalid profile" in data["detail"]["detail"]

    def test_empty_profile_returns_validation_error(
        self,
        client: TestClient,
    ) -> None:
        """Test that empty profile returns validation error."""
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "test-bucket/uploads/test/test.wav",
                "profile": "",
                "subject_id": "user_123",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_missing_profile_returns_validation_error(
        self,
        client: TestClient,
    ) -> None:
        """Test that missing profile field returns validation error."""
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "test-bucket/uploads/test/test.wav",
                "subject_id": "user_123",
            },
        )

        assert response.status_code == 422


class TestVerifyEvidenceRef:
    """Test suite for evidence_ref parsing and validation."""

    def test_s3_uri_format_accepted(
        self,
        client: TestClient,
    ) -> None:
        """Test that s3://bucket/key format is accepted."""
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "s3://test-bucket/uploads/voice/test.wav",
                "profile": "voice.login.default",
                "subject_id": "user_123",
            },
        )

        assert response.status_code == 200

    def test_bucket_key_format_accepted(
        self,
        client: TestClient,
    ) -> None:
        """Test that bucket/key format is accepted."""
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "test-bucket/uploads/voice/test.wav",
                "profile": "voice.login.default",
                "subject_id": "user_123",
            },
        )

        assert response.status_code == 200

    def test_key_without_prefix_rejected(
        self,
        client: TestClient,
    ) -> None:
        """Test that keys not starting with uploads/ are rejected."""
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "test-bucket/private/secret.wav",
                "profile": "voice.login.default",
                "subject_id": "user_123",
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "INVALID_EVIDENCE_REF"

    def test_path_traversal_rejected(
        self,
        client: TestClient,
    ) -> None:
        """Test that path traversal attempts are rejected."""
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "test-bucket/uploads/../private/secret.wav",
                "profile": "voice.login.default",
                "subject_id": "user_123",
            },
        )

        assert response.status_code == 400
        assert "path traversal" in response.json()["detail"]["detail"].lower()

    def test_empty_evidence_ref_rejected(
        self,
        client: TestClient,
    ) -> None:
        """Test that empty evidence_ref returns validation error."""
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "",
                "profile": "voice.login.default",
                "subject_id": "user_123",
            },
        )

        assert response.status_code == 422


class TestVerifyResponse:
    """Test suite for verification response structure."""

    def test_response_contains_required_fields(
        self,
        client: TestClient,
    ) -> None:
        """Test that response contains all required fields."""
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "test-bucket/uploads/voice/test.wav",
                "profile": "voice.login.default",
                "subject_id": "user_123",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "valid" in data
        assert "confidence" in data
        assert "reason" in data
        assert "metadata" in data

    def test_confidence_within_range(
        self,
        client: TestClient,
    ) -> None:
        """Test that confidence score is between 0 and 1."""
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "test-bucket/uploads/voice/test.wav",
                "profile": "voice.login.default",
                "subject_id": "user_123",
            },
        )

        data = response.json()
        assert 0.0 <= data["confidence"] <= 1.0

    def test_metadata_includes_subject_id(
        self,
        client: TestClient,
    ) -> None:
        """Test that metadata includes the subject_id."""
        subject_id = "user_test_789"
        response = client.post(
            "/verify",
            json={
                "evidence_ref": "test-bucket/uploads/voice/test.wav",
                "profile": "voice.login.default",
                "subject_id": subject_id,
            },
        )

        data = response.json()
        assert data["metadata"]["subject_id"] == subject_id
