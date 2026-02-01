# authentik-media-gateway
Media verification gateway for Authentik using the Claim Check pattern (voice, face, OCR).

A production-ready FastAPI service implementing the **Claim Check pattern** for Authentik media verification flows. This gateway enables biometric authentication (voice, face, document OCR) in Authentik by handling media upload and verification through extensible processors.

## Problem Solved

Authentik doesn't natively support media-based verification (voice biometrics, document scanning, facial recognition). This gateway bridges that gap by:

1. **Providing presigned URLs** for secure client-side media uploads to S3/MinIO
2. **Implementing the Claim Check pattern** - clients upload to object storage, then pass a reference for server-side verification
3. **Routing verification requests** to specialized processors based on profile prefixes
4. **Integrating with Authentik** via Expression Policies that call the `/verify` endpoint

## Architecture

```
┌─────────────────┐     1. GET /presigned-url      ┌──────────────────────┐
│                 │ ─────────────────────────────► │                      │
│   Authentik     │                                │  Media Gateway API   │
│   (Frontend)    │ ◄───────────────────────────── │                      │
│                 │     2. Return upload URL       │  ┌────────────────┐  │
└────────┬────────┘                                │  │ Voice Processor│  │
         │                                         │  ├────────────────┤  │
         │ 3. PUT file                             │  │ OCR Processor  │  │
         ▼                                         │  ├────────────────┤  │
┌─────────────────┐                                │  │ Face Processor │  │
│   MinIO / S3    │ ◄──────────────────────────────│  └────────────────┘  │
│                 │     5. Download for verify     └──────────────────────┘
└─────────────────┘                                          ▲
                                                             │
┌─────────────────┐     4. POST /verify                      │
│   Authentik     │ ─────────────────────────────────────────┘
│   (Policy)      │     6. Return {valid, confidence}
└─────────────────┘
```

## Project Status

⚠️ Early-stage MVP. APIs may change.
Voice verification is implemented as a reference architecture.
OCR and Face processors are planned.

## Who is this for?

- Authentik operators
- Security engineers
- OSS contributors interested in biometrics

## Non-goals (for now)

- End-user UI
- Biometric enrollment flows
- Production-grade anti-spoofing

## Quick Start

### 1. Clone and Configure

```bash
# Copy environment file
cp .env.example .env

# Edit .env if needed (defaults work for local development)
```

### 2. Start Services

```bash
# Start MinIO + API + Redis
make up

# Or with docker compose directly
docker compose up -d
```

### 3. Verify Installation

```bash
# Health check
curl http://localhost:8000/health
# Returns: {"status": "ok"}

# Check API docs
open http://localhost:8000/docs
```

### 4. Test the Flow

```bash
# Step 1: Get presigned URL for upload
curl "http://localhost:8000/presigned-url?purpose=login_voice&content_type=audio/wav&ext=wav"

# Response:
# {
#   "upload_url": "http://localhost:9000/media-gateway/uploads/...",
#   "bucket": "media-gateway",
#   "object_key": "uploads/login_voice/20240101_120000_abc123.wav",
#   "evidence_ref": "media-gateway/uploads/login_voice/20240101_120000_abc123.wav",
#   "expires_in": 300
# }

# Step 2: Upload file using the presigned URL
curl -X PUT \
  -H "Content-Type: audio/wav" \
  --data-binary @test_audio.wav \
  "<upload_url from step 1>"

# Step 3: Verify the uploaded media
curl -X POST http://localhost:8000/verify \
  -H "Content-Type: application/json" \
  -d '{
    "evidence_ref": "media-gateway/uploads/login_voice/20240101_120000_abc123.wav",
    "profile": "voice.login.default",
    "subject_id": "user_123"
  }'

# Response:
# {
#   "valid": true,
#   "confidence": 0.85,
#   "reason": "Voice sample validated successfully",
#   "metadata": {...}
# }
```

## API Endpoints

### GET /health

Health check endpoint.

```json
{ "status": "ok" }
```

### GET /presigned-url

Generate a presigned PUT URL for uploading media.

**Query Parameters:**
- `purpose` (required): Upload purpose (e.g., "login_voice", "mfa_voice")
- `content_type` (required): MIME type (e.g., "audio/wav")
- `ext` (required): File extension without dot (e.g., "wav")

**Response:**
```json
{
  "upload_url": "https://...",
  "bucket": "media-gateway",
  "object_key": "uploads/login_voice/...",
  "evidence_ref": "media-gateway/uploads/...",
  "expires_in": 300
}
```

### POST /verify

Verify uploaded media using the appropriate processor.

**Request Body:**
```json
{
  "evidence_ref": "bucket/uploads/path/to/file.wav",
  "profile": "voice.login.default",
  "subject_id": "user_123",
  "metadata": {}  // optional
}
```

