"""
Lenina - Anvil RESTful Management API
"""

from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.responses import StreamingResponse
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


def get_version() -> str:
    """Get version from package metadata or git"""
    try:
        from importlib.metadata import version

        return version("lenina")
    except Exception:
        pass

    try:
        import subprocess

        result = subprocess.run(
            ["git", "describe", "--tags", "--always"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    return "unknown"


__version__ = get_version()

app = FastAPI(
    title="Lenina",
    description="RESTful API for managing Anvil (Foundry's local Ethereum blockchain)",
    version=__version__,
)


class AnvilConfig(BaseModel):
    """Configuration for starting Anvil"""

    port: Optional[int] = Field(default=8545, description="Anvil RPC port")
    chainId: Optional[int] = Field(default=31337, description="Chain ID")
    blockTime: Optional[int] = Field(default=0, description="Block time in seconds (0 for auto)")
    gasLimit: Optional[int] = Field(default=30000000, description="Gas limit per block")
    mnemonic: Optional[str] = Field(default=None, description="HD wallet mnemonic (12-24 words)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "port": 8545,
                "chainId": 31337,
                "blockTime": 0,
                "gasLimit": 30000000,
                "mnemonic": None,
            }
        }
    }


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


class MiningConfig(BaseModel):
    """Configuration for mining control"""

    interval: Optional[float] = Field(
        default=0, description="Block time interval in seconds (0 for on-demand)"
    )
    autoMine: Optional[bool] = Field(default=None, description="Enable/disable auto-mining")

    model_config = {"json_schema_extra": {"example": {"interval": 0, "autoMine": False}}}


class MiningStatusResponse(BaseModel):
    """Response from getting mining status"""

    autoMine: bool
    interval: float
    blockNumber: int


class MineBlocksResponse(BaseModel):
    """Response from mining blocks"""

    blocksMined: int
    newBlockNumber: int
    status: str


class PrivateKeyInfo(BaseModel):
    """Private key and address pair"""

    address: str
    privateKey: str


class AnvilKeysResponse(BaseModel):
    """Response from getting private keys"""

    accounts: List[PrivateKeyInfo]
    mnemonic: Optional[str] = None


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


class LogEntry(BaseModel):
    """Single log entry"""

    line: str
    timestamp: float
    sequence: int


class AnvilLogsResponse(BaseModel):
    """Response from getting Anvil logs"""

    lines: List[LogEntry]
    totalLines: int
    truncated: bool
    format: str = "markdown"


# Global state
anvil_process: Optional[subprocess.Popen[Any]] = None
anvil_start_time: Optional[float] = None
anvil_config: Optional[Dict[str, Any]] = None
anvil_accounts: List[PrivateKeyInfo] = []
anvil_logs: List[Dict[str, Any]] = []
anvil_log_sequence: int = 0
LOG_BUFFER_MAX = 1000


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


def to_hex(value: int | float) -> str:
    """Convert a number to hex string with 0x prefix"""
    return hex(int(value))


def append_log_line(line: str) -> None:
    """Append a log line to the circular buffer"""
    global anvil_logs, anvil_log_sequence

    anvil_log_sequence += 1
    anvil_logs.append(
        {"line": line.rstrip(), "timestamp": time.time(), "sequence": anvil_log_sequence}
    )

    if len(anvil_logs) > LOG_BUFFER_MAX:
        anvil_logs.pop(0)


def format_logs_as_markdown(logs: List[Dict[str, Any]]) -> str:
    """Format logs as markdown code block"""
    if not logs:
        return "```\nNo logs available\n```"

    formatted = "\n".join(entry["line"] for entry in logs)
    return f"```\n{formatted}\n```"


