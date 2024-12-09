"""Resources management page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from mcp_server_llmling.log import get_logger
from mcp_server_llmling.ui.components.header import Header


if TYPE_CHECKING:
    from mcp_server_llmling.injection.server import ConfigInjectionServer

logger = get_logger(__name__)


class ResourcesPage:
    """Resources management page."""

    def __init__(self, server: ConfigInjectionServer) -> None:
        self.server = server
        self.header = Header(server)

    @ui.page("/resources")
    def render(self) -> None:
        """Render the resources page."""
        self.header.render()

        with ui.column().classes("p-4 w-full gap-4"):
            ui.label("Resources").classes("text-2xl")

            # Simple table showing resources
            resources = self.server.llm_server.runtime.list_resource_names()
            registry = self.server.llm_server.runtime._resource_registry
            rows = [
                {"name": name, "type": registry[name].__class__.__name__}
                for name in resources
            ]

            columns = [
                {"name": "name", "label": "Name", "field": "name"},
                {"name": "type", "label": "Type", "field": "type"},
            ]

            ui.table(columns=columns, rows=rows, row_key="name").classes("w-full")
