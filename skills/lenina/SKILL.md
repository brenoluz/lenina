---
name: lenina
description: How to use the Lenina project (Anvil REST API management) using curl commands. Make sure to use this skill whenever the user mentions curl, HTTP requests, REST API, or wants to interact with Lenina/Anvil programmatically without SDKs, even if they don't explicitly mention "curl commands."
---

# Lenina: Using Lenina with curl

This skill provides complete workflow-style guidance for using the Lenina REST API with curl commands. Designed for users familiar with curl but new to blockchain/Anvil concepts.

## Quick Reference

**Base URL:** `http://localhost:8000` (default Lenina port)

**Anvil RPC URL:** `http://localhost:8545` (default Anvil port, exposed by Lenina)

---

## Workflow 1: Getting Started

### Step 1: Check if Lenina is running

```bash
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-14T10:30:00.000Z"
}
```

**If you get an error:** Lenina is not running. Start it with:
```bash
python main.py
# Or use Docker: docker-compose up -d
```

### Step 2: Start Anvil (the local blockchain)

**What is Anvil?** Anvil is a local Ethereum blockchain used for development and testing. It's like a sandbox blockchain that runs on your computer.

```bash
curl -X POST http://localhost:8000/anvil/start
```

**Expected response:**
```json
{
  "pid": 12345,
  "port": 8545,
  "chainId": 31337,
  "status": "running"
}
```

**What these fields mean:**
- `pid`: Process ID of the Anvil instance
- `port`: The RPC port (8545 is the standard development port)
- `chainId`: 31337 is the default local development chain ID
- `status`: "running" means it's ready to use

### Step 3: Verify Anvil is running

```bash
curl http://localhost:8000/anvil/status
```

**Response:**
```json
{
  "running": true,
  "pid": 12345,
  "uptime": 45.67,
  "port": 8545
}
```

---

## Workflow 2: Start Anvil with Custom Configuration

### Start with custom chain ID and port

```bash
curl -X POST http://localhost:8000/anvil/start \
  -H "Content-Type: application/json" \
  -d '{
    "port": 8546,
    "chainId": 1337,
    "blockTime": 5,
    "gasLimit": 20000000
  }'
```

**Configuration options:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `port` | integer | `8545` | Anvil RPC port |
| `chainId` | integer | `31337` | Chain ID (like a network identifier) |
| `blockTime` | integer | `0` | Seconds between blocks (0 = auto-mine on transaction) |
| `gasLimit` | integer | `30000000` | Maximum gas per block |
| `mnemonic` | string | (auto) | Wallet seed phrase for deterministic addresses |

### Start with a specific mnemonic (for consistent addresses)

```bash
curl -X POST http://localhost:8000/anvil/start \
  -H "Content-Type: application/json" \
  -d '{
    "mnemonic": "my secure mnemonic phrase here"
  }'
```

**Why use a mnemonic?** Using the same mnemonic always generates the same wallet addresses and private keys. Useful for reproducible testing.

---

## Workflow 3: Get Private Keys and Addresses

### Retrieve all generated accounts

```bash
curl http://localhost:8000/anvil/keys
```

**Response:**
```json
{
  "accounts": [
    {
      "address": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
      "privateKey": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    },
    {
      "address": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
      "privateKey": "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
    }
  ],
  "mnemonic": "test test test test test test test test test test test junk"
}
```

**What you get:**
- 10 pre-funded test accounts (by default, each with 10,000 ETH)
- **`address`**: The public Ethereum address (safe to share)
- **`privateKey`**: The secret key (NEVER share this - anyone with it controls the account)
- **`mnemonic`**: The seed phrase that generates all accounts

**Security note:** These are TEST accounts with fake ETH on a local blockchain. Never use these keys on mainnet!

---

## Workflow 4: Get Current Configuration

### Check Anvil settings

```bash
curl http://localhost:8000/anvil/config
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

---

## Workflow 5: Stop and Restart Anvil

### Stop Anvil

```bash
curl -X POST http://localhost:8000/anvil/stop
```

**Response:**
```json
{
  "status": "stopped",
  "message": "Anvil instance (PID 12345) has been stopped"
}
```

### Restart with new configuration

```bash
curl -X POST http://localhost:8000/anvil/restart \
  -H "Content-Type: application/json" \
  -d '{
    "chainId": 1337,
    "port": 8546
  }'
```

**Note:** If you don't provide configuration, the previous settings are preserved.

---

## Workflow 6: Send Ethereum JSON-RPC Requests

**What is JSON-RPC?** JSON-RPC is the standard protocol for talking to Ethereum nodes. You use it to query the blockchain, send transactions, and interact with smart contracts.

### Get current block number

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

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": "0x1",
  "id": 1
}
```

**Note:** `0x1` is hexadecimal for 1 (block numbers are returned in hex).

### Get account balance

```bash
curl -X POST http://localhost:8000/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "eth_getBalance",
    "params": ["0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266", "latest"],
    "id": 1
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": "0x3635c9adc5dea00000",
  "id": 1
}
```

**Convert hex to ETH:** `0x3635c9adc5dea00000` = 10,000 ETH (in wei)

### Get accounts list

```bash
curl -X POST http://localhost:8000/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "eth_accounts",
    "params": [],
    "id": 1
  }'
```

### Send ETH between accounts

```bash
curl -X POST http://localhost:8000/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "eth_sendTransaction",
    "params": [{
      "from": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
      "to": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
      "value": "0x16345785d8a0000"
    }],
    "id": 1
  }'
```

**Response:**
```json
{
  "jsonrpc": "2.0",
  "result": "0xabc123...",
  "id": 1
}
```

**Result:** Transaction hash (use `eth_getTransactionReceipt` to check status)

### Common RPC methods reference