async def capture_anvil_output():
    """Continuously capture Anvil stdout in background"""
    global anvil_process

    current_block = 0

    while anvil_process is not None and anvil_process.poll() is None:
        if anvil_process.stdout:
            try:
                output = anvil_process.stdout.read(4096) or ""
                if output:
                    for line in output.splitlines():
                        append_log_line(line)

                        block_match = re.search(r"Block\s+(\d+)", line, re.IGNORECASE)
                        if block_match:
                            current_block = int(block_match.group(1))
            except BlockingIOError:
                pass
        await asyncio.sleep(0.1)


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.get("/anvil/config", response_model=AnvilConfigResponse)
async def get_avnil_config() -> AnvilConfigResponse:
    """
    Get Anvil configuration.

    Response includes: IP, port, chainId, version, blockTime, gasLimit, etc.
    Returns 400 if Anvil is not running.
    """
    # Check if Anvil is running
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(status_code=400, detail="No Anvil instance is running")

    if not anvil_config:
        raise HTTPException(status_code=500, detail="Anvil configuration not available")

    return AnvilConfigResponse(
        ip=get_lan_ip(),
        port=anvil_config.get("port", 8545),
        chainId=anvil_config.get("chainId", 31337),
        version=__version__,
        blockTime=anvil_config.get("blockTime", 0),
        gasLimit=anvil_config.get("gasLimit", 30000000),
        mnemonic=anvil_config.get("mnemonic"),
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
        raise HTTPException(status_code=400, detail="No Anvil instance is running")

    if not anvil_accounts:
        raise HTTPException(status_code=500, detail="Failed to retrieve private keys from Anvil")

    return AnvilKeysResponse(
        accounts=anvil_accounts, mnemonic=anvil_config.get("mnemonic") if anvil_config else None
    )


@app.get("/anvil/contract/{address}", response_model=ContractDetailsResponse)
async def get_contract(
    address: str = Path(..., description="Contract address to check"),
) -> ContractDetailsResponse:
    """
    Check if a contract exists at the specified address.

    Returns 200 with contract info (bytecode, bytecodeHash) if deployed.
    Returns 404 if no contract at address.
    Returns 400 if Anvil is not running.
    """
    # Check if Anvil is running
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(status_code=400, detail="No Anvil instance is running")

    # Validate address format
    if not re.match(r"^0x[0-9a-fA-F]{40}$", address):
        raise HTTPException(status_code=400, detail="Invalid Ethereum address format")

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
                    "id": 1,
                },
                timeout=10.0,
            )
            result = response.json()

            if "error" in result:
                raise HTTPException(
                    status_code=400,
                    detail=f"RPC error: {result['error'].get('message', 'Unknown error')}",
                )

            bytecode = result.get("result", "0x")

            # If bytecode is "0x" or empty, no contract at address
            if bytecode == "0x" or not bytecode:
                raise HTTPException(
                    status_code=404, detail=f"No contract deployed at address {address}"
                )

            # Calculate bytecode hash
            import hashlib

            bytecode_hash = "0x" + hashlib.sha256(bytecode.encode()).hexdigest()

            return ContractDetailsResponse(
                address=address, bytecodeHash=bytecode_hash, bytecode=bytecode
            )

    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail="Timeout connecting to Anvil RPC")
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect to Anvil RPC: {str(e)}")


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
        raise HTTPException(status_code=400, detail="Anvil is already running")

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
        "--port",
        str(port),
        "--chain-id",
        str(chain_id),
        "--gas-limit",
        str(gas_limit),
        "--host",
        "0.0.0.0",
        "--no-mining",
    ]

    if block_time > 0:
        cmd.extend(["--block-time", str(block_time)])

    if mnemonic and mnemonic.strip():
        cmd.extend(["--mnemonic", mnemonic])

    try:
        import fcntl

        # Start Anvil process
        anvil_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid if os.name != "nt" else None,
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
            raise HTTPException(status_code=500, detail=f"Failed to start Anvil: {output}")

        # Parse Anvil's output to extract private keys and addresses
        # Read available output in non-blocking mode
        output = ""
        if anvil_process.stdout:
            try:
                output = anvil_process.stdout.read(8192) or ""
                # Capture initial output to logs
                for line in output.splitlines():
                    append_log_line(line)
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
            anvil_accounts.append(
                PrivateKeyInfo(address=addresses[i][1], privateKey=private_keys[i][1])
            )

        anvil_start_time = time.time()
        anvil_config = {
            "port": port,
            "chainId": chain_id,
            "blockTime": block_time,
            "gasLimit": gas_limit,
            "mnemonic": mnemonic,
            "autoMine": False,  # --no-auto-mine disables auto-mining by default
        }

        asyncio.create_task(capture_anvil_output())

        return AnvilStartResponse(
            pid=anvil_process.pid, port=port, chainId=chain_id, status="running"
        )

    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Anvil not found. Ensure Foundry is installed.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start Anvil: {str(e)}")


