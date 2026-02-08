"""Enrollment endpoint for voice reference upload."""

import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import get_settings
from app.storage.s3_client import upload_object

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/enroll", tags=["enrollment"])


def _validate_wav(data: bytes) -> tuple[bool, str | None]:
    """Validate minimal WAV format: size and RIFF/WAVE header. Returns (valid, error_reason)."""
    if len(data) < 44:
        return False, "File too small to be a valid WAV file (minimum 44 bytes header)"
    if data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        if data[:3] == b"ID3" or data[:2] == b"\xff\xfb":
            return False, "MP3 format detected. Please provide WAV format."
        if data[:4] == b"OggS":
            return False, "OGG format detected. Please provide WAV format."
        return False, "Invalid audio format. Expected WAV file with RIFF/WAVE header."
    if data[12:16] != b"fmt ":
        return False, "Invalid WAV format: missing fmt chunk."
    return True, None


@router.post("/voice/{subject_id}")
async def enroll_voice(subject_id: str, file: UploadFile = File(...)) -> dict[str, str]:
    """Upload a voice enrollment (reference) for the given subject.

    The audio file must be WAV format. It is stored at references/{subject_id}/enrollment.wav
    and used later for verification.

    Args:
        subject_id: User identifier (must not contain '/' or '..').
        file: WAV audio file (multipart/form-data).

    Returns:
        200 with success message.

    Raises:
        HTTPException 400: Invalid subject_id or invalid/unsupported audio format.
        HTTPException 413: File exceeds size limit.
        HTTPException 500: S3 upload failed.
    """
    if "/" in subject_id or ".." in subject_id or not subject_id.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "detail": "subject_id must be a single segment (no '/' or '..')",
                "code": "INVALID_SUBJECT_ID",
            },
        )

    settings = get_settings()
    body = await file.read()

    if len(body) > settings.max_download_bytes:
        raise HTTPException(
            status_code=413,
            detail={
                "detail": f"File size exceeds maximum allowed ({settings.max_download_bytes} bytes)",
                "code": "FILE_TOO_LARGE",
            },
        )

    valid, reason = _validate_wav(body)
    if not valid:
        raise HTTPException(
            status_code=400,
            detail={
                "detail": reason or "Invalid audio format",
                "code": "INVALID_AUDIO",
            },
        )

    key = f"references/{subject_id}/enrollment.wav"
    try:
        upload_object(
            bucket=settings.s3_bucket,
            key=key,
            body=body,
            content_type="audio/wav",
        )
    except Exception as e:
        logger.exception("S3 upload failed for enrollment: %s", e)
        raise HTTPException(
            status_code=500,
            detail={
                "detail": "Failed to store enrollment",
                "code": "UPLOAD_FAILED",
            },
        ) from e

    logger.info("Enrollment stored for subject_id=%s at key=%s", subject_id, key)
    return {"message": "Voice enrollment stored successfully", "subject_id": subject_id}
