"""
Lenina - Anvil RESTful Management API
"""
from fastapi import FastAPI, HTTPException, Path
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import subprocess
import asyncio
import re
import os
import signal
import time
from datetime import datetime
import httpx
import socket

app = FastAPI(
    title="Lenina",
    description="RESTful API for managing Anvil (Foundry's local Ethereum blockchain)",
    version="0.1.0"
)


class AnvilConfig(BaseModel):
    """Configuration for starting Anvil"""
    port: Optional[int] = Field(default=8545, description="Anvil RPC port")
    chainId: Optional[int] = Field(default=31337, description="Chain ID")
    blockTime: Optional[int] = Field(default=0, description="Block time in seconds (0 for auto)")
    gasLimit: Optional[int] = Field(default=30000000, description="Gas limit per block")
    mnemonic: Optional[str] = Field(default=None, description="HD wallet mnemonic")


class AnvilStatus(BaseModel):
    """Status of Anvil instance"""
    running: bool
    pid: Optional[int] = None
    uptime: Optional[float] = None
    port: Optional[int] = None


class AnvilStartResponse(BaseModel):
    """Response from starting Anvil"""
    pid: int
    port: int
    chainId: int
    status: str


class AnvilStopResponse(BaseModel):
    """Response from stopping Anvil"""
    status: str
    message: str


class AnvilRestartResponse(BaseModel):
    """Response from restarting Anvil"""
    pid: int
    port: int
    chainId: int
    status: str
    message: str


class PrivateKeyInfo(BaseModel):
    """Private key and address pair"""
    address: str
    privateKey: str


class AnvilKeysResponse(BaseModel):
    """Response from getting private keys"""
    accounts: List[PrivateKeyInfo]
    mnemonic: Optional[str] = None


class ContractInfo(BaseModel):
    """Information about a deployed contract"""
    address: str
    bytecodeHash: str
    deploymentBlock: int
    abi: Optional[Dict[str, Any]] = None


class ContractsListResponse(BaseModel):
    """Response from listing deployed contracts"""
    contracts: List[ContractInfo]


class ContractDetailsResponse(BaseModel):
    """Response from checking contract at address"""
    address: str
    bytecodeHash: str
    deploymentBlock: Optional[int] = None
    bytecode: str


class AnvilConfigResponse(BaseModel):
    """Response from getting Anvil configuration"""
    ip: str
    port: int
    chainId: int
    version: str
    blockTime: int
    gasLimit: int
    mnemonic: Optional[str] = None


class RpcRequest(BaseModel):
    """JSON-RPC request model"""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="RPC method name")
    params: Optional[List[Any]] = Field(default=None, description="RPC method parameters")
    id: Optional[Any] = Field(default=None, description="Request ID")


class RpcResponse(BaseModel):
    """JSON-RPC response model"""
    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    result: Optional[Any] = Field(default=None, description="RPC result")
    error: Optional[Dict[str, Any]] = Field(default=None, description="RPC error if any")
    id: Optional[Any] = Field(default=None, description="Request ID")


# Global state
anvil_process: Optional[subprocess.Popen[Any]] = None
anvil_start_time: Optional[float] = None
anvil_config: Optional[Dict[str, Any]] = None
anvil_accounts: List[PrivateKeyInfo] = []
deployed_contracts: List[Dict[str, Any]] = []


def get_lan_ip() -> str:
    """Get the LAN IP address of this machine"""
    host_ip = os.environ.get("HOST_IP")
    if host_ip:
        return host_ip
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/anvil/config", response_model=AnvilConfigResponse)
async def get_config() -> AnvilConfigResponse:
    """
    Get Anvil configuration.

    Response includes: IP, port, chainId, version, blockTime, gasLimit, etc.
    Returns 400 if Anvil is not running.
    """
    # Check if Anvil is running
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(
            status_code=400,
            detail="No Anvil instance is running"
        )

    if not anvil_config:
        raise HTTPException(
            status_code=500,
            detail="Anvil configuration not available"
        )

    return AnvilConfigResponse(
        ip=get_lan_ip(),
        port=anvil_config.get("port", 8545),
        chainId=anvil_config.get("chainId", 31337),
        version="0.1.0",
        blockTime=anvil_config.get("blockTime", 0),
        gasLimit=anvil_config.get("gasLimit", 30000000),
        mnemonic=anvil_config.get("mnemonic")
    )


