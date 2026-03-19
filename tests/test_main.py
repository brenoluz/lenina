"""
Integration tests for Lenina - Anvil RESTful Management API

Run tests:
    pytest tests/test_main.py -v

Run with coverage:
    pytest tests/test_main.py --cov=main --cov-report=html
"""

import os
import sys
from typing import Iterator

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from main import app
from fastapi.testclient import TestClient
import pytest  # type: ignore


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    def test_health_check(self, client: TestClient):
        """Test that health endpoint returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_health_check_timestamp_format(self, client: TestClient):
        """Test that timestamp is in ISO format."""
        response = client.get("/health")
        data = response.json()

        # ISO format: YYYY-MM-DDTHH:MM:SS.ffffff
        assert "T" in data["timestamp"]
        assert len(data["timestamp"]) > 10


class TestAnvilStatusWithoutInstance:
    """Tests for endpoints when Anvil is not running."""

    def test_status_anvil_not_running(self, client: TestClient):
        """Test status endpoint when Anvil is not running."""
        response = client.get("/anvil/status")

        assert response.status_code == 200
        data = response.json()
        assert data["running"] is False
        assert data["pid"] is None
        assert data["uptime"] is None
        assert data["port"] is None

    def test_stop_anvil_not_running(self, client: TestClient):
        """Test stopping Anvil when not running returns 400."""
        response = client.post("/anvil/stop")

        assert response.status_code == 400
        assert "instance" in response.json()["detail"]

    def test_get_keys_not_running(self, client: TestClient):
        """Test getting keys when Anvil is not running."""
        response = client.get("/anvil/keys")

        assert response.status_code == 400
        assert "instance" in response.json()["detail"]

    def test_get_config_not_running(self, client: TestClient):
        """Test getting config when Anvil is not running."""
        response = client.get("/anvil/config")

        assert response.status_code == 400
        assert "instance" in response.json()["detail"]

    def test_check_contract_not_running(self, client: TestClient):
        """Test checking contract when Anvil is not running."""
        response = client.get("/anvil/contract/0x5FbDB2315678afecb367f032d93F642f64180aa3")

        assert response.status_code == 400
        assert "instance" in response.json()["detail"]

    def test_rpc_not_running(self, client: TestClient):
        """Test RPC proxy when Anvil is not running."""
        rpc_request = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
        response = client.post("/anvil/rpc", json=rpc_request)

        assert response.status_code == 400
        assert "instance" in response.json()["detail"]


class TestPydanticModels:
    """Tests for Pydantic request/response models."""

    def test_anvil_config_defaults(self):
        """Test AnvilConfig model with default values."""
        from main import AnvilConfig

        config = AnvilConfig()
        assert config.port == 8545
        assert config.chainId == 31337
        assert config.blockTime == 0
        assert config.gasLimit == 30000000
        assert config.mnemonic is None

    def test_anvil_config_custom_values(self):
        """Test AnvilConfig model with custom values."""
        from main import AnvilConfig

        config = AnvilConfig(port=9000, chainId=1337)
        assert config.port == 9000
        assert config.chainId == 1337

    def test_anvil_start_response(self):
        """Test AnvilStartResponse model."""
        from main import AnvilStartResponse

        response = AnvilStartResponse(pid=123, port=8545, chainId=31337, status="running")
        assert response.pid == 123
        assert response.port == 8545
        assert response.chainId == 31337
        assert response.status == "running"

    def test_anvil_stop_response(self):
        """Test AnvilStopResponse model."""
        from main import AnvilStopResponse

        response = AnvilStopResponse(status="stopped", message="Test message")
        assert response.status == "stopped"
        assert response.message == "Test message"

    def test_private_key_info(self):
        """Test PrivateKeyInfo model."""
        from main import PrivateKeyInfo

        account = PrivateKeyInfo(
            address="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
            privateKey="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
        )
        assert account.address.startswith("0x")
        assert account.privateKey.startswith("0x")

    def test_rpc_request(self):
        """Test RpcRequest model."""
        from main import RpcRequest

        request = RpcRequest(method="eth_blockNumber", params=[], id=1)
        assert request.jsonrpc == "2.0"
        assert request.method == "eth_blockNumber"
        assert request.params == []
        assert request.id == 1

    def test_rpc_response(self):
        """Test RpcResponse model."""
        from main import RpcResponse

        response = RpcResponse(result="0x1", id=1)
        assert response.jsonrpc == "2.0"
        assert response.result == "0x1"
        assert response.id == 1


class TestDockerConfiguration:
    """Tests for Docker configuration."""

    def test_dockerfile_exists(self):
        """Test that Dockerfile exists."""
        dockerfile_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Dockerfile"
        )
        assert os.path.exists(dockerfile_path), "Dockerfile should exist"

    def test_docker_compose_exists(self):
        """Test that docker-compose.yml exists."""
        compose_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docker-compose.yml"
        )
        assert os.path.exists(compose_path), "docker-compose.yml should exist"

    def test_readme_exists(self):
        """Test that README.md exists."""
        readme_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "README.md"
        )
        assert os.path.exists(readme_path), "README.md should exist"

    def test_docs_folder_exists(self):
        """Test that docs folder exists."""
        docs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs"
        )
        assert os.path.exists(docs_path), "docs folder should exist"


class TestAPIValidation:
    """Tests for API validation and error handling."""

    def test_invalid_contract_address(self, client: TestClient):
        """Test that invalid contract address returns 400."""
        # Note: Without Anvil running, this will return "not running" error
        # But we can still validate the status code
        response = client.get("/anvil/contract/invalid-address")
        # Will be 400 due to either invalid format or not running
        assert response.status_code == 400

    def test_contract_address_format_valid(self, client: TestClient):
        """Test that valid format address is accepted (even if contract doesn't exist)."""
        # This will fail with "not running" not "invalid address"
        response = client.get("/anvil/contract/0x5FbDB2315678afecb367f032d93F642f64180aa3")
        # Should not be a 400 for invalid format
        assert response.status_code != 400 or "Invalid Ethereum" not in response.json().get(
            "detail", ""
        )


class TestCheckContractWithAnvilRunning:
    """Tests for checking contracts when Anvil is running."""

    def test_check_contract_not_deployed(self, client: TestClient):
        """Test checking an address without a contract returns 404."""
        import time

        start_response = client.post("/anvil/start", json={"port": 9548})
        assert start_response.status_code == 200
        time.sleep(0.3)

        try:
            response = client.get("/anvil/contract/0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266")
            assert response.status_code == 404
            assert "No contract deployed" in response.json()["detail"]
        finally:
            client.post("/anvil/stop")
            time.sleep(0.2)

    def test_check_contract_via_rpc(self, client: TestClient):
        """Test checking contract existence via eth_getCode through RPC proxy."""
        import time
        import requests

        start_response = client.post("/anvil/start", json={"port": 9549})
        assert start_response.status_code == 200
        time.sleep(0.3)

        try:
            port = start_response.json().get("port", 9549)
            rpc_url = f"http://127.0.0.1:{port}"
            time.sleep(0.5)

            accounts_resp = requests.post(
                rpc_url,
                json={"jsonrpc": "2.0", "method": "eth_accounts", "params": [], "id": 1},
                timeout=5,
            )
            accounts = accounts_resp.json().get("result", [])

            if not accounts:
                pytest.skip("No accounts available")

            code_resp = requests.post(
                rpc_url,
                json={
                    "jsonrpc": "2.0",
                    "method": "eth_getCode",
                    "params": [accounts[0], "latest"],
                    "id": 1,
                },
                timeout=5,
            )
            code = code_resp.json().get("result", "0x")
            assert code == "0x", "EOA should have no code"

            contract_response = client.get(f"/anvil/contract/{accounts[0]}")
            assert contract_response.status_code == 404

            rpc_response = client.post(
                "/anvil/rpc", json={"method": "eth_blockNumber", "params": [], "id": 1}
            )
            assert rpc_response.status_code == 200
            assert "result" in rpc_response.json()
        finally:
            client.post("/anvil/stop")
            time.sleep(0.2)


class TestDocumentation:
    """Tests for documentation completeness."""

    def test_api_docs_content(self):
        """Test that API docs file has required sections."""
        docs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "api.md"
        )

        with open(docs_path, "r") as f:
            content = f.read()

        # Check for key sections
        assert "# Lenina API Reference" in content
        assert "GET /health" in content
        assert "POST /anvil/start" in content
        assert "POST /anvil/stop" in content
        assert "GET /anvil/keys" in content

    def test_architecture_docs_content(self):
        """Test that architecture docs exist and have content."""
        docs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "architecture.md"
        )

        with open(docs_path, "r") as f:
            content = f.read()

        assert "# Lenina Architecture" in content
        assert "FastAPI" in content
        assert "Anvil" in content

    def test_deployment_docs_content(self):
        """Test that deployment docs exist and have content."""
        docs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "deployment.md"
        )

        with open(docs_path, "r") as f:
            content = f.read()

        assert "# Lenina Deployment Guide" in content
        assert "Docker" in content


