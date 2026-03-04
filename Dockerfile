# Lenina - Anvil RESTful Management API
# Docker container with Python runtime and Foundry/Anvil

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \ 
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Foundry (includes Anvil)
RUN curl -L https://foundry.paradigm.xyz | bash

# Source the shell configuration to make foundry available
ENV PATH="/root/.foundry/bin:${PATH}"

# Install foundry tools (anvil, cast, forge, chisel)
RUN /root/.foundry/bin/foundryup

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
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
