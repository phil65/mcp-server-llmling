from __future__ import annotations

import pytest

from mcp_server_llmling.mcp_inproc_session import MCPInProcSession


@pytest.mark.asyncio
async def test_resource_to_tool_workflow() -> None:
    """Test loading a resource and using it with a tool."""
    client = MCPInProcSession()
    try:
        # Start server
        await client.start()

        # Do handshake
        init_response = await client.send_request(
            "initialize",
            {
                "protocolVersion": "0.1",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"},
                "processId": None,
                "rootUri": None,
                "workspaceFolders": None,
            },
        )
        assert "serverInfo" in init_response

        # Send initialized notification
        await client.send_notification("notifications/initialized", {})

        # List tools
        tools_response = await client.send_request("tools/list")
        assert "tools" in tools_response

        # Call analyze tool
        result = await client.send_request(
            "tools/call",
            {"name": "analyze", "arguments": {"code": "def test():\n    return 42\n"}},
        )
        assert isinstance(result, dict)

    finally:
        await client.close()
