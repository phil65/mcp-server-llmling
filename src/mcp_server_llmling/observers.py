"""Observer implementations for converting registry events to MCP notifications."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_server_llmling.log import get_logger


if TYPE_CHECKING:
    from llmling.config.models import BaseResource
    from llmling.prompts.models import BasePrompt
    from llmling.tools.base import LLMCallableTool

    from mcp_server_llmling.server import LLMLingServer

logger = get_logger(__name__)


class ResourceObserver:
    """Converts resource registry events to MCP notifications."""

    def __init__(self, server: LLMLingServer) -> None:
        """Initialize observer with server instance."""
        self.server = server
        registry = server.runtime._resource_registry

        # Connect to registry events
        registry.events.added.connect(self._handle_resource_added)
        registry.events.removed.connect(self._handle_resource_removed)
        registry.events.changed.connect(self._handle_resource_modified)

    def _handle_resource_added(self, key: str, resource: BaseResource) -> None:
        """Handle resource addition."""
        self.server._create_task(self.server.notify_resource_list_changed())

    def _handle_resource_modified(self, key: str, resource: BaseResource) -> None:
        """Handle resource modification."""
        # Get URI for resource change notification
        loader = self.server.runtime.get_resource_loader(resource)
        uri = loader.create_uri(name=key)
        self.server._create_task(self.server.notify_resource_change(uri))

    def _handle_resource_removed(self, key: str, resource: BaseResource) -> None:
        """Handle resource removal."""
        self.server._create_task(self.server.notify_resource_list_changed())


class PromptObserver:
    """Converts prompt registry events to MCP notifications."""

    def __init__(self, server: LLMLingServer) -> None:
        """Initialize observer with server instance."""
        self.server = server
        registry = server.runtime._prompt_registry

        # Connect to registry events
        registry.events.added.connect(self._handle_prompt_added)
        registry.events.removed.connect(self._handle_prompt_removed)
        registry.events.changed.connect(self._handle_prompt_modified)

    def _handle_prompt_added(self, key: str, prompt: BasePrompt) -> None:
        """Handle prompt addition."""
        self.server._create_task(self.server.notify_prompt_list_changed())

    def _handle_prompt_modified(self, key: str, prompt: BasePrompt) -> None:
        """Handle prompt modification."""
        self.server._create_task(self.server.notify_prompt_list_changed())

    def _handle_prompt_removed(self, key: str, prompt: BasePrompt) -> None:
        """Handle prompt removal."""
        self.server._create_task(self.server.notify_prompt_list_changed())


class ToolObserver:
    """Converts tool registry events to MCP notifications."""

    def __init__(self, server: LLMLingServer) -> None:
        """Initialize observer with server instance."""
        self.server = server
        registry = server.runtime._tool_registry

        # Connect to registry events
        registry.events.added.connect(self._handle_tool_added)
        registry.events.removed.connect(self._handle_tool_removed)
        registry.events.changed.connect(self._handle_tool_modified)

    def _handle_tool_added(self, key: str, tool: LLMCallableTool) -> None:
        """Handle tool addition."""
        self.server._create_task(self.server.notify_tool_list_changed())

    def _handle_tool_modified(self, key: str, tool: LLMCallableTool) -> None:
        """Handle tool modification."""
        self.server._create_task(self.server.notify_tool_list_changed())

    def _handle_tool_removed(self, key: str, tool: LLMCallableTool) -> None:
        """Handle tool removal."""
        self.server._create_task(self.server.notify_tool_list_changed())
