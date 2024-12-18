"""Tests for server event handling."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import Mock

from llmling.config.models import TextResource
from psygnal.containers import EventedDict
import pytest


if TYPE_CHECKING:
    from mcp_server_llmling.server import LLMLingServer


@pytest.fixture
def server() -> LLMLingServer:
    """Create a server instance with mocked notifications."""
    from mcp_server_llmling.server import LLMLingServer

    # Create server with minimal runtime
    mock_runtime = Mock()
    mock_runtime._resource_registry = EventedDict()
    mock_runtime._prompt_registry = EventedDict()
    mock_runtime._tool_registry = EventedDict()
    mock_runtime.get_resource_loader.return_value.create_uri.return_value = "test://uri"

    server = LLMLingServer(mock_runtime)

    async def notify_change(uri: str) -> None: ...
    async def notify_list_changed() -> None: ...

    server.notify_resource_change = Mock(side_effect=notify_change)
    server.notify_resource_list_changed = Mock(side_effect=notify_list_changed)
    server.notify_prompt_list_changed = Mock(side_effect=notify_list_changed)
    server.notify_tool_list_changed = Mock(side_effect=notify_list_changed)

    return server


@pytest.mark.asyncio
async def test_prompt_notifications(server: LLMLingServer) -> None:
    """Test that prompt registry changes trigger notifications."""
    server.runtime._prompt_registry["test"] = Mock()
    await asyncio.sleep(0)
    server.notify_prompt_list_changed.assert_called_once()


@pytest.mark.asyncio
async def test_tool_notifications(server: LLMLingServer) -> None:
    """Test that tool registry changes trigger notifications."""
    server.runtime._tool_registry["test"] = Mock()
    await asyncio.sleep(0)
    server.notify_tool_list_changed.assert_called_once()


@pytest.mark.asyncio
async def test_resource_notifications(server: LLMLingServer) -> None:
    """Test that resource registry changes trigger notifications."""
    resource = TextResource(content="test")

    # Test addition
    server.runtime._resource_registry["test"] = resource
    await asyncio.sleep(0)
    assert server.notify_resource_list_changed.call_count == 1

    # Test modification
    server.runtime._resource_registry["test"] = TextResource(content="modified")
    await asyncio.sleep(0)
    assert server.notify_resource_change.call_count == 1

    # Test removal
    del server.runtime._resource_registry["test"]
    await asyncio.sleep(0)
    assert server.notify_resource_list_changed.call_count == 2  # noqa: PLR2004


@pytest.mark.asyncio
async def test_notification_error_handling(server: LLMLingServer) -> None:
    """Test that notification errors are handled gracefully."""

    async def failing_notify(*args: object) -> None:
        msg = "Test error"
        raise RuntimeError(msg)

    server.notify_resource_list_changed = Mock(side_effect=failing_notify)

    # Should not raise
    server.runtime._resource_registry["test"] = TextResource(content="test")
    await asyncio.sleep(0)
