# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - Initial Release

### 🚀 Added

- **Anvil Lifecycle Management**
  - `POST /anvil/start` - Start Anvil instance with optional configuration
  - `POST /anvil/stop` - Stop running Anvil instance
  - `POST /anvil/restart` - Restart Anvil with preserved or new configuration

- **Information Endpoints**
  - `GET /anvil/status` - Get Anvil running status (PID, uptime, port)
  - `GET /anvil/keys` - Retrieve all private keys and addresses
  - `GET /anvil/config` - Get current Anvil configuration
  - `GET /health` - Health check endpoint

- **Contract Management**
  - `GET /anvil/contracts` - List all deployed contracts (auto-tracked)
  - `GET /anvil/contract/{address}` - Check if contract exists at address

- **Log Management**
  - `GET /anvil/logs` - Retrieve recent log lines with filtering
  - `GET /anvil/logs/stream` - Real-time log streaming via SSE

- **RPC Proxy**
  - `POST /anvil/rpc` - Forward JSON-RPC requests to Anvil

- **Docker Support**
  - Dockerfile with Python 3.11 and Foundry
  - docker-compose.yml for easy deployment
  - Health checks configured
  - External access support via LAN IP detection

- **Documentation**
  - Auto-generated OpenAPI/Swagger docs at `/docs`
  - Complete API reference in `docs/api.md`
  - Architecture and deployment guides

### 🔧 Technical

- FastAPI for REST API framework
- Pydantic for request/response validation
- subprocess for Anvil process management
- httpx for RPC proxying
- Circular buffer for log storage (max 1000 lines)
- Automatic contract deployment tracking via stdout parsing

### 📦 Configuration

Supports environment variables:
- `LENINA_PORT` - API port (default: 8000)
- `ANVIL_PORT` - Anvil RPC port (default: 8545)
- `ANVIL_CHAIN_ID` - Chain ID (default: 31337)
- `ANVIL_GAS_LIMIT` - Gas limit (default: 30000000)
- `ANVIL_MNEMONIC` - HD wallet mnemonic (optional)
- `HOST_IP` - Override auto-detected LAN IP

---

## Versioning

This project uses Git tags for versioning. Versions are automatically derived from tags using `git describe`.

To release a new version:
```bash
git tag -a v0.2.0 -m "Release description"
git push origin v0.2.0
```

[Unreleased]: https://github.com/your-org/lenina/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/your-org/lenina/releases/tag/v0.1.0
