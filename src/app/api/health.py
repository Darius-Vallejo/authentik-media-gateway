"""Health check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Check if the service is running.

    Returns:
        A simple status object indicating the service is operational.
    """
    return {"status": "ok"}