| Method | Description | Example params |
|--------|-------------|----------------|
| `eth_blockNumber` | Get current block | `[]` |
| `eth_getBalance` | Get account balance | `["0xAddress", "latest"]` |
| `eth_accounts` | List available accounts | `[]` |
| `eth_sendTransaction` | Send transaction | `[{from, to, value}]` |
| `eth_call` | Read-only contract call | `[{to, data}, "latest"]` |
| `eth_getCode` | Get contract bytecode | `["0xAddress", "latest"]` |
| `eth_getLogs` | Get event logs | `[{address, topics}]` |
| `eth_gasPrice` | Get current gas price | `[]` |
| `eth_estimateGas` | Estimate gas for tx | `[{from, to, data}]` |

---

## Workflow 7: Check Deployed Contracts

### List all deployed contracts

```bash
curl http://localhost:8000/anvil/contracts
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

### Check if a specific address has a contract

```bash
curl http://localhost:8000/anvil/contract/0x5FbDB2315678afecb367f032d93F642f64180aa3
```

**Response (contract exists):**
```json
{
  "address": "0x5FbDB2315678afecb367f032d93F642f64180aa3",
  "bytecodeHash": "0xabc123...",
  "deploymentBlock": null,
  "bytecode": "0x608060405234801561001057600080fd5b..."
}
```

**Response (no contract):**
```json
{
  "detail": "No contract deployed at address 0x5FbDB2315678afecb367f032d93F642f64180aa3"
}
```

---

## Workflow 8: Complete Development Workflow

### Full workflow from start to finish

```bash
# 1. Check Lenina health
curl http://localhost:8000/health

# 2. Start Anvil with default settings
curl -X POST http://localhost:8000/anvil/start

# 3. Get the accounts and private keys
curl http://localhost:8000/anvil/keys | jq .accounts[0]

# 4. Check the balance of the first account
curl -X POST http://localhost:8000/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "eth_getBalance",
    "params": ["0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266", "latest"],
    "id": 1
  }'

# 5. Get current block number
curl -X POST http://localhost:8000/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# 6. Send some ETH to another account
curl -X POST http://localhost:8000/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "eth_sendTransaction",
    "params": [{
      "from": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
      "to": "0x70997970C51812dc3A010C7d01b50e0d17dc79C8",
      "value": "0xDE0B6B3A7640000"
    }],
    "id": 1
  }'

# 7. Verify the transaction by checking block number (should have increased)
curl -X POST http://localhost:8000/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# 8. List any deployed contracts
curl http://localhost:8000/anvil/contracts

# 9. When done, stop Anvil
curl -X POST http://localhost:8000/anvil/stop
```

---

## Workflow 9: Advanced - Mining and Block Time

### Manually mine a block (when blockTime is 0)

```bash
# First, start Anvil with blockTime: 0 (auto-mine is default)
curl -X POST http://localhost:8000/anvil/start \
  -H "Content-Type: application/json" \
  -d '{"blockTime": 0}'

# Mine a block manually using RPC
curl -X POST http://localhost:8000/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"evm_mine","params":[],"id":1}'
```

### Set automatic block time

```bash
# Mine a block every 5 seconds
curl -X POST http://localhost:8000/anvil/start \
  -H "Content-Type: application/json" \
  -d '{"blockTime": 5}'
```

---

## Troubleshooting

### Error: "Connection refused"

```bash
curl: (7) Failed to connect to localhost port 8000
```

**Solution:** Lenina is not running. Start it:
```bash
python main.py
# Or: docker-compose up -d
```

### Error: "No Anvil instance is running"

```json
{
  "detail": "No Anvil instance is running"
}
```

**Solution:** Start Anvil first:
```bash
curl -X POST http://localhost:8000/anvil/start
```

### Error: "Address already in use"

```json
{
  "detail": "Anvil is already running"
}
```

**Solution:** Either stop the current instance or use a different port:
```bash
# Stop current instance
curl -X POST http://localhost:8000/anvil/stop

# Or start on different port
curl -X POST http://localhost:8000/anvil/start \
  -H "Content-Type: application/json" \
  -d '{"port": 8546}'
```

### Error: "Anvil not found"

```json
{
  "detail": "Anvil not found. Ensure Foundry is installed."
}
```

**Solution:** Install Foundry:
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

---

## JSON Formatting Tips

### Pretty-print JSON responses

If you have `jq` installed:
```bash
curl http://localhost:8000/anvil/keys | jq .
```

### Extract specific values

```bash
# Get first account address
curl http://localhost:8000/anvil/keys | jq -r '.accounts[0].address'

# Get current block number
curl -s -X POST http://localhost:8000/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  | jq -r '.result'
```

---

## Quick Reference Card

```bash
# Health check
curl http://localhost:8000/health

# Start/Stop/Restart
curl -X POST http://localhost:8000/anvil/start
curl -X POST http://localhost:8000/anvil/stop
curl -X POST http://localhost:8000/anvil/restart

# Status & Config
curl http://localhost:8000/anvil/status
curl http://localhost:8000/anvil/config
curl http://localhost:8000/anvil/keys

# Contracts
curl http://localhost:8000/anvil/contracts
curl http://localhost:8000/anvil/contract/{address}

# RPC Proxy
curl -X POST http://localhost:8000/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

---

## Next Steps

After mastering curl commands, you might want to:

1. **Use with Hardhat:** Configure `hardhat.config.js` to use `http://localhost:8545`
2. **Use with ethers.js:** Create a provider with `new ethers.JsonRpcProvider("http://localhost:8545")`
3. **Use with Foundry tools:** Run `forge test --rpc-url http://localhost:8545`
4. **Explore OpenAPI docs:** Visit `http://localhost:8000/docs` for interactive API documentation
