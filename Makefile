# Authentik Media Gateway - Makefile
# Run `make help` to see available commands

.PHONY: help dev test up down logs clean fmt lint install

# Default target
help:
	@echo "Authentik Media Gateway - Available Commands"
	@echo ""
	@echo "Development:"
	@echo "  make install  - Install dependencies locally"
	@echo "  make dev      - Run development server with hot reload"
	@echo "  make test     - Run pytest test suite"
	@echo "  make fmt      - Format code with ruff"
	@echo "  make lint     - Run linter checks"
	@echo ""
	@echo "Docker:"
	@echo "  make up       - Start all services (docker compose up)"
	@echo "  make down     - Stop all services (docker compose down)"
	@echo "  make logs     - Follow API logs"
	@echo "  make build    - Rebuild Docker images"
	@echo "  make clean    - Remove volumes and containers"
	@echo ""

# Install dependencies locally (from project root; pyproject.toml + src layout)
install:
	pip install -e ".[dev]"

# Run development server locally (PYTHONPATH=src so uvicorn finds app)
dev:
	PYTHONPATH=src uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests (pytest reads testpaths=["tests"] and pythonpath=["src"] from pyproject.toml)
test:
	pytest tests -v --tb=short

# Run tests with coverage
test-cov:
	pytest tests -v --cov=app --cov-report=term-missing

# Format code with ruff
fmt:
	ruff format src tests
	ruff check --fix src tests

# Run linter
lint:
	ruff check src tests
	mypy src/app

# Docker commands (use docker-compose if "docker compose" is not available)
DOCKER_COMPOSE := $(shell command -v docker-compose 2>/dev/null || echo "docker compose")
up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f api

build:
	$(DOCKER_COMPOSE) build --no-cache

# Clean up everything
clean:
	$(DOCKER_COMPOSE) down -v --remove-orphans
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true

# Quick health check
health:
	curl -s http://localhost:8000/health | python -m json.tool
