# ==============================================================================
# Industrial-MCP: Multi-Stage Production Dockerfile (Non-Root Tier 2)
# ==============================================================================

# Stage 1: Build & Dependency Resolution via uv
FROM ghcr.io/astral-sh/uv:0.5.11-python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies using lockfile
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy source code and build wheel
COPY src ./src
COPY README.md ARCHITECTURE.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Stage 2: Minimal Non-Root Runtime Image
FROM python:3.12-slim-bookworm AS runner

WORKDIR /app

# Create non-root system user and group (Security standard Tier 2)
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser

# Set environment
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST="0.0.0.0" \
    PORT=8000

# Copy virtual environment and application code from builder
COPY --from=builder --chown=appuser:appgroup /app/.venv /app/.venv
COPY --chown=appuser:appgroup src ./src
COPY --chown=appuser:appgroup main.py pyproject.toml ./

# Ensure data directory exists with appropriate permissions
RUN mkdir -p /app/data /app/data/parquet && \
    chown -R appuser:appgroup /app/data

# Switch to non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/status')" || exit 1

ENTRYPOINT ["uvicorn", "src.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