@app.post("/anvil/stop", response_model=AnvilStopResponse)
async def stop_anvil(preserve_logs: bool = False) -> AnvilStopResponse:
    """
    Stop a running Anvil instance.

    Returns 400 if no Anvil instance is running.
    Gracefully terminates the process.
    """
    global \
        anvil_process, \
        anvil_start_time, \
        anvil_config, \
        anvil_accounts, \
        anvil_logs, \
        anvil_log_sequence

    # Check if Anvil is running
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(status_code=400, detail="No Anvil instance is running")

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
        if not preserve_logs:
            anvil_logs.clear()
            anvil_log_sequence = 0

        return AnvilStopResponse(
            status="stopped", message=f"Anvil instance (PID {pid}) has been stopped"
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
        if not preserve_logs:
            anvil_logs.clear()
            anvil_log_sequence = 0

        return AnvilStopResponse(status="stopped", message=f"Anvil instance was forcefully stopped")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop Anvil: {str(e)}")


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
            port=anvil_config.get("port") if anvil_config else None,
        )
    else:
        return AnvilStatus(running=False, pid=None, uptime=None, port=None)


@app.get("/anvil/logs", response_model=AnvilLogsResponse)
async def get_anvil_logs(
    lines: int = 100, since: Optional[int] = None, format: str = "markdown"
) -> AnvilLogsResponse:
    """
    Get Anvil console logs.

    - **lines**: Number of recent lines (1-1000, default: 100)
    - **since**: Optional sequence number to get logs after
    - **format**: Output format - markdown, json, or text

    Returns logs in circular buffer (max 1000 lines).
    Returns 400 if no Anvil instance is running.
    """
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(status_code=400, detail="No Anvil instance is running")

    filtered_logs = anvil_logs.copy()

    if since is not None:
        filtered_logs = [log for log in filtered_logs if log["sequence"] > since]

    recent_logs = filtered_logs[-lines:] if lines else filtered_logs

    return AnvilLogsResponse(
        lines=[LogEntry(**log) for log in recent_logs],
        totalLines=len(anvil_logs),
        truncated=len(recent_logs) < len(filtered_logs),
        format=format,
    )


@app.get("/anvil/logs/stream")
async def stream_anvil_logs(since: Optional[int] = None, format: str = "markdown"):
    """
    Stream Anvil logs in real-time using Server-Sent Events (SSE).

    - **since**: Optional sequence number to start from (default: end of current buffer)
    - **format**: Output format - markdown or text

    Returns event stream with new log lines as they arrive.
    Connection closes when Anvil stops.
    """
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(status_code=400, detail="No Anvil instance is running")

    async def event_generator():
        last_sequence = since if since is not None else (anvil_log_sequence or 0)

        while anvil_process is not None and anvil_process.poll() is None:
            new_logs = [log for log in anvil_logs if log["sequence"] > last_sequence]

            for log in new_logs:
                if format == "markdown":
                    data = f"```\n{log['line']}\n```"
                else:
                    data = log["line"]

                yield f"data: {data}\n\n"
                last_sequence = log["sequence"]

            yield f": keepalive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
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
        raise HTTPException(status_code=400, detail="No Anvil instance is running")

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
                    "id": request.id,
                },
                timeout=30.0,
            )
            result = response.json()

            return RpcResponse(
                jsonrpc=result.get("jsonrpc", "2.0"),
                result=result.get("result"),
                error=result.get("error"),
                id=result.get("id"),
            )

    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail="Timeout connecting to Anvil RPC")
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect to Anvil RPC: {str(e)}")