@app.get("/anvil/keys", response_model=AnvilKeysResponse)
async def get_private_keys() -> AnvilKeysResponse:
    """
    Retrieve Anvil's generated private keys and addresses.

    Returns 400 if Anvil is not running.
    Response includes at least 10 default accounts with private keys.
    """
    # Check if Anvil is running
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(
            status_code=400,
            detail="No Anvil instance is running"
        )

    if not anvil_accounts:
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve private keys from Anvil"
        )

    return AnvilKeysResponse(
        accounts=anvil_accounts,
        mnemonic=anvil_config.get("mnemonic") if anvil_config else None
    )


@app.get("/anvil/contracts", response_model=ContractsListResponse)
async def list_contracts() -> ContractsListResponse:
    """
    List all deployed contracts.

    Response includes: address, deploymentBlock, bytecodeHash for each.
    Contracts tracked from session start or persistence if configured.
    Returns 400 if Anvil is not running.
    """
    # Check if Anvil is running
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(
            status_code=400,
            detail="No Anvil instance is running"
        )

    return ContractsListResponse(
        contracts=[ContractInfo(**c) for c in deployed_contracts]
    )


@app.get("/anvil/contract/{address}", response_model=ContractDetailsResponse)
async def get_contract(address: str = Path(..., description="Contract address to check")) -> ContractDetailsResponse:
    """
    Check if a contract exists at the specified address.

    Returns 200 with contract info (bytecode, bytecodeHash) if deployed.
    Returns 404 if no contract at address.
    Returns 400 if Anvil is not running.
    """
    # Check if Anvil is running
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(
            status_code=400,
            detail="No Anvil instance is running"
        )

    # Validate address format
    if not re.match(r"^0x[0-9a-fA-F]{40}$", address):
        raise HTTPException(
            status_code=400,
            detail="Invalid Ethereum address format"
        )

    # Get the Anvil port from config
    port = anvil_config.get("port", 8545) if anvil_config else 8545
    rpc_url = f"http://127.0.0.1:{port}"

    try:
        async with httpx.AsyncClient() as client:
            # Use eth_getCode to check if contract exists at address
            response = await client.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_getCode",
                    "params": [address, "latest"],
                    "id": 1
                },
                timeout=10.0
            )
            result = response.json()

            if "error" in result:
                raise HTTPException(
                    status_code=400,
                    detail=f"RPC error: {result['error'].get('message', 'Unknown error')}"
                )

            bytecode = result.get("result", "0x")

            # If bytecode is "0x" or empty, no contract at address
            if bytecode == "0x" or not bytecode:
                raise HTTPException(
                    status_code=404,
                    detail=f"No contract deployed at address {address}"
                )

            # Calculate bytecode hash
            import hashlib
            bytecode_hash = "0x" + hashlib.sha256(bytecode.encode()).hexdigest()

            return ContractDetailsResponse(
                address=address,
                bytecodeHash=bytecode_hash,
                bytecode=bytecode
            )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=400,
            detail="Timeout connecting to Anvil RPC"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to Anvil RPC: {str(e)}"
        )


@app.post("/anvil/start", response_model=AnvilStartResponse)
async def start_anvil(config: Optional[AnvilConfig] = None) -> AnvilStartResponse:
    """
    Start an Anvil instance with optional configuration.

    Returns 400 if Anvil is already running.
    Returns 500 if Anvil fails to start.
    """
    global anvil_process, anvil_start_time, anvil_config, anvil_accounts

    # Check if already running
    if anvil_process is not None and anvil_process.poll() is None:
        raise HTTPException(
            status_code=400,
            detail="Anvil is already running"
        )

    # Use provided config or defaults
    cfg = config.dict() if config else {}
    port = cfg.get("port", 8545)
    chain_id = cfg.get("chainId", 31337)
    block_time = cfg.get("blockTime", 0)
    gas_limit = cfg.get("gasLimit", 30000000)
    mnemonic = cfg.get("mnemonic")

    # Build Anvil command
    cmd = [
        "anvil",
        "--port", str(port),
        "--chain-id", str(chain_id),
        "--gas-limit", str(gas_limit),
        "--host", "0.0.0.0",
    ]

    if block_time > 0:
        cmd.extend(["--block-time", str(block_time)])

    if mnemonic:
        cmd.extend(["--mnemonic", mnemonic])

    try:
        import fcntl
        
        # Start Anvil process
        anvil_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid if os.name != "nt" else None
        )
        
        # Set stdout to non-blocking mode
        if anvil_process.stdout and os.name != "nt":
            flags = fcntl.fcntl(anvil_process.stdout.fileno(), fcntl.F_GETFL)
            fcntl.fcntl(anvil_process.stdout.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)

        # Wait a moment for Anvil to start and read output
        await asyncio.sleep(0.5)

        # Check if process is still running
        if anvil_process.poll() is not None:
            # Process failed to start
            output = ""
            try:
                if anvil_process.stdout:
                    output = anvil_process.stdout.read()
            except Exception:
                pass
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start Anvil: {output}"
            )

        # Parse Anvil's output to extract private keys and addresses
        # Read available output in non-blocking mode
        output = ""
        if anvil_process.stdout:
            try:
                output = anvil_process.stdout.read(8192) or ""
            except BlockingIOError:
                output = ""

        # Parse addresses and private keys using regex
        address_pattern = r"\((\d+)\)\s+(0x[0-9a-fA-F]+)\s+\("
        key_pattern = r"\((\d+)\)\s+(0x[0-9a-fA-F]+)$"

        addresses = re.findall(address_pattern, output)
        private_keys = re.findall(key_pattern, output, re.MULTILINE)

        # Clear and populate accounts
        anvil_accounts.clear()
        min_count = min(len(addresses), len(private_keys))

        for i in range(min_count):
            anvil_accounts.append(PrivateKeyInfo(
                address=addresses[i][1],
                privateKey=private_keys[i][1]
            ))

        anvil_start_time = time.time()
        anvil_config = {
            "port": port,
            "chainId": chain_id,
            "blockTime": block_time,
            "gasLimit": gas_limit,
            "mnemonic": mnemonic
        }

        # Reset deployed contracts tracking
        deployed_contracts.clear()

        return AnvilStartResponse(
            pid=anvil_process.pid,
            port=port,
            chainId=chain_id,
            status="running"
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Anvil not found. Ensure Foundry is installed."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start Anvil: {str(e)}"
        )


