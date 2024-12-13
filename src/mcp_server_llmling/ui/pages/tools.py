"""Tools management page."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from mcp_server_llmling.log import get_logger
from mcp_server_llmling.ui.components.header import Header
from mcp_server_llmling.ui.components.tool_list import ToolList


if TYPE_CHECKING:
    from mcp_server_llmling.injection.server import ConfigInjectionServer

logger = get_logger(__name__)


class ToolsPage:
    """Tools management page."""

    def __init__(self, server: ConfigInjectionServer) -> None:
        self.server = server
        self.header = Header(server)
        self.tool_list = ToolList(server)

    @ui.page("/tools")
    def render(self) -> None:
        """Render the tools page."""
        self.header.render()

        with ui.column().classes("p-4 w-full gap-4"):
            with ui.row().classes("w-full justify-between items-center"):
                ui.label("Tools").classes("text-2xl")

            # Call the instance method correctly
            self.tool_list.render()  # type: ignore

            with ui.card().classes("w-full mt-4"):
                ui.label("Import Paths").classes("text-lg mb-2")
                current_paths: list[str] = [
                    tool.import_path
                    for tool in self.server.llm_server.runtime._tool_registry.values()
                ]
                if current_paths:
                    for path in sorted(set(current_paths)):
                        ui.label(f"• {path}").classes("text-sm text-gray-600")
                else:
                    ui.label("No tools configured").classes("text-sm text-gray-600")