**Response:**
```json
{
  "valid": true,
  "confidence": 0.85,
  "reason": "Voice sample validated successfully",
  "metadata": {
    "processor": "voice_bio",
    "audio_info": {...}
  }
}
```

## Verification Profiles

Profiles determine which processor handles the verification request. Format: `type.category.variant`

| Prefix | Processor | Status |
|--------|-----------|--------|
| `voice.*` | VoiceBioProcessor | Implemented (MVP) |
| `ocr.*` | OCRProcessor | Stub (501) |
| `face.*` | FaceProcessor | Stub (501) |

Examples:
- `voice.login.default` - Voice verification for login
- `voice.mfa.high` - High-security voice MFA
- `ocr.id_card.passport` - Passport OCR (not implemented)
- `face.login.selfie` - Facial recognition (not implemented)

## Authentik Integration

### Import the Blueprint

1. Go to **Authentik Admin > System > Blueprints**
2. Click **Create** and upload `blueprints/authentik-blueprint.yaml`
3. Edit the blueprint to update `MEDIA_GATEWAY_URL`:
   - Docker on same host: `http://host.docker.internal:8000`
   - Docker Compose network: `http://media-gateway-api:8000`
   - External: `https://your-gateway.example.com`

### Manual Integration

If you prefer manual setup, create an **Expression Policy** with this code:

```python
import requests

MEDIA_GATEWAY_URL = "http://host.docker.internal:8000"

evidence_ref = request.context.get("prompt_data", {}).get("evidence_ref")
profile = request.context.get("prompt_data", {}).get("profile")
subject_id = request.user.username

response = requests.post(
    f"{MEDIA_GATEWAY_URL}/verify",
    json={
        "evidence_ref": evidence_ref,
        "profile": profile,
        "subject_id": subject_id
    },
    timeout=30
)

result = response.json()
if result.get("valid") and result.get("confidence", 0) >= 0.7:
    return True

ak_message(f"Verification failed: {result.get('reason')}")
return False
```

## Configuration

All configuration is via environment variables. See `.env.example` for all options.

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_HOST` | Server bind host | `0.0.0.0` |
| `APP_PORT` | Server bind port | `8000` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `S3_ENDPOINT_URL` | S3/MinIO endpoint | Required |
| `S3_BUCKET` | Storage bucket | Required |
| `S3_KEY_PREFIX` | Required key prefix | `uploads/` |
| `MAX_DOWNLOAD_BYTES` | Max file size | `10485760` (10MB) |
| `ALLOWED_CONTENT_TYPES` | Allowed MIME types | `["audio/wav", "audio/webm"]` |

## Development

### Local Setup

```bash
# Install dependencies
make install

# Run development server
make dev

# Run tests
make test

# Format and lint
make fmt
make lint
```

### Adding a New Processor

1. Create a new file in `src/app/processors/`:

```python
from app.processors.base import MediaProcessor, VerificationResult

class MyProcessor(MediaProcessor):
    @property
    def name(self) -> str:
        return "my_processor"

    async def verify(
        self,
        media_bytes: bytes,
        subject_id: str,
        profile: str,
        metadata: dict | None = None,
    ) -> VerificationResult:
        # Your verification logic here
        return VerificationResult(
            valid=True,
            confidence=0.9,
            reason="Verification passed",
            metadata={"processor": self.name}
        )
```

2. Register it in `src/app/processors/registry.py`:

```python
def _build_registry(self) -> None:
    # ... existing processors ...
    self._processors["mytype."] = MyProcessor()
```

## Security Considerations

### Object Key Restrictions

- All object keys must start with the configured prefix (default: `uploads/`)
- Path traversal (`..`) is blocked
- Absolute paths are rejected

### Size Limits

- Maximum download size is configurable (default: 10MB)
- Size is checked before and after download

### Content Type Validation

- Only allowed MIME types can get presigned URLs
- Configure via `ALLOWED_CONTENT_TYPES`

### Spoofing Disclaimer

This MVP implementation does **not** include:
- Liveness detection for voice/face
- Anti-replay protection
- Enrollment flow for reference samples

For production use, implement these additional security measures.

### Object Lifecycle

Consider implementing:
- Automatic deletion of processed files
- Expiration policies on the S3 bucket
- Audit logging for all verification attempts

## Project Structure

```
authentik-media-gateway/
├── src/
│   ├── app/
│   │   ├── api/           # FastAPI endpoints
│   │   ├── config/        # Pydantic settings
│   │   ├── processors/    # Verification processors
│   │   ├── schemas/       # Request/response models
│   │   ├── services/      # Business logic
│   │   ├── storage/       # S3 client and presigned URLs
│   │   └── main.py        # Application entry point
│   └── pyproject.toml
├── tests/                 # Pytest test suite
├── blueprints/            # Authentik blueprint templates
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── .env.example
```

## License

MIT License - See LICENSE file for details.
