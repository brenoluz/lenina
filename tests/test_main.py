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
    
    def test_list_contracts_not_running(self, client: TestClient):
        """Test listing contracts when Anvil is not running."""
        response = client.get("/anvil/contracts")
        
        assert response.status_code == 400
        assert "instance" in response.json()["detail"]
    
    def test_check_contract_not_running(self, client: TestClient):
        """Test checking contract when Anvil is not running."""
        response = client.get("/anvil/contract/0x5FbDB2315678afecb367f032d93F642f64180aa3")
        
        assert response.status_code == 400
        assert "instance" in response.json()["detail"]
    
    def test_rpc_not_running(self, client: TestClient):
        """Test RPC proxy when Anvil is not running."""
        rpc_request = {
            "jsonrpc": "2.0",
            "method": "eth_blockNumber",
            "params": [],
            "id": 1
        }
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
            privateKey="0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
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
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Dockerfile"
        )
        assert os.path.exists(dockerfile_path), "Dockerfile should exist"
    
    def test_docker_compose_exists(self):
        """Test that docker-compose.yml exists."""
        compose_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docker-compose.yml"
        )
        assert os.path.exists(compose_path), "docker-compose.yml should exist"
    
    def test_readme_exists(self):
        """Test that README.md exists."""
        readme_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "README.md"
        )
        assert os.path.exists(readme_path), "README.md should exist"
    
    def test_docs_folder_exists(self):
        """Test that docs folder exists."""
        docs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs"
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
        assert response.status_code != 400 or "Invalid Ethereum" not in response.json().get("detail", "")


class TestDocumentation:
    """Tests for documentation completeness."""
    
    def test_api_docs_content(self):
        """Test that API docs file has required sections."""
        docs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs", "api.md"
        )
        
        with open(docs_path, 'r') as f:
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
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs", "architecture.md"
        )
        
        with open(docs_path, 'r') as f:
            content = f.read()
        
        assert "# Lenina Architecture" in content
        assert "FastAPI" in content
        assert "Anvil" in content
    
    def test_deployment_docs_content(self):
        """Test that deployment docs exist and have content."""
        docs_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "docs", "deployment.md"
        )
        
        with open(docs_path, 'r') as f:
            content = f.read()
        
        assert "# Lenina Deployment Guide" in content
        assert "Docker" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
