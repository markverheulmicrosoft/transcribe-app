# Makefile for Transcribe App
# Using UV for fast Python dependency management

.PHONY: help install dev run test lint format clean docker-build docker-run

# Default target
help:
	@echo "Transcribe App - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install     - Install dependencies with UV"
	@echo "  make dev         - Install dev dependencies with UV"
	@echo ""
	@echo "Development:"
	@echo "  make run         - Run the app locally (with hot reload)"
	@echo "  make test        - Run tests with pytest"
	@echo "  make test-cov    - Run tests with coverage report"
	@echo "  make lint        - Run ruff linter"
	@echo "  make format      - Format code with ruff"
	@echo "  make typecheck   - Run mypy type checker"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  - Build Docker image"
	@echo "  make docker-run    - Run with Docker Compose"
	@echo "  make docker-stop   - Stop Docker Compose"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean       - Remove cache and build files"

# Install production dependencies
install:
	uv sync --no-dev

# Install all dependencies including dev
dev:
	uv sync

# Run the application locally with hot reload
run:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
test:
	uv run pytest -v

# Run tests with coverage
test-cov:
	uv run pytest --cov=app --cov-report=term-missing --cov-report=html

# Lint code
lint:
	uv run ruff check app tests

# Format code
format:
	uv run ruff format app tests
	uv run ruff check --fix app tests

# Type checking
typecheck:
	uv run mypy app

# Build Docker image
docker-build:
	docker build -t transcribe-app:latest .

# Run with Docker Compose
docker-run:
	docker-compose up -d

# Stop Docker Compose
docker-stop:
	docker-compose down

# Clean up cache files
clean:
	rm -rf __pycache__ .pytest_cache .coverage htmlcov .mypy_cache .ruff_cache
	rm -rf app/__pycache__ app/**/__pycache__
	rm -rf tests/__pycache__
	rm -rf uploads/*
	rm -rf .venv
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
