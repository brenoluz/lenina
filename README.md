# Lenina - Anvil RESTful Management

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Docker Pulls](https://img.shields.io/docker/pulls/brenoluz/lenina)](https://hub.docker.com/r/brenoluz/lenina)
[![Docker Image Version](https://img.shields.io/docker/v/brenoluz/lenina/latest)](https://hub.docker.com/r/brenoluz/lenina/tags)

Lenina is a Python-based RESTful API for managing Anvil (Foundry's local Ethereum blockchain). It provides programmatic control over Anvil instances including start, stop, restart operations, private key retrieval, contract deployment verification, and configuration inspection.

## Features

- 🚀 **Full Anvil Lifecycle Management** - Start, stop, and restart Anvil instances via REST API
- 🔑 **Private Key Access** - Retrieve all generated private keys and addresses programmatically
- 📋 **Automatic Contract Tracking** - Auto-detect contracts deployed via any method (RPC, Foundry, web3.py, etc.)
- ⚙️ **Configuration Exposure** - Get all Anvil configuration settings via API
- 🔄 **RPC Proxy** - Forward JSON-RPC requests to Anvil through the REST API
- 📝 **Real-time Logs** - Stream Anvil logs via SSE or retrieve recent entries
- 🐳 **Docker Ready** - Official Docker image available at `brenoluz/lenina`
- 📖 **Auto-Generated Docs** - OpenAPI documentation available at `/docs`

## Quick Start

### Using Docker (Recommended)

**Option 1: Pull from Docker Hub**

```bash
docker pull brenoluz/lenina:v0.1.0
docker run -d -p 8000:8000 -p 8545:8545 --name lenina brenoluz/lenina:v0.1.0
```

**Option 2: Use docker-compose**

```bash
docker-compose up -d
```

**Verify it's running:**

```bash
curl http://localhost:8000/health
```

**Start Anvil:**

```bash
curl -X POST http://localhost:8000/anvil/start
```

**Access API docs:** Open http://localhost:8000/docs in your browser

### Local Setup

**Prerequisites:**
- Python 3.10 or higher
- Foundry (for Anvil) - Install from [https://book.getfoundry.sh/](https://book.getfoundry.sh/)

1. **Install Foundry:**

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

2. **Clone and install dependencies:**

```bash
git clone <repository-url>
cd lenina
pip install -r requirements.txt
```

3. **Run Lenina:**

```bash
python main.py
```

4. **Start Anvil via API:**

```bash
curl -X POST http://localhost:8000/anvil/start
```

## API Endpoints

### Health Check

```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-04T10:30:00.000Z"
}
```

### Start Anvil

```http
POST /anvil/start
Content-Type: application/json

{
  "port": 8545,
  "chainId": 31337,
  "blockTime": 0,
  "gasLimit": 30000000,
  "mnemonic": "your optional mnemonic here"
}
```

**Response:**
```json
{
  "pid": 12345,
  "port": 8545,
  "chainId": 31337,
  "status": "running"
}
```

**Status Codes:**
- `200` - Success
- `400` - Anvil already running
- `500` - Failed to start (Anvil not found, etc.)

### Stop Anvil

```http
POST /anvil/stop
```

**Response:**
```json
{
  "status": "stopped",
  "message": "Anvil instance (PID 12345) has been stopped"
}
```

**Status Codes:**
- `200` - Success
- `400` - No Anvil instance running
- `500` - Failed to stop

### Restart Anvil

```http
POST /anvil/restart
Content-Type: application/json

{
  "port": 8545,
  "chainId": 31337
}
```

**Response:**
```json
{
  "pid": 12346,
  "port": 8545,
  "chainId": 31337,
  "status": "running",
  "message": "Anvil instance restarted successfully"
}
```

### Get Status

```http
GET /anvil/status
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

**Response (stopped):**
```json
{
  "running": false,
  "pid": null,
  "uptime": null,
  "port": null
}
```

### Get Private Keys

```http
GET /anvil/keys
```

**Response:**
```json
{
  "accounts": [
    {
      "address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
      "privateKey": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    },
    // ... 9 more accounts
  ],
  "mnemonic": "test test test test test test test test test test test junk"
}
```

**Status Codes:**
- `200` - Success
- `400` - No Anvil instance running
- `500` - Failed to retrieve keys

### Get Configuration

```http
GET /anvil/config
```

**Response:**
```json
{
  "ip": "127.0.0.1",
  "port": 8545,
  "chainId": 31337,
  "version": "0.1.0",
  "blockTime": 0,
  "gasLimit": 30000000,
  "mnemonic": "test test test test test test test test test test test junk"
}
```

### Check Contract

```http
GET /anvil/contract/0x5FbDB2315678afecb367f032d93F642f64180aa3
```

**Response (contract exists):**
```json
{
  "address": "0x5FbDB2315678afecb367f032d93F642f64180aa3",
  "bytecodeHash": "0xabc123...",
  "deploymentBlock": null,
  "bytecode": "0x6080604052..."
}
```

**Response (no contract):**
```json
{
  "detail": "No contract deployed at address 0x5FbDB2315678afecb367f032d93F642f64180aa3"
}
```

### List Contracts

```http
GET /anvil/contracts
```

**Response:**
```json
{
  "contracts": [
    {
      "address": "0x5FbDB2315678afecb367f032d93F642f64180aa3",
      "bytecodeHash": "0xabc123...",
      "deploymentBlock": 1,
      "abi": null
    }
  ]
}
```

### Proxy RPC Request

```http
POST /anvil/rpc
Content-Type: application/json

{
  "jsonrpc": "2.0",
  "method": "eth_blockNumber",
  "params": [],
  "id": 1
}
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": "0x1",
  "error": null,
  "id": 1
}
```

**Supported RPC Methods:**
- `eth_blockNumber` - Get current block number
- `eth_getBalance` - Get account balance
- `eth_sendTransaction` - Send transaction
- `eth_call` - Execute contract call
- `eth_getCode` - Get contract bytecode
- `eth_getLogs` - Get event logs
- And all other standard Ethereum JSON-RPC methods

### Get Anvil Logs

```http
GET /anvil/logs?lines=100&since=0&format=markdown
```

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lines` | integer | `100` | Number of recent lines (1-1000) |
| `since` | integer | `null` | Get logs after this sequence number |
| `format` | string | `markdown` | Output format: `markdown`, `json`, or `text` |

**Response:**
```json
{
  "lines": [
    {
      "line": "Listening on 127.0.0.1:8545",
      "timestamp": 1709547000.123,
      "sequence": 1
    }
  ],
  "totalLines": 50,
  "truncated": false,
  "format": "markdown"
}
```

### Stream Logs (Server-Sent Events)

```http
GET /anvil/logs/stream?since=0&format=text
```

**Description:** Real-time log streaming via SSE. Connection stays open while Anvil runs.

**Example:**
```bash
# Stream logs in terminal
curl -N http://localhost:8000/anvil/logs/stream

# Get logs after sequence 100
curl -N http://localhost:8000/anvil/logs/stream?since=100
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

### Docker Configuration

Edit `docker-compose.yml` to customize:

```yaml
services:
  lenina:
    ports:
      - "8000:8000"  # API port
      - "8545:8545"  # Anvil RPC port
    environment:
      - ANVIL_CHAIN_ID=31337
      - ANVIL_GAS_LIMIT=30000000
```

## Usage Examples

### Complete Workflow

```bash
# 1. Start Lenina (using Docker)
docker run -d -p 8000:8000 -p 8545:8545 --name lenina brenoluz/lenina:v0.1.0

# 2. Start Anvil
curl -X POST http://localhost:8000/anvil/start

# 3. Get status
curl http://localhost:8000/anvil/status

# 4. Get private keys
curl http://localhost:8000/anvil/keys

# 5. Send RPC request
curl -X POST http://localhost:8000/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# 6. Check contract deployment
curl http://localhost:8000/anvil/contract/0x5FbDB2315678afecb367f032d93F642f64180aa3

# 7. Get recent logs
curl http://localhost:8000/anvil/logs?lines=30

# 8. Stream logs
curl -N http://localhost:8000/anvil/logs/stream

# 9. Stop Anvil
curl -X POST http://localhost:8000/anvil/stop
```

### Using with Hardhat/Foundry

```javascript
// hardhat.config.js
module.exports = {
  networks: {
    lenina: {
      url: "http://localhost:8545",
      accounts: [
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        // Add more private keys from /anvil/keys endpoint
      ]
    }
  }
};
```

### Using with ethers.js

```javascript
const { ethers } = require("ethers");

// Get keys from Lenina
const response = await fetch("http://localhost:8000/anvil/keys");
const { accounts } = await response.json();

// Create provider and signer
const provider = new ethers.JsonRpcProvider("http://localhost:8545");
const signer = new ethers.Wallet(accounts[0].privateKey, provider);

// Deploy contract
const factory = new ethers.ContractFactory(abi, bytecode, signer);
const contract = await factory.deploy();
```

## Docker

### Pull from Docker Hub (Recommended)

```bash
docker pull brenoluz/lenina:v0.1.0
```

### Run Container

```bash
docker run -d \
  -p 8000:8000 \
  -p 8545:8545 \
  --name lenina \
  brenoluz/lenina:v0.1.0
```

### Build Image Locally

```bash
docker build -t lenina .
```

### Docker Compose

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f
```

## Development

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx pytest-cov

# Run tests
pytest

# Run with coverage
pytest --cov=main --cov-report=html
```

### Type Checking

```bash
# Install mypy
pip install mypy

# Run type check
mypy main.py --strict
```

## Project Structure

```
lenina/
├── main.py              # Main application
├── requirements.txt     # Python dependencies
├── pyproject.toml      # Python project configuration
├── Dockerfile          # Docker image definition
├── docker-compose.yml  # Docker Compose configuration
├── docs/               # Detailed documentation
│   ├── api.md         # API reference
│   ├── architecture.md # System architecture
│   └── deployment.md   # Deployment guide
└── tests/              # Integration tests
    └── test_main.py
```

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
                     │   Process    │
                     │  Management  │
                     └──────────────┘
                           │
                           ▼
                     ┌──────────────┐
                     │  Log Buffer  │
                     │  (circular)  │
                     └──────────────┘
```

- **FastAPI** handles REST endpoints and OpenAPI documentation
- **subprocess** manages Anvil process lifecycle
- **httpx** proxies RPC requests to Anvil
- **Pydantic** validates all request/response data

## Troubleshooting

### Anvil Not Found

```
Error: Anvil not found. Ensure Foundry is installed.
```

**Solution:** Install Foundry:
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

### Port Already in Use

```
Error: Address already in use
```

**Solution:** Change the port in configuration:
```bash
export ANVIL_PORT=8546
export LENINA_PORT=8001
```

### Container Fails to Start

**Solution:** Check logs:
```bash
docker-compose logs lenina
```

### Swagger UI Shows "string" for Mnemonic

```
Error: the word `string` is invalid
```

**Cause:** Swagger UI auto-fills string fields with `"string"` placeholder, which Anvil rejects.

**Solution:** Delete the mnemonic value in Swagger UI (leave empty) or use a valid 12-24 word mnemonic phrase.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Additional Documentation

For more detailed documentation, see the [`/docs`](./docs/) folder:

- [API Reference](./docs/api.md) - Complete API documentation
- [Architecture](./docs/architecture.md) - System design and architecture
- [Deployment](./docs/deployment.md) - Production deployment guide

## AI Skills

Lenina includes a skill for AI coding assistants that provides comprehensive curl-based usage examples.

### Installation

#### Claude Desktop (claude.ai)

1. Open Claude Desktop settings
2. Navigate to the Skills section
3. Click "Add Skill" and select the `skills/lenina` folder from this repository

Alternatively, copy the `skills/lenina` folder to your skills directory:

- **macOS:** `~/Library/Application Support/Claude/skills/lenina`
- **Linux:** `~/.config/claude/skills/lenina`
- **Windows:** `%APPDATA%\Claude\skills\lenina`

#### OpenCode

OpenCode automatically loads skills from the `.claude/skills/` folder in your project.

Copy the skill to your project:

```bash
mkdir -p .claude/skills
cp -r skills/lenina .claude/skills/
```

Or create a symlink:

```bash
mkdir -p .claude/skills
ln -s ../skills/lenina .claude/skills/lenina
```

#### GitHub Copilot (Codex)

For GitHub Copilot users using the Copilot CLI or VS Code extension:

1. Create a `.github/copilot-instructions.md` file in your project
2. Add the following content:

```markdown
# Lenina Project - Curl Usage

This project includes a comprehensive skill for using Lenina with curl.
Reference: `skills/lenina/SKILL.md`

When asked about curl commands, API usage, or HTTP requests for Lenina,
provide examples based on the workflow patterns in the skill file.
```

3. Copilot will use these instructions when providing assistance

#### Cursor

1. Open Cursor settings (⌘+, or Ctrl+,)
2. Go to the "Features" tab
3. Scroll to "Skills" or "AI Instructions"
4. Click "Add Skill" and point to the `skills/lenina` folder

#### Generic Setup (Any AI Assistant)

If your AI assistant supports custom skills or instructions, copy the `skills/lenina/SKILL.md` file to your assistant's skill/instruction directory.

### Usage

Once installed, you can ask your AI assistant questions like:

- "How do I start Anvil using curl?"
- "Show me how to send ETH using the Lenina API"
- "What's the curl command to get my private keys?"
- "How do I deploy a contract using curl requests?"

The skill provides workflow-style examples for all Lenina API operations.
