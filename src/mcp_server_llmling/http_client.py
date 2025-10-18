"""HTTP-based MCP protocol client implementation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from pydantic import AnyUrl

from mcp_server_llmling.log import get_logger


if TYPE_CHECKING:
    from collections.abc import Sequence

    from mcp.types import Prompt, Resource, Tool

logger = get_logger(__name__)


@dataclass
class HTTPClientConfig:
    """Configuration for HTTP-based MCP client."""

    server_url: str
    protocol_version: str = "0.1"
    client_name: str = "mcp-client"
    client_version: str = "1.0"
    timeout: float = 30.0
    headers: dict[str, str] | None = None


class MCPClientError(Exception):
    """Base exception for MCP client errors."""


class McpConnectionError(MCPClientError):
    """Raised when connection to server fails."""


class ToolError(MCPClientError):
    """Raised when tool execution fails."""


class HTTPMCPClient:
    """High-level MCP protocol client for connecting to external servers via HTTP."""

    def __init__(self, config: HTTPClientConfig) -> None:
        """Initialize client with configuration.

        Args:
            config: Client configuration including server URL
        """
        self.config = config
        self._session: ClientSession | None = None
        self._context_manager = streamablehttp_client(
            url=self.config.server_url,
            headers=self.config.headers,
            timeout=self.config.timeout,
        )

    async def start(self) -> None:
        """Connect to server and perform handshake."""
        try:
            # Connect via streamablehttp_client and get streams

            streams_and_callback = await self._context_manager.__aenter__()
            read_stream, write_stream, _get_session_id = streams_and_callback

            self._session = ClientSession(read_stream, write_stream)
            await self._session.__aenter__()
            result = await self._session.initialize()
            msg = "Connected to MCP server at %s (protocol version %s)"
            logger.info(msg, self.config.server_url, result.protocolVersion)
        except Exception as exc:
            # Clean up on failure
            try:
                await self._context_manager.__aexit__(type(exc), exc, exc.__traceback__)
            except Exception:
                logger.exception("Error during cleanup after connection failure")
            msg = "Failed to connect to server"
            raise McpConnectionError(msg) from exc

    async def close(self) -> None:
        """Close connection to server."""
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                logger.exception("Error closing session")
            finally:
                self._session = None

        try:
            await self._context_manager.__aexit__(None, None, None)
        except Exception:
            logger.exception("Error closing context manager")

    @property
    def session(self) -> ClientSession:
        """Get active session."""
        if not self._session:
            msg = "Not connected to server"
            raise RuntimeError(msg)
        return self._session

    async def list_tools(self) -> Sequence[Tool]:
        """List available tools."""
        try:
            result = await self.session.list_tools()
        except Exception as exc:
            msg = "Failed to list tools"
            raise ToolError(msg) from exc
        else:
            return result.tools

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> Any:
        """Call a tool with given arguments."""
        timeout = timeout or self.config.timeout
        try:
            async with asyncio.timeout(timeout):
                result = await self.session.call_tool(name, arguments)
                return result.content
        except TimeoutError as exc:
            msg = f"Tool execution timed out after {timeout}s"
            raise ToolError(msg) from exc
        except Exception as exc:
            msg = f"Tool execution failed: {exc}"
            raise ToolError(msg) from exc

    async def list_resources(self) -> Sequence[Resource]:
        """List available resources."""
        try:
            result = await self.session.list_resources()
        except Exception as exc:
            msg = "Failed to list resources"
            raise MCPClientError(msg) from exc
        else:
            return result.resources

    async def list_prompts(self) -> Sequence[Prompt]:
        """List available prompts."""
        try:
            result = await self.session.list_prompts()
        except Exception as exc:
            msg = "Failed to list prompts"
            raise MCPClientError(msg) from exc
        else:
            return result.prompts

    async def subscribe_resource(self, uri: str | AnyUrl) -> None:
        """Subscribe to resource updates."""
        try:
            if isinstance(uri, str):
                uri = AnyUrl(uri)
            await self.session.subscribe_resource(uri)
        except Exception as exc:
            msg = "Failed to subscribe to resource"
            raise MCPClientError(msg) from exc

    async def unsubscribe_resource(self, uri: str | AnyUrl) -> None:
        """Unsubscribe from resource updates."""
        try:
            if isinstance(uri, str):
                uri = AnyUrl(uri)
            await self.session.unsubscribe_resource(uri)
        except Exception as exc:
            msg = "Failed to unsubscribe from resource"
            raise MCPClientError(msg) from exc

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        """Async context manager exit."""
        await self.close()


if __name__ == "__main__":

    async def main() -> None:
        """Example usage of HTTPMCPClient."""
        config = HTTPClientConfig(server_url="http://localhost:3001")

        async with HTTPMCPClient(config) as client:
            # List available tools
            tools = await client.list_tools()
            print("Available tools:", tools)

            # Call a tool
            result = await client.call_tool("example_tool", {"arg": "value"})
            print("Tool result:", result)

    asyncio.run(main())