class TestMiningControl:
    """Tests for mining control endpoints (disable, enable, status, mine)."""

    def test_mining_status_without_anvil(self, client: TestClient):
        """Test mining status endpoint when Anvil is not running."""
        response = client.get("/anvil/mining/status")

        assert response.status_code == 400
        assert "instance" in response.json()["detail"]

    def test_mining_disable_without_anvil(self, client: TestClient):
        """Test disabling auto-mining when Anvil is not running."""
        response = client.post("/anvil/mining/disable")

        assert response.status_code == 400
        assert "instance" in response.json()["detail"]

    def test_mining_enable_without_anvil(self, client: TestClient):
        """Test enabling auto-mining when Anvil is not running."""
        response = client.post("/anvil/mining/enable")

        assert response.status_code == 400
        assert "instance" in response.json()["detail"]

    def test_mining_blocks_without_anvil(self, client: TestClient):
        """Test mining blocks when Anvil is not running."""
        response = client.post("/anvil/mining/mine")

        assert response.status_code == 400
        assert "instance" in response.json()["detail"]

    def test_mining_status_with_anvil(self, client: TestClient):
        """Test getting mining status when Anvil is running."""
        import time

        start_response = client.post("/anvil/start", json={"port": 9550})
        assert start_response.status_code == 200
        time.sleep(0.5)

        try:
            status_response = client.get("/anvil/mining/status")
            assert status_response.status_code == 200
            data = status_response.json()

            assert "autoMine" in data
            assert "interval" in data
            assert "blockNumber" in data
            assert isinstance(data["blockNumber"], int)
            assert data["blockNumber"] >= 0
        finally:
            client.post("/anvil/stop")
            time.sleep(0.2)

    def test_mining_disable_and_enable(self, client: TestClient):
        """Test disabling and then enabling auto-mining."""
        import time

        start_response = client.post("/anvil/start", json={"port": 9551})
        assert start_response.status_code == 200
        time.sleep(0.5)

        try:
            # Get initial status
            initial_status = client.get("/anvil/mining/status")
            assert initial_status.status_code == 200

            # Disable auto-mining
            disable_response = client.post("/anvil/mining/disable")
            assert disable_response.status_code == 200
            data = disable_response.json()

            assert data["autoMine"] is False
            assert data["interval"] == 0
            assert "blockNumber" in data

            # Enable auto-mining again
            enable_response = client.post("/anvil/mining/enable")
            assert enable_response.status_code == 200
            data = enable_response.json()

            assert data["autoMine"] is True
            assert "blockNumber" in data
        finally:
            client.post("/anvil/stop")
            time.sleep(0.2)

    def test_mining_manual_blocks(self, client: TestClient):
        """Test manually mining blocks."""
        import time

        start_response = client.post("/anvil/start", json={"port": 9552})
        assert start_response.status_code == 200
        time.sleep(0.5)

        try:
            # Get initial block number
            initial_status = client.get("/anvil/mining/status")
            initial_block = initial_status.json()["blockNumber"]

            # Mine 1 block
            mine_response = client.post("/anvil/mining/mine")
            assert mine_response.status_code == 200
            data = mine_response.json()

            assert data["blocksMined"] == 1
            assert data["newBlockNumber"] == initial_block + 1
            assert data["status"] == "success"

            # Verify block number increased
            new_status = client.get("/anvil/mining/status")
            assert new_status.json()["blockNumber"] == initial_block + 1
        finally:
            client.post("/anvil/stop")
            time.sleep(0.2)

    def test_mining_multiple_blocks(self, client: TestClient):
        """Test mining multiple blocks at once."""
        import time

        start_response = client.post("/anvil/start", json={"port": 9553})
        assert start_response.status_code == 200
        time.sleep(0.5)

        try:
            # Get initial block number
            initial_status = client.get("/anvil/mining/status")
            initial_block = initial_status.json()["blockNumber"]

            # Mine 5 blocks
            mine_response = client.post("/anvil/mining/mine?blocks=5")
            assert mine_response.status_code == 200
            data = mine_response.json()

            assert data["blocksMined"] == 5
            assert data["newBlockNumber"] == initial_block + 5
            assert data["status"] == "success"
        finally:
            client.post("/anvil/stop")
            time.sleep(0.2)

    def test_mining_blocks_with_interval(self, client: TestClient):
        """Test mining blocks with interval between them."""
        import time

        start_response = client.post("/anvil/start", json={"port": 9554})
        assert start_response.status_code == 200
        time.sleep(0.5)

        try:
            # Get initial block number
            initial_status = client.get("/anvil/mining/status")
            initial_block = initial_status.json()["blockNumber"]

            # Mine 3 blocks with 0.1 second interval
            mine_response = client.post("/anvil/mining/mine?blocks=3&interval=0.1")
            assert mine_response.status_code == 200
            data = mine_response.json()

            assert data["blocksMined"] == 3
            assert data["newBlockNumber"] == initial_block + 3
            assert data["status"] == "success"
        finally:
            client.post("/anvil/stop")
            time.sleep(0.2)

    def test_mining_enable_with_interval(self, client: TestClient):
        """Test enabling auto-mining (interval parameter is accepted but interval mining requires restart)."""
        import time

        start_response = client.post("/anvil/start", json={"port": 9555})
        assert start_response.status_code == 200
        time.sleep(0.5)

        try:
            # Enable auto-mining (interval param is accepted but interval mining requires restart with blockTime)
            enable_response = client.post("/anvil/mining/enable", json={"interval": 2})
            assert enable_response.status_code == 200
            data = enable_response.json()

            assert data["autoMine"] is True
            assert "blockNumber" in data

            # Note: Interval mining is set at startup via --block-time
            # The enable endpoint accepts interval param but it's for reporting only
            # To use interval mining, restart Anvil: POST /anvil/restart with {"blockTime": N}
        finally:
            client.post("/anvil/stop")
            time.sleep(0.2)

    def test_mining_disable_manual_mine_workflow(self, client: TestClient):
        """Test complete workflow: disable auto-mining, manually mine, re-enable."""
        import time

        start_response = client.post("/anvil/start", json={"port": 9556})
        assert start_response.status_code == 200
        time.sleep(0.5)

        try:
            # Step 1: Disable auto-mining
            disable_response = client.post("/anvil/mining/disable")
            assert disable_response.status_code == 200
            assert disable_response.json()["autoMine"] is False

            # Step 2: Get block number before manual mining
            before_status = client.get("/anvil/mining/status")
            before_block = before_status.json()["blockNumber"]

            # Step 3: Manually mine 2 blocks
            mine_response = client.post("/anvil/mining/mine?blocks=2")
            assert mine_response.status_code == 200
            assert mine_response.json()["blocksMined"] == 2

            # Step 4: Verify block number increased
            after_status = client.get("/anvil/mining/status")
            assert after_status.json()["blockNumber"] == before_block + 2

            # Step 5: Re-enable auto-mining
            enable_response = client.post("/anvil/mining/enable")
            assert enable_response.status_code == 200
            assert enable_response.json()["autoMine"] is True
        finally:
            client.post("/anvil/stop")
            time.sleep(0.2)

    def test_mining_blocks_validation(self, client: TestClient):
        """Test validation of blocks parameter."""
        import time

        start_response = client.post("/anvil/start", json={"port": 9557})
        assert start_response.status_code == 200
        time.sleep(0.5)

        try:
            # Test with 0 blocks (should fail validation)
            mine_response = client.post("/anvil/mining/mine?blocks=0")
            assert mine_response.status_code == 422  # Validation error

            # Test with negative blocks (should fail validation)
            mine_response = client.post("/anvil/mining/mine?blocks=-1")
            assert mine_response.status_code == 422  # Validation error

            # Test with valid blocks (should succeed)
            mine_response = client.post("/anvil/mining/mine?blocks=1")
            assert mine_response.status_code == 200
        finally:
            client.post("/anvil/stop")
            time.sleep(0.2)


class TestMiningControlPydanticModels:
    """Tests for mining control Pydantic models."""

    def test_mining_config_defaults(self):
        """Test MiningConfig model with default values."""
        from main import MiningConfig

        config = MiningConfig()
        assert config.interval == 0
        assert config.autoMine is None

    def test_mining_config_custom_values(self):
        """Test MiningConfig model with custom values."""
        from main import MiningConfig

        config = MiningConfig(interval=5.0, autoMine=True)
        assert config.interval == 5.0
        assert config.autoMine is True

    def test_mining_status_response(self):
        """Test MiningStatusResponse model."""
        from main import MiningStatusResponse

        response = MiningStatusResponse(autoMine=True, interval=0, blockNumber=100)
        assert response.autoMine is True
        assert response.interval == 0
        assert response.blockNumber == 100

    def test_mine_blocks_response(self):
        """Test MineBlocksResponse model."""
        from main import MineBlocksResponse

        response = MineBlocksResponse(blocksMined=5, newBlockNumber=105, status="success")
        assert response.blocksMined == 5
        assert response.newBlockNumber == 105
        assert response.status == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
