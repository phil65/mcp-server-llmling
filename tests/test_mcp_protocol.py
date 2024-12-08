"""Tests for MCP protocol implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mcp_server_llmling import constants


if TYPE_CHECKING:
    from mcp_server_llmling.mcp_inproc_session import MCPInProcSession


@pytest.mark.asyncio
async def test_mcp_resource_operations(configured_client: MCPInProcSession) -> None:
    """Test MCP resource operations."""
    # List resources
    response = await configured_client.send_request("resources/list")
    assert "resources" in response
    resource_list = response["resources"]
    assert len(resource_list) >= 1
    test_resource = next(r for r in resource_list if r["description"] == "Test resource")

    # Read resource content
    response = await configured_client.send_request(
        "resources/read",
        {"uri": test_resource["uri"]},
    )
    assert "contents" in response
    assert len(response["contents"]) == 1
    content = response["contents"][0]
    assert content["text"] == "Test content"
    assert content["mimeType"] == "text/plain"


@pytest.mark.asyncio
async def test_mcp_tool_operations(configured_client: MCPInProcSession) -> None:
    """Test MCP tool operations."""
    # List tools
    tools = await configured_client.list_tools()
    assert len(tools) >= 1
    _example_tool = next(t for t in tools if t["name"] == "example")

    # Call tool
    args = {"text": "test", "repeat": 2}
    result = await configured_client.call_tool("example", args)
    assert result["content"][0]["text"] == "testtest"


@pytest.mark.asyncio
async def test_mcp_prompt_operations(configured_client: MCPInProcSession) -> None:
    """Test MCP prompt operations."""
    # List prompts
    prompts = await configured_client.list_prompts()
    assert len(prompts) >= 1
    test_prompt = next(p for p in prompts if p["name"] == "test")

    # Get prompt
    params = {"name": test_prompt["name"], "arguments": {"test": "value"}}
    result = await configured_client.send_request("prompts/get", params)
    assert "messages" in result
    assert len(result["messages"]) >= 1
    assert result["messages"][0]["content"]["text"] == "test"


@pytest.mark.asyncio
async def test_mcp_error_handling(configured_client: MCPInProcSession) -> None:
    """Test MCP error response format."""
    # Test with invalid tool
    params = {"name": "nonexistent"}
    response = await configured_client.send_request("tools/call", params)
    assert "content" in response
    assert len(response["content"]) == 1
    assert "not found" in response["content"][0]["text"].lower()

    # Test with invalid prompt
    params = {"name": "nonexistent"}
    with pytest.raises(Exception) as exc_info:  # noqa: PT011
        await configured_client.send_request("prompts/get", params)
    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_mcp_handshake(configured_client: MCPInProcSession) -> None:
    """Test MCP protocol handshake."""
    # Do another handshake to explicitly test it
    init_response = await configured_client.do_handshake()

    # Verify server info
    assert "serverInfo" in init_response
    server_info = init_response["serverInfo"]
    assert server_info["name"] == constants.SERVER_NAME
    assert "version" in server_info

    # Verify capabilities
    assert "capabilities" in init_response
    capabilities = init_response["capabilities"]
    assert "resources" in capabilities
    assert "prompts" in capabilities
    assert "tools" in capabilities
    assert "logging" in capabilities


@pytest.mark.asyncio
async def test_mcp_streaming(configured_client: MCPInProcSession) -> None:
    """Test MCP streaming operations."""
    # Call tool with progress tracking
    args = {"text": "test", "repeat": 2}  # Will repeat 'test' twice
    result = await configured_client.call_tool("example", args, with_progress=True)
    assert "content" in result
    assert len(result["content"]) == 1
    assert result["content"][0]["text"] == "testtest"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
