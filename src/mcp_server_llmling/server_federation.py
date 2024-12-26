"""Models and handlers for MCP server federation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, Literal

from pydantic import BaseModel, Field

from mcp_server_llmling.log import get_logger
from mcp_server_llmling.sse_client import SSEClientConfig, SSEMCPClient


if TYPE_CHECKING:
    from collections.abc import Sequence

    from mcp.types import Prompt, Resource, Tool

logger = get_logger(__name__)


class ExternalServerBase(BaseModel):
    """Base configuration for external MCP server."""

    type: str = Field(init=False)
    name: str
    transport: Literal["sse"] = "sse"  # for future extension to other transports


class URLServerConfig(ExternalServerBase):
    """Configuration for connecting to an existing MCP server via URL."""

    type: Literal["url"] = Field("url", init=False)
    url: str


class CommandServerConfig(ExternalServerBase):
    """Configuration for starting and connecting to an MCP server via command."""

    type: Literal["command"] = Field("command", init=False)
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)


ExternalServerConfig = Annotated[
    URLServerConfig | CommandServerConfig,
    Field(discriminator="type"),
]


class FederatedServers(BaseModel):
    """Configuration section for federated servers."""

    external_servers: dict[str, ExternalServerConfig] = {}


@dataclass
class ConnectedServer:
    """Represents a connected external server."""

    name: str
    config: ExternalServerConfig
    client: SSEMCPClient


class ServerFederation:
    """Manages connections to external MCP servers."""

    def __init__(self) -> None:
        """Initialize federation manager."""
        self.servers: dict[str, ConnectedServer] = {}

    async def connect_servers(self, config: FederatedServers) -> None:
        """Connect to all configured external servers."""
        for name, server_cfg in config.external_servers.items():
            try:
                if server_cfg.transport != "sse":
                    msg = f"Unsupported transport type: {server_cfg.transport}"
                    raise ValueError(msg)  # noqa: TRY301

                match server_cfg:
                    case URLServerConfig():
                        client = SSEMCPClient(SSEClientConfig(server_url=server_cfg.url))
                        await client.start()
                    case CommandServerConfig():
                        msg = "Command-based servers not yet implemented"
                        raise NotImplementedError(msg)  # noqa: TRY301
                    case _:
                        msg = f"Unknown server config type: {server_cfg.type}"
                        raise ValueError(msg)  # noqa: TRY301

                server = ConnectedServer(name=name, config=server_cfg, client=client)
                self.servers[name] = server
                logger.info(
                    "Connected to external server %s (type: %s)",
                    name,
                    server_cfg.type,
                )

            except Exception:
                logger.exception("Failed to connect to external server: %s", name)

    async def close(self) -> None:
        """Close all server connections."""
        for server in self.servers.values():
            try:
                await server.client.close()
            except Exception:
                logger.exception("Error closing connection to %s", server.name)
        self.servers.clear()

    async def list_all_tools(self) -> Sequence[Tool]:
        """List tools from all connected servers."""
        all_tools: list[Tool] = []
        for server in self.servers.values():
            try:
                tools = await server.client.list_tools()
                # TODO: Add server prefix to tool names to avoid conflicts?
                all_tools.extend(tools)
            except Exception:
                logger.exception("Failed to list tools from %s", server.name)
        return all_tools

    async def list_all_resources(self) -> Sequence[Resource]:
        """List resources from all connected servers."""
        all_resources: list[Resource] = []
        for server in self.servers.values():
            try:
                resources = await server.client.list_resources()
                all_resources.extend(resources)
            except Exception:
                logger.exception("Failed to list resources from %s", server.name)
        return all_resources

    async def list_all_prompts(self) -> Sequence[Prompt]:
        """List prompts from all connected servers."""
        all_prompts: list[Prompt] = []
        for server in self.servers.values():
            try:
                prompts = await server.client.list_prompts()
                all_prompts.extend(prompts)
            except Exception:
                logger.exception("Failed to list prompts from %s", server.name)
        return all_prompts

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        """Call a tool on the appropriate server."""
        # TODO: Handle tool name conflicts
        # Could use format like "server_name:tool_name"
        for server in self.servers.values():
            try:
                tools = await server.client.list_tools()
                if any(t.name == name for t in tools):
                    return await server.client.call_tool(name, arguments)
            except Exception:
                logger.exception("Failed to call tool on %s", server.name)

        msg = f"Tool {name} not found on any server"
        raise ValueError(msg)
