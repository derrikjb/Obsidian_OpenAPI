# Obsidian OpenAPI Server Dockerfile
# Multi-stage build for optimal image size

# Build stage
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PATH="/opt/venv/bin:$PATH" \
    OBSIDIAN_OPENAPI_PORT=27150 \
    OBSIDIAN_OPENAPI_HOST=0.0.0.0

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create app directory
WORKDIR /app

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Create non-root user for security
RUN groupadd -r obsidian && useradd -r -g obsidian obsidian && \
    chown -R obsidian:obsidian /app
USER obsidian

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:27150/health || exit 1

# Expose port
EXPOSE 27150

# Run the application
CMD ["python", "-m", "app.main"]