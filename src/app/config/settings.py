"""Application settings loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root (src/app/config -> project root) so .env is found regardless of cwd
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class Settings(BaseSettings):
    """Application configuration loaded from environment variables.

    All settings can be overridden via environment variables.
    Prefix is not used to keep variable names simple.
    """

    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_host: str = Field(default="0.0.0.0", description="Host to bind the server to")
    app_port: int = Field(default=8000, description="Port to bind the server to")
    log_level: str = Field(default="INFO", description="Logging level")

    # S3/MinIO settings (defaults allow local dev without .env; set in .env for real S3/MinIO)
    s3_endpoint_url: str = Field(
        default="http://localhost:9000",
        description="S3-compatible endpoint URL (e.g., http://minio:9000)",
    )
    s3_region: str = Field(default="us-east-1", description="S3 region")
    s3_access_key_id: str = Field(
        default="minioadmin",
        description="S3 access key ID",
    )
    s3_secret_access_key: str = Field(
        default="minioadmin",
        description="S3 secret access key",
    )
    s3_bucket: str = Field(
        default="media-gateway",
        description="S3 bucket name for media storage",
    )
    s3_key_prefix: str = Field(
        default="uploads/",
        description="Required prefix for all object keys (security boundary)",
    )
    s3_presigned_ttl_seconds: int = Field(
        default=300,
        description="TTL in seconds for presigned URLs",
    )
    s3_timeout_seconds: int = Field(
        default=30,
        description="Timeout for S3 operations in seconds",
    )

    # Security and limits
    max_download_bytes: int = Field(
        default=10 * 1024 * 1024,  # 10 MB
        description="Maximum size in bytes for downloaded media files",
    )
    allowed_content_types: list[str] = Field(
        default=["audio/wav", "audio/webm", "audio/mpeg"],
        description="Allowed MIME types for presigned URL generation",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: The application settings singleton.
    """
    return Settings()
