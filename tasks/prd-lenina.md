# PRD: Lenina - Anvil RESTful Management

## Introduction

Lenina is a Python-based RESTful API for managing Anvil (Foundry's local Ethereum blockchain). It provides programmatic control over Anvil instances including start, stop, restart operations, private key retrieval, contract deployment verification, and configuration inspection. The service is designed to be containerized and accessible via HTTP endpoints for developer productivity.

## Goals

- Provide RESTful API endpoints for all Anvil lifecycle operations
- Enable contract deployment tracking and verification
- Expose Anvil configuration via API (IP, port, version, etc.)
- Support Docker deployment for consistent environments
- No authentication overhead for local development workflows
- Full-featured API including Anvil RPC proxy capabilities

## User Stories

### US-001: Start Anvil instance via API
**Description:** As a contract developer, I want to start an Anvil instance via REST API so I can spin up a local blockchain on demand.

**Acceptance Criteria:**
- [ ] POST `/anvil/start` endpoint accepts optional configuration (port, chainId, blockTime, etc.)
- [ ] Returns 200 with Anvil process ID and connection details on success
- [ ] Returns 400 if Anvil is already running
- [ ] Returns 500 if Anvil fails to start
- [ ] Typecheck passes

### US-002: Stop Anvil instance via API
**Description:** As a contract developer, I want to stop a running Anvil instance via REST API so I can cleanly shut down the blockchain.

**Acceptance Criteria:**
- [ ] POST `/anvil/stop` endpoint stops the running Anvil process
- [ ] Returns 200 with confirmation on success
- [ ] Returns 400 if no Anvil instance is running
- [ ] Gracefully terminates the process
- [ ] Typecheck passes

### US-003: Restart Anvil instance via API
**Description:** As a contract developer, I want to restart Anvil via REST API so I can reset the blockchain state without manual intervention.

**Acceptance Criteria:**
- [ ] POST `/anvil/restart` endpoint stops and starts Anvil
- [ ] Preserves configuration from previous run or accepts new config
- [ ] Returns 200 with new process details on success
- [ ] Typecheck passes

### US-004: Get private keys via API
**Description:** As a contract developer, I want to retrieve Anvil's generated private keys via REST API so I can use them for testing and deployment.

**Acceptance Criteria:**
- [ ] GET `/anvil/keys` endpoint returns list of private keys and addresses
- [ ] Returns 400 if Anvil is not running
- [ ] Response includes at least 10 default accounts with private keys
- [ ] Typecheck passes

### US-005: Check contract deployment status
**Description:** As a contract developer, I want to verify if a contract was deployed at a specific address via REST API so I can validate my deployment scripts.

**Acceptance Criteria:**
- [ ] GET `/anvil/contract/:address` endpoint checks if contract exists at address
- [ ] Returns 200 with contract info (bytecode, ABI if available) if deployed
- [ ] Returns 404 if no contract at address
- [ ] Returns 400 if Anvil is not running
- [ ] Typecheck passes

### US-006: Get Anvil configuration
**Description:** As a contract developer, I want to see all Anvil configuration via REST API so I know the current blockchain settings.

**Acceptance Criteria:**
- [ ] GET `/anvil/config` endpoint returns full configuration
- [ ] Response includes: IP, port, chainId, version, blockTime, gasLimit, etc.
- [ ] Returns 400 if Anvil is not running
- [ ] Typecheck passes

### US-007: Get Anvil status
**Description:** As a contract developer, I want to check if Anvil is running via REST API so I know the current state before making other calls.

**Acceptance Criteria:**
- [ ] GET `/anvil/status` endpoint returns running state
- [ ] Response includes: running (boolean), pid, uptime, port
- [ ] Returns 200 regardless of running state
- [ ] Typecheck passes

### US-008: Proxy Anvil RPC requests
**Description:** As a contract developer, I want to send RPC requests through Lenina so I can interact with the blockchain via the REST API.

**Acceptance Criteria:**
- [ ] POST `/anvil/rpc` endpoint accepts JSON-RPC requests
- [ ] Forwards requests to Anvil's JSON-RPC endpoint
- [ ] Returns Anvil's response to client
- [ ] Supports standard Ethereum JSON-RPC methods (eth_sendTransaction, eth_call, etc.)
- [ ] Returns 400 if Anvil is not running
- [ ] Typecheck passes

### US-009: Docker containerization
**Description:** As a contract developer, I want to run Lenina in Docker so I have a consistent environment across machines.

**Acceptance Criteria:**
- [ ] Dockerfile created with Python runtime
- [ ] Anvil (Foundry) installed in container
- [ ] Container exposes configurable port (default 8000)
- [ ] docker-compose.yml for easy local development
- [ ] Container health check endpoint
- [ ] Typecheck passes

### US-010: List deployed contracts
**Description:** As a contract developer, I want to see all deployed contracts via REST API so I can track my deployment history.

**Acceptance Criteria:**
- [ ] GET `/anvil/contracts` endpoint returns list of all deployed contracts
- [ ] Response includes: address, deploymentBlock, bytecodeHash for each
- [ ] Contracts tracked from session start or persistence if configured
- [ ] Returns 400 if Anvil is not running
- [ ] Typecheck passes

### US-011: Project documentation
**Description:** As a developer, I want comprehensive project documentation so I can understand how to use and deploy Lenina.

**Acceptance Criteria:**
- [ ] README.md created in project root with:
  - Project overview and features
  - Quick start guide (Docker and local setup)
  - API endpoints reference with examples
  - Configuration options (environment variables)
- [ ] `/docs` folder created with detailed documentation
- [ ] README.md links to `/docs` for extended documentation
- [ ] Docker setup instructions included
- [ ] API usage examples for all endpoints

### US-012: Integration tests for all endpoints
**Description:** As a developer, I want comprehensive integration tests so I can verify all API endpoints work correctly and catch regressions.

**Acceptance Criteria:**
- [ ] Test suite created using pytest with async support
- [ ] Tests for `/anvil/start` endpoint (success, already running, failure cases)
- [ ] Tests for `/anvil/stop` endpoint (success, not running cases)
- [ ] Tests for `/anvil/restart` endpoint (with/without config changes)
- [ ] Tests for `/anvil/keys` endpoint (returns 10+ accounts, not running case)
- [ ] Tests for `/anvil/contract/:address` endpoint (contract exists, not exists, not running)
- [ ] Tests for `/anvil/config` endpoint (returns all config fields, not running)
- [ ] Tests for `/anvil/status` endpoint (running and not running states)
- [ ] Tests for `/anvil/rpc` endpoint (proxy requests, not running)
- [ ] Tests for `/anvil/contracts` endpoint (list contracts, not running)
- [ ] Tests for `/health` endpoint
- [ ] Lifecycle integration test (start → status → keys → rpc → stop flow)
- [ ] Docker container test (build and run integration tests in container)
- [ ] All tests pass with >90% code coverage
- [ ] Typecheck passes

## Functional Requirements

- FR-1: Implement Flask/FastAPI REST server in Python
- FR-2: Manage Anvil process lifecycle (start/stop/restart)
- FR-3: Parse and expose Anvil's private keys from startup output
- FR-4: Track deployed contracts via RPC event listening or state polling
- FR-5: Expose Anvil configuration via config endpoint
- FR-6: Proxy JSON-RPC requests to Anvil
- FR-7: Build Docker image with Foundry/Anvil pre-installed
- FR-8: Implement health check endpoint at GET `/health`
- FR-9: Support configuration via environment variables
- FR-10: Return proper HTTP status codes (200, 400, 404, 500)
- FR-11: Create comprehensive README.md and /docs documentation
- FR-12: Comprehensive integration test suite with pytest

## Non-Goals

- No user authentication or authorization (local dev only)
- No persistent storage of contracts across restarts (unless explicitly configured)
- No support for multiple simultaneous Anvil instances
- No WebSocket support for RPC subscriptions
- No GUI or web interface
- No integration with remote testnets or mainnet

## Design Considerations

- Use FastAPI for automatic OpenAPI documentation
- Anvil process managed via Python subprocess module
- Contract tracking via eth_getLogs or deployment transaction monitoring
- Configuration stored in memory, optionally persisted to JSON
- Docker image based on Python slim image with Foundry added

## Technical Considerations

- Python 3.10+ required
- Foundry/Anvil must be installed in Docker image
- Default port 8000 for Lenina API, default 8545 for Anvil RPC
- Graceful shutdown handling for Anvil process
- Environment variables for all configurable options:
  - `LENINA_PORT`: API port (default 8000)
  - `ANVIL_PORT`: Anvil RPC port (default 8545)
  - `ANVIL_CHAIN_ID`: Chain ID (default 31337)
  - `ANVIL_MNEMONIC`: HD wallet mnemonic (optional)

## Success Metrics

- All REST endpoints respond in under 100ms (excluding Anvil start time)
- Anvil starts within 2 seconds
- Zero manual intervention needed for start/stop/restart cycles
- Docker container builds and runs without errors
- OpenAPI docs available at `/docs` endpoint
- README.md available in project root linking to /docs folder
- Integration test suite passes with >90% coverage

## Open Questions

- Should contract deployments be persisted across Anvil restarts?
- Should we support custom Anvil forks (mainnet/other chain forking)?
- Should we add rate limiting to RPC proxy endpoint?
- Should we support multiple Anvil instances with instance IDs?
