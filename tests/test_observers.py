"""Tests for server observers."""

from __future__ import annotations

import asyncio
from unittest.mock import Mock

from llmling.config.models import TextResource
from psygnal.containers import EventedDict
import pytest

from mcp_server_llmling.observers import PromptObserver, ResourceObserver, ToolObserver


@pytest.fixture
def mock_server() -> Mock:
    """Create a mock server with required methods."""
    server = Mock()
    server._create_task = Mock(side_effect=asyncio.create_task)

    # Add async notification methods
    async def notify_change(uri: str) -> None: ...
    async def notify_list_changed() -> None: ...

    server.notify_resource_change = Mock(side_effect=notify_change)
    server.notify_resource_list_changed = Mock(side_effect=notify_list_changed)
    server.notify_prompt_list_changed = Mock(side_effect=notify_list_changed)
    server.notify_tool_list_changed = Mock(side_effect=notify_list_changed)

    # Mock runtime config with evented dicts
    mock_runtime = Mock()
    mock_runtime._resource_registry = EventedDict()
    mock_runtime._prompt_registry = EventedDict()
    mock_runtime._tool_registry = EventedDict()
    mock_runtime.get_resource_loader.return_value.create_uri.return_value = "test://uri"
    server.runtime = mock_runtime

    return server


@pytest.mark.asyncio
async def test_prompt_observer_notifications(mock_server: Mock) -> None:
    """Test that prompt observer triggers server notifications."""
    _observer = PromptObserver(mock_server)

    # Emit events directly through the registry
    mock_server.runtime._prompt_registry["test"] = Mock()
    await asyncio.sleep(0)

    mock_server.notify_prompt_list_changed.assert_called_once()
    assert mock_server._create_task.call_count == 1


@pytest.mark.asyncio
async def test_tool_observer_notifications(mock_server: Mock) -> None:
    """Test that tool observer triggers server notifications."""
    _observer = ToolObserver(mock_server)

    # Emit events directly through the registry
    mock_server.runtime._tool_registry["test"] = Mock()
    await asyncio.sleep(0)

    mock_server.notify_tool_list_changed.assert_called_once()
    assert mock_server._create_task.call_count == 1


@pytest.mark.asyncio
async def test_resource_observer_notifications(mock_server: Mock) -> None:
    """Test that resource observer triggers server notifications."""
    _observer = ResourceObserver(mock_server)
    resource = TextResource(content="test")

    # Test addition
    mock_server.runtime._resource_registry["test"] = resource
    await asyncio.sleep(0)

    # Test modification (changing value triggers changed event)
    mock_server.runtime._resource_registry["test"] = TextResource(content="modified")
    await asyncio.sleep(0)

    # Test removal
    del mock_server.runtime._resource_registry["test"]
    await asyncio.sleep(0)

    assert mock_server.notify_resource_change.call_count == 1
    assert mock_server.notify_resource_list_changed.call_count == 2  # noqa: PLR2004
    assert mock_server._create_task.call_count == 3  # noqa: PLR2004


@pytest.mark.asyncio
async def test_observer_error_handling(mock_server: Mock) -> None:
    """Test that observer handles server errors gracefully."""

    async def failing_notify(*args: object) -> None:
        msg = "Test error"
        raise RuntimeError(msg)

    mock_server.notify_resource_list_changed = Mock(side_effect=failing_notify)
    _observer = ResourceObserver(mock_server)

    # Should not raise when registry event occurs
    mock_server.runtime._resource_registry["test"] = TextResource(content="test")
    await asyncio.sleep(0)

    # Verify task was created despite error
    assert mock_server._create_task.call_count == 1
