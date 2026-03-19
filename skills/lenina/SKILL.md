---
name: lenina
description: How to use the Lenina project (Anvil REST API management) using curl commands. Make sure to use this skill whenever the user mentions curl, HTTP requests, REST API, or wants to interact with Lenina/Anvil programmatically without SDKs, even if they don't explicitly mention "curl commands."
---

# Lenina: Using Lenina with curl

This skill provides complete workflow-style guidance for using the Lenina REST API with curl commands. Designed for users familiar with curl but new to blockchain/Anvil concepts.

## Configuration

**Lenina Base URL:** `http://mini:8000`

**Anvil RPC URL:** `http://192.168.1.12:8545` (remote server)

**GitHub:** https://github.com/brenoluz/lenina

---

## Environment Setup

### Set Base URL

```bash
# Export for current session:
export LENINA_BASE_URL=http://mini:8000
```

**Note:** Always use `$LENINA_BASE_URL` in curl commands after setting the URL.

## Workflow 1: Getting Started

### Step 1: Check if Lenina is running

```bash
curl $LENINA_BASE_URL/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-03-14T10:30:00.000Z"
}
```

**If you get an error:** Verify the Lenina server is accessible at `http://mini:8000`

### Step 2: Start Anvil (the local blockchain)

**What is Anvil?** Anvil is a local Ethereum blockchain used for development and testing. It's like a sandbox blockchain that runs on your computer.

```bash
curl -X POST $LENINA_BASE_URL/anvil/start
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

**Anvil RPC Endpoint:** `http://192.168.1.12:8545`

### Step 3: Verify Anvil is running

```bash
curl $LENINA_BASE_URL/anvil/status
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
curl -X POST $LENINA_BASE_URL/anvil/start \
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
curl -X POST $LENINA_BASE_URL/anvil/start \
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
curl $LENINA_BASE_URL/anvil/keys
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
curl $LENINA_BASE_URL/anvil/config
```

**Response:**
```json
{
  "ip": "127.0.0.1",
  "port": 8545,
  "chainId": 31337,
  "version": "v0.1.0",
  "blockTime": 0,
  "gasLimit": 30000000,
  "mnemonic": "test test test test test test test test test test test junk"
}
```

---

## Workflow 5: Stop and Restart Anvil

### Stop Anvil

```bash
curl -X POST $LENINA_BASE_URL/anvil/stop
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
curl -X POST $LENINA_BASE_URL/anvil/restart \
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
curl -X POST $LENINA_BASE_URL/anvil/rpc \
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
curl -X POST $LENINA_BASE_URL/anvil/rpc \
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
curl -X POST $LENINA_BASE_URL/anvil/rpc \
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
curl -X POST $LENINA_BASE_URL/anvil/rpc \
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

### Check if a specific address has a contract

```bash
curl $LENINA_BASE_URL/anvil/contract/0x5FbDB2315678afecb367f032d93F642f64180aa3
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
curl $LENINA_BASE_URL/health

# 2. Start Anvil with default settings
curl -X POST $LENINA_BASE_URL/anvil/start

# 3. Get the accounts and private keys
curl $LENINA_BASE_URL/anvil/keys | jq .accounts[0]

# 4. Check the balance of the first account
curl -X POST $LENINA_BASE_URL/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "eth_getBalance",
    "params": ["0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266", "latest"],
    "id": 1
  }'

# 5. Get current block number
curl -X POST $LENINA_BASE_URL/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# 6. Send some ETH to another account
curl -X POST $LENINA_BASE_URL/anvil/rpc \
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
 curl -X POST $LENINA_BASE_URL/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# 8. When done, stop Anvil
curl -X POST $LENINA_BASE_URL/anvil/stop
```

---

## Workflow 9: Mining Control - Disable Auto-Mining and Manual Block Production

### Disable auto-mining for precise control

```bash
# Disable automatic mining - transactions will stay pending until you manually mine
curl -X POST $LENINA_BASE_URL/anvil/mining/disable
```

**Response:**
```json
{
  "autoMine": false,
  "interval": 0,
  "blockNumber": 42
}
```

**Why disable auto-mining?** When auto-mining is disabled, transactions you send will remain pending in the mempool until you explicitly mine a block. This is useful for:
- Testing transaction ordering
- Batch multiple transactions before including them in a block
- Simulating network congestion
- Precise control over when transactions are executed

### Enable auto-mining again

```bash
# Re-enable instant auto-mining (default behavior)
curl -X POST $LENINA_BASE_URL/anvil/mining/enable
```

**Response:**
```json
{
  "autoMine": true,
  "interval": 0,
  "blockNumber": 43
}
```

**Note:** For interval mining (blocks every N seconds), restart Anvil with `blockTime` parameter:
```bash
curl -X POST $LENINA_BASE_URL/anvil/restart \
  -H "Content-Type: application/json" \
  -d '{"blockTime": 5}'