@app.post("/anvil/mining/disable", response_model=MiningStatusResponse)
async def disable_auto_mining() -> MiningStatusResponse:
    """
    Disable auto-mining in Anvil.

    After disabling, blocks will only be mined when explicitly requested via /anvil/mining/mine.
    This is useful for testing scenarios where you need precise control over block production.

    Returns 400 if Anvil is not running.
    """
    # Check if Anvil is running
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(status_code=400, detail="No Anvil instance is running")

    port = anvil_config.get("port", 8545) if anvil_config else 8545
    rpc_url = f"http://127.0.0.1:{port}"

    try:
        async with httpx.AsyncClient() as client:
            # Use evm_setAutomine to disable auto-mining
            response = await client.post(
                rpc_url,
                json={"jsonrpc": "2.0", "method": "evm_setAutomine", "params": [False], "id": 1},
                timeout=10.0,
            )
            result = response.json()

            if "error" in result:
                raise HTTPException(
                    status_code=400,
                    detail=f"RPC error: {result['error'].get('message', 'Unknown error')}",
                )

            # Get current block number
            block_response = await client.post(
                rpc_url,
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 2},
                timeout=10.0,
            )
            block_result = block_response.json()
            block_number = int(block_result.get("result", "0x0"), 16)

            # Update config to reflect mining disabled
            if anvil_config:
                anvil_config["blockTime"] = 0
                anvil_config["autoMine"] = False

            return MiningStatusResponse(autoMine=False, interval=0, blockNumber=block_number)

    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail="Timeout connecting to Anvil RPC")
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect to Anvil RPC: {str(e)}")


@app.post("/anvil/mining/enable", response_model=MiningStatusResponse)
async def enable_auto_mining(config: Optional[MiningConfig] = None) -> MiningStatusResponse:
    """
    Enable auto-mining in Anvil.

    - **interval**: Parameter accepted but ignored (interval mining must be set at startup via /anvil/start with blockTime)
    - **autoMine**: Set to True to enable auto-mining

    Note: For interval mining, restart Anvil with blockTime parameter: POST /anvil/restart with {"blockTime": N}

    Returns 400 if Anvil is not running.
    """
    # Check if Anvil is running
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(status_code=400, detail="No Anvil instance is running")

    port = anvil_config.get("port", 8545) if anvil_config else 8545
    rpc_url = f"http://127.0.0.1:{port}"

    cfg = config.dict() if config else {}
    interval = cfg.get("interval", 0)

    try:
        async with httpx.AsyncClient() as client:
            # Use evm_setAutomine to enable auto-mining
            response = await client.post(
                rpc_url,
                json={"jsonrpc": "2.0", "method": "evm_setAutomine", "params": [True], "id": 1},
                timeout=10.0,
            )
            result = response.json()

            if "error" in result:
                raise HTTPException(
                    status_code=400,
                    detail=f"RPC error: {result['error'].get('message', 'Unknown error')}",
                )

            # Note: evm_setIntervalMining is not a standard Anvil RPC method
            # Interval mining must be set at startup via --block-time flag
            # We just use the configured interval for reporting purposes

            # Get current block number
            block_response = await client.post(
                rpc_url,
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 2},
                timeout=10.0,
            )
            block_result = block_response.json()
            block_number = int(block_result.get("result", "0x0"), 16)

            # Update config to reflect mining enabled
            if anvil_config:
                anvil_config["blockTime"] = interval if interval > 0 else 0
                anvil_config["autoMine"] = True

            return MiningStatusResponse(
                autoMine=True, interval=interval if interval > 0 else 0, blockNumber=block_number
            )

    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail="Timeout connecting to Anvil RPC")
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect to Anvil RPC: {str(e)}")


@app.get("/anvil/mining/status", response_model=MiningStatusResponse)
async def get_mining_status() -> MiningStatusResponse:
    """
    Get current mining status.

    Returns information about auto-mining status, interval, and current block number.
    Returns 400 if Anvil is not running.
    """
    # Check if Anvil is running
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(status_code=400, detail="No Anvil instance is running")

    port = anvil_config.get("port", 8545) if anvil_config else 8545
    rpc_url = f"http://127.0.0.1:{port}"

    try:
        async with httpx.AsyncClient() as client:
            # Get current block number
            block_response = await client.post(
                rpc_url,
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                timeout=10.0,
            )
            block_result = block_response.json()

            if "error" in block_result:
                raise HTTPException(
                    status_code=400,
                    detail=f"RPC error: {block_result['error'].get('message', 'Unknown error')}",
                )

            block_number = int(block_result.get("result", "0x0"), 16)

            # Get interval from config
            interval = anvil_config.get("blockTime", 0) if anvil_config else 0

            # Get auto-mine state from config (set to False when --no-auto-mine is used)
            auto_mine = anvil_config.get("autoMine", False) if anvil_config else False

            return MiningStatusResponse(
                autoMine=auto_mine, interval=interval, blockNumber=block_number
            )

    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail="Timeout connecting to Anvil RPC")
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect to Anvil RPC: {str(e)}")


