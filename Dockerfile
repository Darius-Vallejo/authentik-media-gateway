# =============================================================================
# Authentik Media Gateway - Multi-stage Dockerfile
# =============================================================================
# Build: docker build -t authentik-media-gateway .
# Run:   docker run -p 8000:8000 --env-file .env authentik-media-gateway
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder
# -----------------------------------------------------------------------------
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project (pyproject at root + src layout)
COPY pyproject.toml .
COPY src ./src
COPY README.md .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies (without dev dependencies)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
FROM python:3.11-slim as runtime

# Labels
LABEL org.opencontainers.image.title="Authentik Media Gateway"
LABEL org.opencontainers.image.description="Claim Check pattern gateway for Authentik media verification"
LABEL org.opencontainers.image.version="0.1.0"

# Create non-root user for security
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code (app is installed in venv; copy for runtime)
COPY src/app ./app

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default environment variables (can be overridden)
ENV APP_HOST=0.0.0.0 \
    APP_PORT=8000 \
    LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
