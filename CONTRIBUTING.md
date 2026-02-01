# Contributing to Authentik Media Gateway

Thanks for your interest in contributing. This document explains how to get set up and submit changes.

## How to contribute

- **Bug reports and feature requests:** Open an [issue](https://github.com/Darius-Vallejo/authentik-media-gateway/issues) (use the Bug report or Feature request templates).
- **Code and docs:** Open a pull request. For larger changes, open an issue first to discuss.

## Development setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/Darius-Vallejo/authentik-media-gateway.git
   cd authentik-media-gateway
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   make install
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env if needed; defaults work for local dev (MinIO at localhost:9000)
   ```

4. **Run services (optional, for full flow)**
   ```bash
   make up    # MinIO + API + Redis
   make dev   # Or run API locally: make dev
   ```

## Before submitting

- **Tests:** `make test` (or `pytest tests -v`)
- **Lint:** `make lint` (ruff + mypy)
- **Format:** `make fmt` (ruff format and fix)

Pull requests should pass tests and lint. The PR template includes a checklist.

## Pull request process

1. Fork the repo and create a branch from `main`.
2. Make your changes; keep commits focused.
3. Run `make test` and `make lint`.
4. Open a PR with a clear description and link to any related issue (e.g. "Fixes #123").
5. Fill out the PR template checklist.

## Good first issues

Look for issues labeled [good first issue](https://github.com/Darius-Vallejo/authentik-media-gateway/labels/good%20first%20issue). Examples:

- Implement **OCRProcessor** (replace stub with Tesseract or AWS Textract).
- Implement **FaceProcessor** (replace stub with face_recognition or AWS Rekognition).

See `src/app/processors/base.py` for the processor contract and `src/app/processors/voice_bio.py` for a reference implementation.

## Project layout

- `src/app/api/` — FastAPI endpoints (health, presigned-url, verify).
- `src/app/processors/` — Verification processors (voice, OCR, face); add or extend here.
- `src/app/processors/registry.py` — ProcessorRegistry: register new processors by profile prefix.
- `src/app/storage/` — S3 client and presigned URL generation.
- `tests/` — Pytest tests; add tests for new or changed behavior.

## Questions

Open a [discussion](https://github.com/Darius-Vallejo/authentik-media-gateway/discussions) or an issue and we’ll help.
