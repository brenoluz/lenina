# Lenina - Anvil RESTful Management API
# Multi-stage Docker build for optimized image size

# =============================================================================
# Stage 1: Builder
# =============================================================================
FROM python:3.11-slim AS builder

# Install build dependencies (needed for compiling Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Foundry (includes Anvil)
# Pin to specific version for reproducibility: v1.6.0-rc1 (latest stable as of 2026-01-22)
RUN curl -L https://foundry.paradigm.xyz | bash

# Source the shell configuration to make foundry available
ENV PATH="/root/.foundry/bin:${PATH}"

# Install specific Foundry version (pin for reproducibility)
# Latest stable: foundryup defaults to latest stable if no version specified
# For specific version: foundryup --version <version>
# Using empty version installs latest stable
RUN /root/.foundry/bin/foundryup

WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies into /install prefix
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# =============================================================================
# Stage 2: Runtime
# =============================================================================
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install only runtime dependencies (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Foundry binaries from builder stage
COPY --from=builder /root/.foundry /root/.foundry

# Set PATH to include Foundry binaries
ENV PATH="/root/.foundry/bin:${PATH}"

WORKDIR /app

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code (without .git directory)
COPY main.py .

# Expose the Lenina API port (default 8000)
EXPOSE 8000

# Expose Anvil RPC port (default 8545)
EXPOSE 8545

# Health check endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "main.py"]