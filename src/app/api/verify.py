"""Verification endpoint for media processing."""

import logging

from fastapi import APIRouter, HTTPException

from app.processors.registry import InvalidProfileError
from app.schemas.verification import VerificationRequest, VerificationResponse
from app.services.verification_service import (
    InvalidEvidenceRefError,
    MediaTooLargeError,
    VerificationService,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["verification"])


@router.post("/verify", response_model=VerificationResponse)
async def verify_media(request: VerificationRequest) -> VerificationResponse:
    """Verify uploaded media using the appropriate processor.

    This endpoint implements the Claim Check pattern:
    1. Downloads the media from S3 using the evidence_ref
    2. Routes to the correct processor based on the profile prefix
    3. Returns the verification result

    Args:
        request: Verification request with evidence_ref, profile, and subject_id.

    Returns:
        VerificationResponse with validity, confidence, and metadata.

    Raises:
        HTTPException 400: Invalid evidence_ref or profile.
        HTTPException 413: Media file too large.
        HTTPException 501: Processor not implemented (stub).
        HTTPException 500: Unexpected error during verification.
    """
    service = VerificationService()

    try:
        result = await service.verify(
            evidence_ref=request.evidence_ref,
            profile=request.profile,
            subject_id=request.subject_id,
            metadata=request.metadata,
        )

        return VerificationResponse(
            valid=result.valid,
            confidence=result.confidence,
            reason=result.reason,
            metadata=result.metadata,
        )

    except InvalidEvidenceRefError as e:
        logger.warning(f"Invalid evidence ref: {e.message}")
        raise HTTPException(
            status_code=400,
            detail={
                "detail": e.message,
                "code": "INVALID_EVIDENCE_REF",
            },
        ) from e

    except InvalidProfileError as e:
        logger.warning(f"Invalid profile: {e.profile}")
        raise HTTPException(
            status_code=400,
            detail={
                "detail": str(e),
                "code": "INVALID_PROFILE",
            },
        ) from e

    except MediaTooLargeError as e:
        logger.warning(f"Media too large: {e.max_size} bytes limit exceeded")
        raise HTTPException(
            status_code=413,
            detail={
                "detail": str(e),
                "code": "MEDIA_TOO_LARGE",
            },
        ) from e

    except NotImplementedError as e:
        logger.info(f"Processor not implemented: {e}")
        raise HTTPException(
            status_code=501,
            detail={
                "detail": str(e),
                "code": "PROCESSOR_NOT_IMPLEMENTED",
            },
        ) from e

    except Exception as e:
        logger.exception(f"Unexpected error during verification: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "detail": "An unexpected error occurred during verification",
                "code": "INTERNAL_ERROR",
            },
        ) from e
