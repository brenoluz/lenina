# Lenina - Anvil RESTful Management API

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker Pulls](https://img.shields.io/docker/pulls/brenoluz/lenina)](https://hub.docker.com/r/brenoluz/lenina)
[![Docker Image Version](https://img.shields.io/docker/v/brenoluz/lenina/latest)](https://hub.docker.com/r/brenoluz/lenina/tags)

RESTful API for managing Anvil (Foundry's local Ethereum blockchain) with full lifecycle control.

## Features

- 🚀 **Full Anvil Lifecycle** - Start, stop, and restart Anvil instances via REST API
- 🔑 **Private Key Access** - Retrieve all generated accounts with addresses and private keys
- 📋 **Contract Tracking** - Automatic detection of deployed contracts (via RPC, Foundry, web3.py, etc.)
- ⚙️ **Configuration Exposure** - Get all Anvil settings including port, chainId, gasLimit, mnemonic
- 🔄 **RPC Proxy** - Forward JSON-RPC requests through the REST API
- 📝 **Real-time Logs** - Stream Anvil logs via SSE or retrieve recent entries
- 🐳 **Docker Ready** - Fully containerized with docker-compose support

## Quick Start

### Using Docker Run

```bash
docker run -d -p 8000:8000 -p 8545:8545 --name lenina brenoluz/lenina:v0.1.0
```

### Using Docker Compose

```yaml
version: '3.8'
services:
  lenina:
    image: brenoluz/lenina:v0.1.0
    ports:
      - "8000:8000"
      - "8545:8545"
    environment:
      - ANVIL_CHAIN_ID=31337
      - ANVIL_GAS_LIMIT=30000000
    restart: unless-stopped
```

```bash
docker-compose up -d
```

### Verify It's Running

```bash
curl http://localhost:8000/health
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check endpoint |
| `POST` | `/anvil/start` | Start Anvil instance |
| `POST` | `/anvil/stop` | Stop Anvil instance |
| `POST` | `/anvil/restart` | Restart Anvil instance |
| `GET` | `/anvil/status` | Get Anvil running status |
| `GET` | `/anvil/keys` | Get private keys and addresses |
| `GET` | `/anvil/config` | Get Anvil configuration |
| `GET` | `/anvil/contract/{address}` | Check contract at address |
| `GET` | `/anvil/logs` | Get recent log lines |
| `GET` | `/anvil/logs/stream` | Stream logs via SSE |
| `POST` | `/anvil/rpc` | Proxy JSON-RPC requests |

## Usage Examples

### Start Anvil

```bash
curl -X POST http://localhost:8000/anvil/start \
  -H "Content-Type: application/json" \
  -d '{
    "port": 8545,
    "chainId": 31337,
    "blockTime": 0,
    "gasLimit": 30000000
  }'
```

### Get Private Keys

```bash
curl http://localhost:8000/anvil/keys
```

### Stream Logs

```bash
curl -N http://localhost:8000/anvil/logs/stream
```

### Proxy RPC Request

```bash
curl -X POST http://localhost:8000/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "eth_blockNumber",
    "params": [],
    "id": 1
  }'
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LENINA_PORT` | Lenina API port | `8000` |
| `ANVIL_PORT` | Anvil RPC port | `8545` |
| `ANVIL_CHAIN_ID` | Chain ID for Anvil | `31337` |
| `ANVIL_GAS_LIMIT` | Gas limit per block | `30000000` |
| `ANVIL_MNEMONIC` | HD wallet mnemonic | (auto-generated) |
| `HOST_IP` | Override auto-detected LAN IP | (auto-detect) |

### Example with Custom Configuration

```bash
docker run -d \
  -p 8000:8000 -p 8545:8545 \
  -e ANVIL_CHAIN_ID=1337 \
  -e ANVIL_MNEMONIC="your mnemonic here" \
  --name lenina \
  brenoluz/lenina:v0.1.0
```

## Documentation

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **GitHub:** https://github.com/brenoluz/lenina
- **API Reference:** https://github.com/brenoluz/lenina/blob/main/docs/api.md
- **Changelog:** https://github.com/brenoluz/lenina/blob/main/CHANGELOG.md

## Ports

| Port | Service | Description |
|------|---------|-------------|
| `8000` | Lenina API | REST API and Swagger UI |
| `8545` | Anvil RPC | Ethereum JSON-RPC endpoint |

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────┐
│   Client    │────▶│   Lenina     │────▶│  Anvil   │
│  (REST/HTTP)│     │  (FastAPI)   │     │(Foundry) │
└─────────────┘     └──────────────┘     └──────────┘
                           │                   │
                           │◀─────stdout───────│
                           ▼             (log capture)
                     ┌──────────────┐
                     │  Log Buffer  │
                     │  (circular)  │
                     └──────────────┘
```

## Development

### Build from Source

```bash
git clone https://github.com/brenoluz/lenina.git
cd lenina
docker build -t lenina .
```

### Run Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run server
python main.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/brenoluz/lenina/blob/main/LICENSE) file for details.

## Support

- **Issues:** https://github.com/brenoluz/lenina/issues
- **Discussions:** https://github.com/brenoluz/lenina/discussions

---

**Last Updated:** March 2026
**Version:** v0.1.0
