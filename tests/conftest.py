"""Shared test fixtures for server tests."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from llmling.config.models import Config, GlobalSettings, TextResource, ToolConfig
from llmling.config.runtime import RuntimeConfig
from llmling.processors.registry import ProcessorRegistry
from llmling.prompts.models import PromptMessage, StaticPrompt
from llmling.prompts.registry import PromptRegistry
from llmling.resources import ResourceLoaderRegistry
from llmling.resources.registry import ResourceRegistry
from llmling.testing.processors import multiply, uppercase_text
from llmling.testing.tools import analyze_ast, example_tool
from llmling.tools.registry import ToolRegistry
from mcp.shared.memory import create_client_server_memory_streams
import pytest
import yaml

from mcp_server_llmling import LLMLingServer, constants
from mcp_server_llmling.mcp_inproc_session import MCPInProcSession


if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from pathlib import Path

EXAMPLE_TOOL = "llmling.testing.tools.example_tool"


@pytest.fixture
def base_config() -> Config:
    """Create minimal test configuration."""
    return Config(
        version="1.0.0",
        global_settings=GlobalSettings(),
        resources={},
        context_processors={},
        resource_groups={},
    )


@pytest.fixture
def runtime_config(base_config: Config) -> RuntimeConfig:
    """Create test runtime configuration."""
    # Create registries first
    loader_registry = ResourceLoaderRegistry()
    processor_registry = ProcessorRegistry()

    # Create dependent registries
    resource_registry = ResourceRegistry(
        loader_registry=loader_registry,
        processor_registry=processor_registry,
    )
    prompt_registry = PromptRegistry()
    tool_registry = ToolRegistry()

    loader_registry.register_default_loaders()
    # Register test processors
    processor_registry.register("multiply", multiply)
    processor_registry.register("uppercase", uppercase_text)

    # Register test tools
    tool_registry.register("example", example_tool)
    tool_registry.register("analyze", analyze_ast)

    return RuntimeConfig(
        config=base_config,
        loader_registry=loader_registry,
        processor_registry=processor_registry,
        resource_registry=resource_registry,
        prompt_registry=prompt_registry,
        tool_registry=tool_registry,
    )


@pytest.fixture
async def server(runtime_config: RuntimeConfig) -> AsyncIterator[LLMLingServer]:
    """Create configured test server."""
    server = LLMLingServer(runtime=runtime_config, name=constants.SERVER_NAME)

    try:
        yield server
    finally:
        await server.shutdown()


@pytest.fixture
async def running_server(
    server: LLMLingServer,
) -> AsyncIterator[tuple[LLMLingServer, tuple[Any, Any]]]:
    """Create and start test server with memory streams."""
    async with create_client_server_memory_streams() as (client_streams, server_streams):
        init_opts = server.server.create_initialization_options()
        coro = server.server.run(server_streams[0], server_streams[1], init_opts)
        task = asyncio.create_task(coro)
        try:
            yield server, client_streams
        finally:
            task.cancel()
            await server.shutdown()


@pytest.fixture
async def client() -> MCPInProcSession:
    """Create a test client."""
    return MCPInProcSession()


@pytest.fixture
def test_config() -> Config:
    """Create test configuration."""
    msgs = [PromptMessage(role="system", content="test")]
    prompt = StaticPrompt(name="test", description="test", messages=msgs)
    resource = TextResource(content="Test content", description="Test resource")
    tool_cfg = ToolConfig(
        import_path=EXAMPLE_TOOL, name="example", description="Test tool"
    )
    return Config(
        version="1.0",
        prompts={"test": prompt},
        resources={"test": resource},
        tools={"example": tool_cfg},
    )


@pytest.fixture
async def config_file(tmp_path: Path, test_config: Config) -> Path:
    """Create temporary config file."""
    config_path = tmp_path / "test_config.yml"
    content = test_config.model_dump(exclude_none=True)
    data = yaml.dump(content)
    config_path.write_text(data)
    return config_path


@pytest.fixture
async def configured_client(config_file: Path) -> AsyncIterator[MCPInProcSession]:
    """Create client with test configuration."""
    client = MCPInProcSession(config_path=str(config_file))
    try:
        await client.start()
        response = await client.do_handshake()
        assert response["serverInfo"]["name"] == constants.SERVER_NAME
        yield client
    finally:
        await client.close()
