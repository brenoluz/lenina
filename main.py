"""
Lenina - Anvil RESTful Management API
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import subprocess
import asyncio
import re
import os
import signal
import time
from datetime import datetime

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


class ContractInfo(BaseModel):
    """Information about a deployed contract"""
    address: str
    bytecodeHash: str
    deploymentBlock: int
    abi: Optional[Dict] = None


# Global state
anvil_process: Optional[subprocess.Popen] = None
anvil_start_time: Optional[float] = None
anvil_config: Optional[Dict[str, Any]] = None
deployed_contracts: List[Dict[str, Any]] = []


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


@app.post("/anvil/start", response_model=AnvilStartResponse)
async def start_anvil(config: Optional[AnvilConfig] = None):
    """
    Start an Anvil instance with optional configuration.

    Returns 400 if Anvil is already running.
    Returns 500 if Anvil fails to start.
    """
    global anvil_process, anvil_start_time, anvil_config

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
    ]

    if block_time > 0:
        cmd.extend(["--block-time", str(block_time)])

    if mnemonic:
        cmd.extend(["--mnemonic", mnemonic])

    try:
        # Start Anvil process
        anvil_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid if os.name != "nt" else None
        )

        # Wait a moment for Anvil to start
        await asyncio.sleep(0.5)

        # Check if process is still running
        if anvil_process.poll() is not None:
            # Process failed to start
            stderr_output = anvil_process.stderr.read() if anvil_process.stderr else ""
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start Anvil: {stderr_output}"
            )

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
async def stop_anvil():
    """
    Stop a running Anvil instance.

    Returns 400 if no Anvil instance is running.
    Gracefully terminates the process.
    """
    global anvil_process, anvil_start_time, anvil_config

    # Check if Anvil is running
    if anvil_process is None or anvil_process.poll() is not None:
        raise HTTPException(
            status_code=400,
            detail="No Anvil instance is running"
        )

    try:
        # Get process group for clean termination
        pid = anvil_process.pid

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

        return AnvilStopResponse(
            status="stopped",
            message=f"Anvil instance (PID {pid}) has been stopped"
        )

    except subprocess.TimeoutExpired:
        # Force kill if graceful shutdown fails
        if os.name != "nt":
            os.killpg(os.getpgid(anvil_process.pid), signal.SIGKILL)
        else:
            anvil_process.kill()

        anvil_process = None
        anvil_start_time = None
        anvil_config = None

        return AnvilStopResponse(
            status="stopped",
            message=f"Anvil instance was forcefully stopped"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop Anvil: {str(e)}"
        )


@app.post("/anvil/restart", response_model=AnvilRestartResponse)
async def restart_anvil(config: Optional[AnvilConfig] = None):
    """
    Restart a running Anvil instance.

    Preserves configuration from previous run or accepts new config.
    Returns 200 with new process details on success.
    """
    global anvil_process, anvil_start_time, anvil_config

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
    ]

    if block_time > 0:
        cmd.extend(["--block-time", str(block_time)])

    if mnemonic:
        cmd.extend(["--mnemonic", mnemonic])

    try:
        anvil_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            preexec_fn=os.setsid if os.name != "nt" else None
        )

        await asyncio.sleep(0.5)

        if anvil_process.poll() is not None:
            stderr_output = anvil_process.stderr.read() if anvil_process.stderr else ""
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start Anvil: {stderr_output}"
            )

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
