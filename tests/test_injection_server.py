"""Tests for the config injection server."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fastapi.testclient import TestClient
import httpx
from llmling import Config, RuntimeConfig
from llmling.config.models import TextResource
import pytest

from mcp_server_llmling import LLMLingServer
from mcp_server_llmling.injection.models import (
    ComponentResponse,
    ConfigUpdateRequest,
    WebSocketMessage,
)
from mcp_server_llmling.log import get_logger


logger = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


STATUS_OK = 200
STATUS_ERROR = 400


@pytest.fixture
def config() -> Config:
    """Create a basic test configuration."""
    return Config.model_validate({
        "global_settings": {},
        "resources": {"test_resource": {"type": "text", "content": "Initial content"}},
        "tools": {"test_tool": {"import_path": "llmling.testing.tools.example_tool"}},
    })


@pytest.fixture
async def runtime(config: Config) -> AsyncGenerator[RuntimeConfig, None]:
    """Create a runtime config."""
    async with RuntimeConfig.from_config(config) as runtime:
        yield runtime


@pytest.fixture
async def server(runtime: RuntimeConfig) -> AsyncGenerator[LLMLingServer, None]:
    """Create server instance."""
    # Random port
    server = LLMLingServer(runtime, enable_injection=True, injection_port=0)
    assert server.injection_server
    await server.injection_server.start()  # Start server directly, no task needed
    try:
        yield server
    finally:
        await server.injection_server.stop()
        await server.shutdown()


@pytest.fixture
async def client(server: LLMLingServer) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Create HTTP client connected to injection server."""
    assert server.injection_server
    base_url = f"http://localhost:{server.injection_server.port}"

    async with httpx.AsyncClient(base_url=base_url) as client:
        yield client


@pytest.mark.asyncio
async def test_list_components(client: httpx.AsyncClient) -> None:
    """Test listing all components."""
    response = await client.get("/components")
    assert response.status_code == STATUS_OK
    data = response.json()
    assert "resources" in data
    assert "tools" in data
    assert "prompts" in data
    assert "test_resource" in data["resources"]
    assert "test_tool" in data["tools"]


@pytest.mark.asyncio
async def test_add_resource(client: httpx.AsyncClient) -> None:
    """Test adding a resource."""
    payload = {"type": "text", "content": "New content"}
    response = await client.post("/resources/new_resource", json=payload)
    assert response.status_code == STATUS_OK
    data = ComponentResponse.model_validate(response.json())
    assert data.status == "success"
    assert data.component_type == "resource"
    assert data.name == "new_resource"

    # Verify resource was added
    response = await client.get("/resources")
    assert response.status_code == STATUS_OK
    resources = response.json()
    assert "new_resource" in resources


# @pytest.mark.asyncio
# async def test_add_invalid_resource(client: httpx.AsyncClient) -> None:
#     """Test adding an invalid resource."""
#     response = await client.post(
#         "/resources/bad_resource",
#         # Send an invalid resource structure that will fail pydantic validation
#         json={
#             "type": "text",  # valid type
#             "invalid_field": "Bad",  # but invalid structure
#             # missing required 'content' field for TextResource
#         },
#     )
#     assert response.status_code == STATUS_ERROR


@pytest.mark.asyncio
async def test_bulk_update(client: httpx.AsyncClient) -> None:
    """Test bulk component updates."""
    from llmling.config.models import ToolConfig

    update = ConfigUpdateRequest(
        resources={
            "bulk_res1": TextResource(content="Bulk 1"),
            "bulk_res2": TextResource(content="Bulk 2"),
        },
        tools={"bulk_tool": ToolConfig(import_path="llmling.testing.tools.example_tool")},
    )

    response = await client.post("/bulk-update", json=update.model_dump())
    assert response.status_code == STATUS_OK
    data = response.json()
    assert data["summary"]["success"] == 3  # noqa: PLR2004
    assert data["summary"]["error"] == 0

    # Verify components were added
    response = await client.get("/components")
    data = response.json()
    assert "bulk_res1" in data["resources"]
    assert "bulk_res2" in data["resources"]
    assert "bulk_tool" in data["tools"]


@pytest.mark.asyncio
async def test_websocket_communication(server: LLMLingServer) -> None:
    """Test WebSocket updates."""
    assert server.injection_server
    test_client = TestClient(server.injection_server.app)

    # Test update message
    with test_client.websocket_connect("/ws") as websocket:
        # Send update request
        resource = TextResource(content="WebSocket content")
        update_request = ConfigUpdateRequest(resources={"ws_resource": resource})
        data = update_request.model_dump()
        message = WebSocketMessage(type="update", data=data, request_id="test-1")

        logger.info("Sending message: %s", message.model_dump())
        websocket.send_json(message.model_dump())

        response = websocket.receive_json()
        logger.info("Received response: %s", response)

        # Print error details if present
        if response["type"] == "error":
            logger.error("Error message: %s", response.get("message"))

        assert response["type"] == "success"
        assert response["request_id"] == "test-1"


@pytest.mark.asyncio
async def test_concurrent_updates(client: httpx.AsyncClient) -> None:
    """Test concurrent updates."""

    async def add_resource(name: str) -> httpx.Response:
        data = {"type": "text", "content": f"Content {name}"}
        return await client.post(f"/resources/{name}", json=data)

    # Send multiple concurrent requests
    tasks = [add_resource(f"concurrent_{i}") for i in range(5)]
    responses = await asyncio.gather(*tasks)

    # Verify all succeeded
    assert all(r.status_code == STATUS_OK for r in responses)

    # Check all resources exist
    response = await client.get("/resources")
    resources = response.json()
    assert all(f"concurrent_{i}" in resources for i in range(5))
