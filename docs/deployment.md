# Lenina Deployment Guide

Production and development deployment guide for Lenina.

## Environment Setup

Before using the examples in this guide, set the `LENINA_BASE_URL` environment variable:

```bash
# For local development
export LENINA_BASE_URL=http://localhost:8000

# For remote servers
export LENINA_BASE_URL=http://your-server-ip:8000

# Verify it's set
echo $LENINA_BASE_URL
```

This variable is used in all curl examples throughout this guide.

## Table of Contents

- [Local Development](#local-development)
- [Docker Deployment](#docker-deployment)
- [Docker Compose](#docker-compose)
- [Kubernetes](#kubernetes)
- [Environment Configuration](#environment-configuration)
- [Monitoring and Health Checks](#monitoring-and-health-checks)
- [Troubleshooting](#troubleshooting)

---

## Local Development

### Prerequisites

1. **Python 3.10 or higher**
   ```bash
   python --version
   ```

2. **Foundry (for Anvil)**
   ```bash
   curl -L https://foundry.paradigm.xyz | bash
   foundryup
   ```

3. **Verify installation**
   ```bash
   anvil --version
   ```

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd lenina
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Lenina**
   ```bash
   python main.py
   ```

5. **Verify it's running**
   ```bash
   curl $LENINA_BASE_URL/health
   ```

### Configuration

Create a `.env` file (optional):
```bash
LENINA_PORT=8000
ANVIL_PORT=8545
ANVIL_CHAIN_ID=31337
ANVIL_GAS_LIMIT=30000000
# ANVIL_MNEMONIC="your custom mnemonic"
```

Run with environment variables:
```bash
export LENINA_PORT=8001
python main.py
```

---

## Docker Deployment

### Build Image

```bash
docker build -t lenina:latest .
```

### Run Container

**Basic:**
```bash
docker run -d \
  --name lenina \
  -p 8000:8000 \
  -p 8545:8545 \
  lenina:latest
```

**With custom configuration:**
```bash
docker run -d \
  --name lenina \
  -p 8000:8000 \
  -p 8545:8545 \
  -e ANVIL_CHAIN_ID=1337 \
  -e ANVIL_GAS_LIMIT=50000000 \
  lenina:latest
```

### Verify Container

```bash
# Check status
docker ps | grep lenina

# Check logs
docker logs lenina

# Test health endpoint
curl $LENINA_BASE_URL/health
```

### Stop Container

```bash
docker stop lenina
docker rm lenina
```

---

## Docker Compose

### docker-compose.yml

```yaml
version: '3.8'

services:
  lenina:
    build: .
    ports:
      - "8000:8000"
      - "8545:8545"
    environment:
      - LENINA_PORT=8000
      - ANVIL_PORT=8545
      - ANVIL_CHAIN_ID=31337
      - ANVIL_GAS_LIMIT=30000000
    volumes:
      - lenina-data:/root/.foundry
    healthcheck:
      test: ["CMD", "curl", "-f", "$LENINA_BASE_URL/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

volumes:
  lenina-data:
```

### Commands

**Start:**
```bash
docker-compose up -d
```

**Stop:**
```bash
docker-compose down
```

**View logs:**
```bash
docker-compose logs -f
```

**Restart:**
```bash
docker-compose restart
```

**Rebuild:**
```bash
docker-compose up -d --build
```

---

## Kubernetes

### Deployment YAML

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: lenina
  labels:
    app: lenina
spec:
  replicas: 1
  selector:
    matchLabels:
      app: lenina
  template:
    metadata:
      labels:
        app: lenina
    spec:
      containers:
      - name: lenina
        image: lenina:latest
        ports:
        - containerPort: 8000
          name: api
        - containerPort: 8545
          name: anvil-rpc
        env:
        - name: LENINA_PORT
          value: "8000"
        - name: ANVIL_PORT
          value: "8545"
        - name: ANVIL_CHAIN_ID
          value: "31337"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: lenina-service
spec:
  selector:
    app: lenina
  ports:
  - name: api
    port: 8000
    targetPort: 8000
  - name: anvil-rpc
    port: 8545
    targetPort: 8545
  type: ClusterIP
```

### Apply to Cluster

```bash
kubectl apply -f k8s/deployment.yaml
```

### Access Service

```bash
# Port forward for local access
kubectl port-forward service/lenina-service 8000:8000 8545:8545

# Or expose via Ingress
```

---

## Environment Configuration

### All Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LENINA_PORT` | `8000` | Port for Lenina REST API |
| `ANVIL_PORT` | `8545` | Port for Anvil JSON-RPC |
| `ANVIL_CHAIN_ID` | `31337` | Chain ID for Anvil blockchain |
| `ANVIL_GAS_LIMIT` | `30000000` | Gas limit per block |
| `ANVIL_MNEMONIC` | (auto) | HD wallet mnemonic phrase |

### Using .env File

Create `.env` in project root:
```bash
LENINA_PORT=8000
ANVIL_PORT=8545
ANVIL_CHAIN_ID=31337
ANVIL_GAS_LIMIT=30000000
```

Load in Python (if needed):
```python
from dotenv import load_dotenv
load_dotenv()
```

### Docker Environment

In docker-compose.yml:
```yaml
environment:
  - LENINA_PORT=8000
  - ANVIL_PORT=8545
  - ANVIL_CHAIN_ID=31337
```

Or use `.env` file:
```yaml
env_file:
  - .env
```

---

## Monitoring and Health Checks

### Health Endpoint

```bash
curl $LENINA_BASE_URL/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-04T10:30:00.000Z"
}
```

### Status Endpoint

```bash
curl $LENINA_BASE_URL/anvil/status
```

**Response (running):**
```json
{
  "running": true,
  "pid": 12345,
  "uptime": 123.45,
  "port": 8545
}
```

### Docker Health Check

Dockerfile includes health check:
```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f $LENINA_BASE_URL/health || exit 1
```

### Prometheus Metrics (Future)

Consider adding Prometheus metrics endpoint for:
- Request count
- Response times
- Anvil uptime
- Memory usage

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker logs lenina
```

**Common issues:**
- Port already in use
- Insufficient memory
- Foundry installation failed

**Solution:**
```bash
# Check port usage
lsof -i :8000
lsof -i :8545

# Restart container
docker-compose down
docker-compose up -d
```

### Anvil Not Found

**Error:**
```
Error: Anvil not found. Ensure Foundry is installed.
```

**Solution:**
```bash
# Verify Foundry installation
which anvil

# Reinstall Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

### Port Already in Use

**Error:**
```
Error: Address already in use
```

**Solution:**
```bash
# Find process using port
lsof -i :8000

# Kill process
kill -9 <PID>

# Or change port
export LENINA_PORT=8001
```

### Slow Response Times

**Diagnosis:**
```bash
# Check response times
curl -w "@curl-format.txt" -o /dev/null -s $LENINA_BASE_URL/health
```

**Solutions:**
- Increase container resources
- Check system load
- Verify network connectivity

### Memory Issues

**Monitor:**
```bash
docker stats lenina
```

**Solutions:**
- Set memory limits in Docker
- Restart Anvil periodically
- Increase container memory limit

---

## Production Considerations

### Security

⚠️ **WARNING:** Lenina is designed for **local development only**.

- No authentication or authorization
- Private keys exposed via API
- No encryption of data in transit
- No rate limiting

**Do not deploy to production networks or expose to untrusted networks.**

### Resource Limits

**Docker:**
```yaml
deploy:
  resources:
    limits:
      cpus: '1'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 512M
```

**Kubernetes:**
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

### Logging

Enable detailed logging:
```bash
docker logs --tail 100 -f lenina
```

Configure log rotation in Docker:
```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

### Backup and Persistence

**Note:** Lenina does not persist state across restarts by design.

For contract persistence, consider:
- External database for contract addresses
- Periodic state snapshots
- Deployment transaction logs

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install Foundry
      uses: foundry-rs/foundry-toolchain@v1
    
    - name: Install dependencies
      run: pip install -r requirements.txt
    
    - name: Run tests
      run: pytest
    
    - name: Run typecheck
      run: mypy main.py --strict
    
    - name: Build Docker image
      run: docker build -t lenina:test .
    
    - name: Test Docker container
      run: |
        docker run -d --name lenina-test -p 8000:8000 lenina:test
        sleep 5
        curl $LENINA_BASE_URL/health
```

---

## Support

For issues and questions:
- Check the [README.md](../README.md)
- Review [API Documentation](./api.md)
- Study [Architecture](./architecture.md)
- Open a GitHub issue
