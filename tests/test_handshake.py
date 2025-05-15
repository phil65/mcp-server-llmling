"""Test server lifecycle using different approaches."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import TYPE_CHECKING

from llmling import Config, RuntimeConfig
from mcp.shared.memory import create_connected_server_and_client_session
import pytest

from mcp_server_llmling import LLMLingServer, constants


if TYPE_CHECKING:
    from mcp_server_llmling.mcp_inproc_session import MCPInProcSession


INFO = {"name": "test-client", "version": "1.0"}
PARAMS = {
    "protocolVersion": "2025-03-26",
    "capabilities": {},
    "clientInfo": {"name": "test-client", "version": "1.0"},
}


@pytest.mark.asyncio
async def test_server_lifecycle_handshake_client(client: MCPInProcSession) -> None:
    """Test server lifecycle using MCPInProcSession."""
    try:
        await client.start()
        await asyncio.sleep(0.5)
        # Initialize connection
        init_response = await client.send_request("initialize", PARAMS)
        assert isinstance(init_response, dict)
        assert "serverInfo" in init_response
        server_info = init_response["serverInfo"]
        assert server_info["name"] == constants.SERVER_NAME
        assert "version" in server_info
        assert "capabilities" in init_response

        # Send initialized notification
        await client.send_notification("notifications/initialized", {})

        # Test functionality
        tools = await client.list_tools()
        assert isinstance(tools, list)
        resources = await client.list_resources()
        assert isinstance(resources, list)
        prompts = await client.list_prompts()
        assert isinstance(prompts, list)
    finally:
        await client.close()


@pytest.mark.anyio
async def test_server_lifecycle_test_session():
    # Minimal config for LLMLingServer
    config = Config()
    runtime = RuntimeConfig.from_config(config=config)
    server = LLMLingServer(runtime)

    async with create_connected_server_and_client_session(server.server) as client:
        # Handshake
        result = await client.initialize()
        assert result.serverInfo.name == server.name

        # List tools
        tools = await client.list_tools()
        assert isinstance(tools.tools, list)

        # List resources
        resources = await client.list_resources()
        assert isinstance(resources.resources, list)

        # List prompts
        prompts = await client.list_prompts()
        assert isinstance(prompts.prompts, list)


@pytest.mark.asyncio
async def test_server_lifecycle_direct(
    runtime_config: RuntimeConfig,
    server: LLMLingServer,
) -> None:
    """Test server lifecycle using direct method calls."""
    try:
        # Start runtime components
        await runtime_config.startup()

        # Test direct access
        tools = runtime_config.get_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0  # Should have our test tools

        resources = runtime_config.list_resource_names()
        assert isinstance(resources, list)

        prompts = runtime_config.list_prompt_names()
        assert isinstance(prompts, list)

    finally:
        await runtime_config.shutdown()
        await server.shutdown()


@pytest.mark.asyncio
async def test_server_lifecycle_subprocess() -> None:
    """Test server lifecycle using raw subprocess."""
    process = await asyncio.create_subprocess_exec(
        *constants.SERVER_CMD,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    # Start stderr reader task
    async def read_stderr() -> None:
        assert process.stderr
        while True:
            line = await process.stderr.readline()
            if not line:
                break
            print(f"Server stderr: {line.decode().strip()}")

    stderr_task = asyncio.create_task(read_stderr())

    try:
        assert process.stdin
        assert process.stdout
        await asyncio.sleep(0.5)  # Give server time to start

        # Send initialize request
        request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": PARAMS}
        process.stdin.write(json.dumps(request).encode() + b"\n")
        await process.stdin.drain()

        # Read until we get a valid JSON response
        while True:
            response = await process.stdout.readline()
            if not response:
                msg = "No response from server"
                raise RuntimeError(msg)

            try:
                result = json.loads(response.decode())
                assert "result" in result
                assert "serverInfo" in result["result"]
                assert result["result"]["serverInfo"]["name"] == constants.SERVER_NAME
                break  # Valid response found
            except json.JSONDecodeError:
                continue  # Skip non-JSON lines

    finally:
        # Cleanup
        stderr_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await stderr_task
        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=1.0)
        except TimeoutError:
            process.kill()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