@app.post("/anvil/stop", response_model=AnvilStopResponse)
async def stop_anvil() -> AnvilStopResponse:
    """
    Stop a running Anvil instance.

    Returns 400 if no Anvil instance is running.
    Gracefully terminates the process.
    """
    global anvil_process, anvil_start_time, anvil_config, anvil_accounts

    # Check if Anvil is running
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(
            status_code=400,
            detail="No Anvil instance is running"
        )

    pid = anvil_process.pid  # Get pid before any operations

    try:
        # Get process group for clean termination
        if os.name != "nt":
            # Unix: kill the process group
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        else:
            # Windows: terminate process
            anvil_process.terminate()

        # Wait for process to exit
        anvil_process.wait(timeout=5)

        # Clear state
        anvil_process = None
        anvil_start_time = None
        anvil_config = None
        anvil_accounts.clear()

        return AnvilStopResponse(
            status="stopped",
            message=f"Anvil instance (PID {pid}) has been stopped"
        )

    except subprocess.TimeoutExpired:
        # Force kill if graceful shutdown fails
        if os.name != "nt":
            os.killpg(os.getpgid(pid), signal.SIGKILL)
        else:
            # anvil_process is guaranteed to not be None here
            if anvil_process is not None:
                anvil_process.kill()

        anvil_process = None
        anvil_start_time = None
        anvil_config = None
        anvil_accounts.clear()

        return AnvilStopResponse(
            status="stopped",
            message=f"Anvil instance was forcefully stopped"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop Anvil: {str(e)}"
        )


@app.get("/anvil/status", response_model=AnvilStatus)
async def get_anvil_status() -> AnvilStatus:
    """
    Get Anvil running status.

    Response includes: running (boolean), pid, uptime, port.
    Returns 200 regardless of running state.
    """
    # Check if Anvil is running
    if anvil_process is not None and anvil_process.poll() is None:
        uptime = time.time() - anvil_start_time if anvil_start_time else None
        return AnvilStatus(
            running=True,
            pid=anvil_process.pid,
            uptime=uptime,
            port=anvil_config.get("port") if anvil_config else None
        )
    else:
        return AnvilStatus(
            running=False,
            pid=None,
            uptime=None,
            port=None
        )


@app.post("/anvil/rpc", response_model=RpcResponse)
async def proxy_rpc(request: RpcRequest) -> RpcResponse:
    """
    Proxy JSON-RPC requests to Anvil.

    Forwards requests to Anvil's JSON-RPC endpoint and returns the response.
    Supports standard Ethereum JSON-RPC methods (eth_sendTransaction, eth_call, etc.).
    Returns 400 if Anvil is not running.
    """
    # Check if Anvil is running
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(
            status_code=400,
            detail="No Anvil instance is running"
        )

    # Get the Anvil port from config
    port = anvil_config.get("port", 8545) if anvil_config else 8545
    rpc_url = f"http://127.0.0.1:{port}"

    try:
        async with httpx.AsyncClient() as client:
            # Forward the JSON-RPC request to Anvil
            response = await client.post(
                rpc_url,
                json={
                    "jsonrpc": request.jsonrpc,
                    "method": request.method,
                    "params": request.params or [],
                    "id": request.id
                },
                timeout=30.0
            )
            result = response.json()

            return RpcResponse(
                jsonrpc=result.get("jsonrpc", "2.0"),
                result=result.get("result"),
                error=result.get("error"),
                id=result.get("id")
            )

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=400,
            detail="Timeout connecting to Anvil RPC"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to connect to Anvil RPC: {str(e)}"
        )


