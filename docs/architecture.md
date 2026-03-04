# Lenina Architecture

System architecture and design documentation for Lenina.

## Overview

Lenina is a RESTful API wrapper around Anvil (Foundry's local Ethereum blockchain). It provides programmatic control over Anvil's lifecycle and exposes Anvil's capabilities through HTTP endpoints.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Layer                            │
│  (cURL, Postman, Hardhat, ethers.js, web3.py, etc.)            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/REST
┌─────────────────────────────────────────────────────────────────┐
│                      Lenina API Layer                           │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   FastAPI Application                     │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐  │  │
│  │  │ /anvil/ │ │ /anvil/ │ │ /anvil/ │ │ /anvil/contract │  │  │
│  │  │ /start  │ │ /stop   │ │ /status │ │ /{address}      │  │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘  │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐  │  │
│  │  │ /anvil/ │ │ /anvil/ │ │ /anvil/ │ │      /health    │  │  │
│  │  │ /keys   │ │ /config │ │  /rpc   │ │                 │  │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│         ┌────────────────────┼────────────────────┐             │
│         ▼                    ▼                    ▼             │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐       │
│  │   Process   │     │   State     │     │    HTTP     │       │
│  │  Lifecycle  │     │  Management │     │   Client    │       │
│  │  Manager    │     │  (Globals)  │     │  (httpx)    │       │
│  └─────────────┘     └─────────────┘     └─────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
                    ▼                   ▼
        ┌─────────────────┐   ┌─────────────────┐
        │  subprocess     │   │  JSON-RPC Proxy │
        │  (Popen)        │   │  (HTTP POST)    │
        └─────────────────┘   └─────────────────┘
                    │                   │
                    ▼                   ▼
        ┌─────────────────────────────────────────┐
        │           Anvil (Foundry)               │
        │  - Ethereum JSON-RPC on port 8545       │
        │  - Pre-funded test accounts             │
        │  - Deterministic private keys           │
        └─────────────────────────────────────────┘
```

## Components

### 1. FastAPI Application

**File:** `main.py`

The core of Lenina is a FastAPI application that provides:

- **RESTful endpoints** for all Anvil operations
- **Automatic OpenAPI documentation** at `/docs`
- **Request/Response validation** using Pydantic models
- **Async support** for non-blocking I/O operations

**Key Features:**
- Type-safe request/response models
- Automatic JSON serialization
- Built-in CORS support for browser-based tools
- Exception handlers for consistent error responses

### 2. Process Lifecycle Manager

**Purpose:** Manage the Anvil subprocess lifecycle

**Implementation:**
```python
import subprocess
import os
import signal

# Start Anvil
anvil_process = subprocess.Popen(
    ["anvil", "--port", "8545", "--chain-id", "31337"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    preexec_fn=os.setsid  # Create new process group
)

# Stop Anvil (graceful)
os.killpg(os.getpgid(anvil_process.pid), signal.SIGTERM)

# Stop Anvil (force)
os.killpg(os.getpgid(anvil_process.pid), signal.SIGKILL)
```

**Process Group Management:**
- Uses `os.setsid` to create a new process group
- Enables killing all child processes together
- Prevents orphaned processes on shutdown

### 3. State Management

**Global State Variables:**

| Variable | Type | Purpose |
|----------|------|---------|
| `anvil_process` | `subprocess.Popen` | Reference to Anvil process |
| `anvil_start_time` | `float` | Timestamp when Anvil started |
| `anvil_config` | `Dict[str, Any]` | Current Anvil configuration |
| `anvil_accounts` | `List[PrivateKeyInfo]` | Parsed accounts from Anvil output |
| `deployed_contracts` | `List[ContractInfo]` | Tracked contract deployments |

**State Lifecycle:**
- **Start:** Populate all state from Anvil output
- **Stop:** Clear all state
- **Restart:** Clear state, then repopulate

### 4. Output Parser

**Purpose:** Parse Anvil's startup output to extract private keys and addresses

**Anvil Output Format:**
```
Available Accounts
==================
(0) 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 (10000 ETH)
(1) 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 (10000 ETH)
...

Private Keys
==================
(0) 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
(1) 0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d
...
```

**Parsing Logic:**
```python
import re

# Parse addresses
address_pattern = r"\((\d+)\)\s+(0x[0-9a-fA-F]+)\s+\("
addresses = re.findall(address_pattern, output)

# Parse private keys
key_pattern = r"\((\d+)\)\s+(0x[0-9a-fA-F]+)$"
private_keys = re.findall(key_pattern, output, re.MULTILINE)

# Match by index
for i in range(min(len(addresses), len(private_keys))):
    accounts.append({
        "address": addresses[i][1],
        "privateKey": private_keys[i][1]
    })
```

### 5. RPC Proxy

**Purpose:** Forward JSON-RPC requests to Anvil

**Implementation:**
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        f"http://127.0.0.1:{port}",
        json={
            "jsonrpc": "2.0",
            "method": request.method,
            "params": request.params or [],
            "id": request.id
        },
        timeout=30.0
    )
    return response.json()
```

**Features:**
- Async HTTP client for non-blocking I/O
- 30-second timeout for long-running RPC calls
- Preserves JSON-RPC 2.0 format
- Returns Anvil's response directly to client

### 6. Contract Verification

**Purpose:** Check if a contract exists at an address

**Implementation:**
```python
# Use eth_getCode RPC method
response = await client.post(
    rpc_url,
    json={
        "jsonrpc": "2.0",
        "method": "eth_getCode",
        "params": [address, "latest"],
        "id": 1
    }
)

bytecode = response.json().get("result", "0x")

# Empty bytecode means no contract
if bytecode == "0x":
    raise HTTPException(status_code=404, detail="No contract")

# Calculate SHA256 hash for identification
bytecode_hash = sha256(bytecode)
```

## Data Flow

### Start Anvil Flow

```
Client Request
     │
     ▼
POST /anvil/start
     │
     ▼
[FastAPI] Validate config
     │
     ▼
[subprocess.Popen] Start Anvil
     │
     ▼
[Parse Output] Extract keys/addresses
     │
     ▼
[State] Store config, accounts, process
     │
     ▼
Return {pid, port, chainId, status}
```

### RPC Proxy Flow

```
Client Request (JSON-RPC)
     │
     ▼
POST /anvil/rpc
     │
     ▼
[FastAPI] Validate request
     │
     ▼
[httpx] Forward to Anvil:8545
     │
     ▼
[Anvil] Process RPC method
     │
     ▼
[httpx] Return response
     │
     ▼
Return JSON-RPC response to client
```

### Stop Anvil Flow

```
Client Request
     │
     ▼
POST /anvil/stop
     │
     ▼
[FastAPI] Validate Anvil is running
     │
     ▼
[os.killpg] Send SIGTERM to process group
     │
     ▼
[process.wait] Wait for exit (5s timeout)
     │
     ▼
[State] Clear all global state
     │
     ▼
Return {status, message}
```

## Design Patterns

### 1. Global State Pattern

Used for managing Anvil lifecycle state across requests:

```python
# Module-level state
anvil_process: Optional[subprocess.Popen] = None
anvil_config: Optional[Dict[str, Any]] = None

# Access in endpoints
@app.post("/anvil/stop")
async def stop_anvil():
    global anvil_process
    if anvil_process is None:
        raise HTTPException(400, "Not running")
    # ...
```

### 2. Pydantic Models

Used for type-safe request/response validation:

```python
class AnvilConfig(BaseModel):
    port: Optional[int] = 8545
    chainId: Optional[int] = 31337
    blockTime: Optional[int] = 0

class AnvilStartResponse(BaseModel):
    pid: int
    port: int
    chainId: int
    status: str
```

### 3. Process Group Management

Used for clean subprocess termination:

```python
# Unix: Create process group
subprocess.Popen(
    cmd,
    preexec_fn=os.setsid
)

# Unix: Kill process group
os.killpg(os.getpgid(pid), signal.SIGTERM)
```

## Security Considerations

### Local Development Only

- **No authentication** - Assumes trusted local network
- **No rate limiting** - No DoS protection
- **No CORS restrictions** - All origins allowed

### Private Key Exposure

- Private keys are exposed via API by design
- Only safe in isolated development environments
- **Never** deploy to production networks

### Process Isolation

- Anvil runs in a separate process group
- Graceful shutdown prevents orphaned processes
- No direct file system access beyond Anvil's defaults

## Performance Characteristics

### Startup Time

- Anvil startup: ~500ms - 2s
- API endpoint response: <10ms (excluding Anvil start)

### Memory Usage

- Lenina process: ~50MB
- Anvil process: ~200-500MB (varies with state)

### Concurrency

- Single Anvil instance per Lenina instance
- Multiple concurrent RPC requests supported
- Async I/O for non-blocking operations

## Extensibility

### Adding New Endpoints

1. Define Pydantic models for request/response
2. Create FastAPI endpoint decorator
3. Implement business logic
4. Add error handling
5. Update OpenAPI docs (automatic)

### Adding Configuration Options

1. Add field to `AnvilConfig` model
2. Update environment variable handling
3. Pass to Anvil command line
4. Store in `anvil_config` state

## Testing Strategy

### Unit Tests

- Test individual endpoint handlers
- Mock subprocess and httpx
- Verify request/response models

### Integration Tests

- Start real Anvil instance
- Test full lifecycle: start → operations → stop
- Verify RPC proxy functionality

### End-to-End Tests

- Docker container build and run
- Complete workflow from external client
- Performance and stress testing
