"""FastAPI application entry point."""

import logging
import sys
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import enroll, health, presigned, verify
from app.config import get_settings


def configure_logging() -> None:
    """Configure application logging."""
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    # Reduce noise from boto3/botocore
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events.
    """
    configure_logging()
    logger = logging.getLogger(__name__)
    settings = get_settings()

    logger.info(
        f"Starting authentik-media-gateway on {settings.app_host}:{settings.app_port}"
    )
    logger.info(f"S3 endpoint: {settings.s3_endpoint_url}")
    logger.info(f"S3 bucket: {settings.s3_bucket}")
    logger.info(f"Key prefix: {settings.s3_key_prefix}")

    yield

    logger.info("Shutting down authentik-media-gateway")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Authentik Media Gateway",
        description=(
            "Claim Check pattern implementation for Authentik media verification flows. "
            "Provides presigned URL generation for media uploads and verification "
            "using extensible processors (voice biometrics, OCR, face recognition)."
        ),
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        """Add a unique request ID to each request for tracing."""
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle uncaught exceptions with consistent error format."""
        logger = logging.getLogger(__name__)
        request_id = getattr(request.state, "request_id", "unknown")

        logger.exception(
            f"Unhandled exception: {exc}",
            extra={"request_id": request_id},
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": "An internal server error occurred",
                "code": "INTERNAL_ERROR",
                "request_id": request_id,
            },
        )

    # Include routers
    app.include_router(health.router)
    app.include_router(presigned.router)
    app.include_router(verify.router)
    app.include_router(enroll.router)

    return app


# Create app instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )
