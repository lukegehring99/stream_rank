# Backend Dockerfile for FastAPI application
# Production-ready Python 3.11 image

FROM python:3.11-slim AS base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd --gid 1000 appgroup \
    && useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser

# Copy requirements and install dependencies in base stage
# This ensures both dev (base) and production stages have dependencies
COPY requirements-api.txt requirements-worker.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt -r requirements-worker.txt

# -------------------
# Production stage
# -------------------
FROM base AS production

# Copy application code
COPY app/ ./app/
COPY worker/ ./worker/
COPY db/ ./db/
COPY scripts/ ./scripts/

# Make scripts executable
RUN chmod +x ./scripts/*.sh 2>/dev/null || true

# Change ownership to non-root user
RUN chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Default command for API service
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