```

### Check mining status

```bash
curl $LENINA_BASE_URL/anvil/mining/status
```

**Response:**
```json
{
  "autoMine": true,
  "interval": 0,
  "blockNumber": 43
}
```

### Manually mine blocks on demand

```bash
# Mine 1 block (default)
curl -X POST $LENINA_BASE_URL/anvil/mining/mine
```

**Response:**
```json
{
  "blocksMined": 1,
  "newBlockNumber": 44,
  "status": "success"
}
```

### Mine multiple blocks at once

```bash
# Mine 10 blocks instantly
curl -X POST "$LENINA_BASE_URL/anvil/mining/mine?blocks=10"
```

**Response:**
```json
{
  "blocksMined": 10,
  "newBlockNumber": 54,
  "status": "success"
}
```

### Mine blocks with interval between them

```bash
# Mine 5 blocks with 0.5 seconds between each
curl -X POST "$LENINA_BASE_URL/anvil/mining/mine?blocks=5&interval=0.5"
```

**Response:**
```json
{
  "blocksMined": 5,
  "newBlockNumber": 59,
  "status": "success"
}
```

### Complete workflow: Test with manual mining control

```bash
# 1. Start Anvil
curl -X POST $LENINA_BASE_URL/anvil/start

# 2. Disable auto-mining
curl -X POST $LENINA_BASE_URL/anvil/mining/disable

# 3. Send a transaction (it will stay pending)
curl -X POST $LENINA_BASE_URL/anvil/rpc \
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

# 4. Check block number (won't have increased yet)
curl -X POST $LENINA_BASE_URL/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# 5. Manually mine a block to include the transaction
curl -X POST $LENINA_BASE_URL/anvil/mining/mine

# 6. Verify block number increased
curl -X POST $LENINA_BASE_URL/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# 7. Re-enable auto-mining
curl -X POST $LENINA_BASE_URL/anvil/mining/enable

# 8. Stop Anvil when done
curl -X POST $LENINA_BASE_URL/anvil/stop
```

---

## Workflow 10: Complete Development Workflow

### Full workflow from start to finish

```bash
# 1. Check Lenina health
curl $LENINA_BASE_URL/health

# 2. Start Anvil with default settings
curl -X POST $LENINA_BASE_URL/anvil/start

# 3. Get the accounts and private keys
curl $LENINA_BASE_URL/anvil/keys | jq .accounts[0]

# 4. Check the balance of the first account
curl -X POST $LENINA_BASE_URL/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "eth_getBalance",
    "params": ["0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266", "latest"],
    "id": 1
  }'

# 5. Get current block number
curl -X POST $LENINA_BASE_URL/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# 6. Send some ETH to another account
curl -X POST $LENINA_BASE_URL/anvil/rpc \
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
curl -X POST $LENINA_BASE_URL/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# 8. When done, stop Anvil
curl -X POST $LENINA_BASE_URL/anvil/stop
```

---

## Troubleshooting

### Error: "Connection refused"

```bash
curl: (7) Failed to connect to mini port 8000
```

**Solution:** 
1. Verify the Lenina server is running at `http://mini:8000`
2. Check network connectivity to the server

### Error: "No Anvil instance is running"

```json
{
  "detail": "No Anvil instance is running"
}
```

**Solution:** Start Anvil first:
```bash
curl -X POST $LENINA_BASE_URL/anvil/start
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
curl -X POST $LENINA_BASE_URL/anvil/stop

# Or start on different port
curl -X POST $LENINA_BASE_URL/anvil/start \
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
curl $LENINA_BASE_URL/anvil/keys | jq .
```

### Extract specific values

```bash
# Get first account address
curl $LENINA_BASE_URL/anvil/keys | jq -r '.accounts[0].address'

# Get current block number
curl -s -X POST $LENINA_BASE_URL/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  | jq -r '.result'
```

---

## Quick Reference Card

```bash
# Health check
curl $LENINA_BASE_URL/health

# Start/Stop/Restart
curl -X POST $LENINA_BASE_URL/anvil/start
curl -X POST $LENINA_BASE_URL/anvil/stop
curl -X POST $LENINA_BASE_URL/anvil/restart

# Status & Config
curl $LENINA_BASE_URL/anvil/status
curl $LENINA_BASE_URL/anvil/config
curl $LENINA_BASE_URL/anvil/keys

# Mining Control
curl -X POST $LENINA_BASE_URL/anvil/mining/disable       # Disable auto-mining
curl -X POST $LENINA_BASE_URL/anvil/mining/enable        # Enable auto-mining
curl $LENINA_BASE_URL/anvil/mining/status                # Get mining status
curl -X POST $LENINA_BASE_URL/anvil/mining/mine          # Mine 1 block
curl -X POST "$LENINA_BASE_URL/anvil/mining/mine?blocks=10"  # Mine 10 blocks

# Contracts
curl $LENINA_BASE_URL/anvil/contract/{address}

# RPC Proxy
curl -X POST $LENINA_BASE_URL/anvil/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

---

## Next Steps

After mastering curl commands, you might want to:

1. **Use with Hardhat:** Configure `hardhat.config.js` to use `http://192.168.1.12:8545`
2. **Use with ethers.js:** Create a provider with `new ethers.JsonRpcProvider("http://192.168.1.12:8545")`
3. **Use with Foundry tools:** Run `forge test --rpc-url http://192.168.1.12:8545`
4. **Explore OpenAPI docs:** Visit `http://mini:8000/docs` for interactive API documentation

## Resources

- **GitHub:** https://github.com/brenoluz/lenina
- **API Docs:** `http://mini:8000/docs`
- **Changelog:** https://github.com/brenoluz/lenina/blob/main/CHANGELOG.md