@app.post("/anvil/mining/mine", response_model=MineBlocksResponse)
async def mine_blocks(
    blocks: int = Query(default=1, ge=1, le=1000, description="Number of blocks to mine (1-1000)"),
    interval: Optional[float] = Query(
        default=None, description="Interval in seconds between blocks"
    ),
) -> MineBlocksResponse:
    """
    Manually mine blocks.

    - **blocks**: Number of blocks to mine (default: 1, max: 1000)
    - **interval**: Optional interval in seconds between each mined block

    This is useful when auto-mining is disabled and you need to produce blocks on demand.
    Returns 400 if Anvil is not running.
    """
    # Check if Anvil is running
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(status_code=400, detail="No Anvil instance is running")

    port = anvil_config.get("port", 8545) if anvil_config else 8545
    rpc_url = f"http://127.0.0.1:{port}"

    try:
        async with httpx.AsyncClient() as client:
            # Use anvil_mine to mine blocks
            # If interval is provided, use it; otherwise mine instantly
            # Anvil RPC expects hex-encoded numbers
            params: List[Any] = [to_hex(blocks)]
            if interval is not None:
                params.append(
                    to_hex(int(interval * 1000))
                )  # Convert to milliseconds for anvil_mine

            response = await client.post(
                rpc_url,
                json={"jsonrpc": "2.0", "method": "anvil_mine", "params": params, "id": 1},
                timeout=30.0,
            )
            result = response.json()

            if "error" in result:
                raise HTTPException(
                    status_code=400,
                    detail=f"RPC error: {result['error'].get('message', 'Unknown error')}",
                )

            # Get new block number after mining
            block_response = await client.post(
                rpc_url,
                json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 2},
                timeout=10.0,
            )
            block_result = block_response.json()

            if "error" in block_result:
                raise HTTPException(
                    status_code=400,
                    detail=f"RPC error: {block_result['error'].get('message', 'Unknown error')}",
                )

            new_block_number = int(block_result.get("result", "0x0"), 16)

            return MineBlocksResponse(
                blocksMined=blocks, newBlockNumber=new_block_number, status="success"
            )

    except httpx.TimeoutException:
        raise HTTPException(status_code=400, detail="Timeout connecting to Anvil RPC")
    except httpx.RequestError as e:
        raise HTTPException(status_code=400, detail=f"Failed to connect to Anvil RPC: {str(e)}")


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
        "--port",
        str(port),
        "--chain-id",
        str(chain_id),
        "--gas-limit",
        str(gas_limit),
        "--host",
        "0.0.0.0",
        "--no-mining",
    ]

    if block_time > 0:
        cmd.extend(["--block-time", str(block_time)])

    if mnemonic and mnemonic.strip():
        cmd.extend(["--mnemonic", mnemonic])

    try:
        import fcntl

        anvil_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid if os.name != "nt" else None,
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
            raise HTTPException(status_code=500, detail=f"Failed to start Anvil: {output}")

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
            anvil_accounts.append(
                PrivateKeyInfo(address=addresses[i][1], privateKey=private_keys[i][1])
            )

        anvil_start_time = time.time()
        anvil_config = {
            "port": port,
            "chainId": chain_id,
            "blockTime": block_time,
            "gasLimit": gas_limit,
            "mnemonic": mnemonic,
            "autoMine": False,  # --no-auto-mine disables auto-mining by default
        }

        asyncio.create_task(capture_anvil_output())

        return AnvilRestartResponse(
            pid=anvil_process.pid,
            port=port,
            chainId=chain_id,
            status="running",
            message="Anvil instance restarted successfully",
        )

    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Anvil not found. Ensure Foundry is installed.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart Anvil: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