@app.post("/anvil/restart", response_model=AnvilRestartResponse)
async def restart_anvil(config: Optional[AnvilConfig] = None) -> AnvilRestartResponse:
    """
    Restart a running Anvil instance.

    Preserves configuration from previous run or accepts new config.
    Returns 200 with new process details on success.
    """
    global anvil_process, anvil_start_time, anvil_config, anvil_accounts

    # If no config provided, use the current running config
    if config is None and anvil_config is not None:
        config = AnvilConfig(**anvil_config)

    # Stop the current instance if running (don't error if not running)
    if anvil_process is not None and anvil_process.poll() is not None:
        # Process exists but isn't running, clean up state
        anvil_process = None
        anvil_start_time = None
        anvil_config = None
    elif anvil_process is not None:
        # Gracefully stop the running instance
        pid = anvil_process.pid
        try:
            if os.name != "nt":
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            else:
                anvil_process.terminate()
            anvil_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            if os.name != "nt":
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            else:
                anvil_process.kill()
        except Exception:
            pass
        finally:
            anvil_process = None
            anvil_start_time = None
            anvil_config = None
            anvil_accounts.clear()

    # Now start Anvil with the config
    # Reuse the start logic inline to avoid cross-function calls
    cfg = config.dict() if config else {}
    port = cfg.get("port", 8545)
    chain_id = cfg.get("chainId", 31337)
    block_time = cfg.get("blockTime", 0)
    gas_limit = cfg.get("gasLimit", 30000000)
    mnemonic = cfg.get("mnemonic")

    cmd = [
        "anvil",
        "--port", str(port),
        "--chain-id", str(chain_id),
        "--gas-limit", str(gas_limit),
        "--host", "0.0.0.0",
    ]

    if block_time > 0:
        cmd.extend(["--block-time", str(block_time)])

    if mnemonic:
        cmd.extend(["--mnemonic", mnemonic])

    try:
        import fcntl
        
        anvil_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid if os.name != "nt" else None
        )
        
        # Set stdout to non-blocking mode
        if anvil_process.stdout and os.name != "nt":
            flags = fcntl.fcntl(anvil_process.stdout.fileno(), fcntl.F_GETFL)
            fcntl.fcntl(anvil_process.stdout.fileno(), fcntl.F_SETFL, flags | os.O_NONBLOCK)

        await asyncio.sleep(0.5)

        if anvil_process.poll() is not None:
            output = ""
            try:
                if anvil_process.stdout:
                    output = anvil_process.stdout.read()
            except Exception:
                pass
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start Anvil: {output}"
            )

        # Parse Anvil's output to extract private keys and addresses
        # Read available output in non-blocking mode
        output = ""
        if anvil_process.stdout:
            try:
                output = anvil_process.stdout.read(8192) or ""
            except BlockingIOError:
                output = ""

        # Parse addresses and private keys using regex
        address_pattern = r"\((\d+)\)\s+(0x[0-9a-fA-F]+)\s+\("
        key_pattern = r"\((\d+)\)\s+(0x[0-9a-fA-F]+)$"

        addresses = re.findall(address_pattern, output)
        private_keys = re.findall(key_pattern, output, re.MULTILINE)

        # Clear and populate accounts
        anvil_accounts.clear()
        min_count = min(len(addresses), len(private_keys))

        for i in range(min_count):
            anvil_accounts.append(PrivateKeyInfo(
                address=addresses[i][1],
                privateKey=private_keys[i][1]
            ))

        anvil_start_time = time.time()
        anvil_config = {
            "port": port,
            "chainId": chain_id,
            "blockTime": block_time,
            "gasLimit": gas_limit,
            "mnemonic": mnemonic
        }

        deployed_contracts.clear()

        return AnvilRestartResponse(
            pid=anvil_process.pid,
            port=port,
            chainId=chain_id,
            status="running",
            message="Anvil instance restarted successfully"
        )

    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Anvil not found. Ensure Foundry is installed."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to restart Anvil: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
