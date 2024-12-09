"""Dashboard page showing system overview."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from mcp_server_llmling.log import get_logger
from mcp_server_llmling.ui.components.header import Header


if TYPE_CHECKING:
    from mcp_server_llmling.injection.server import ConfigInjectionServer

logger = get_logger(__name__)


class DashboardPage:
    """Dashboard page showing system overview."""

    def __init__(self, server: ConfigInjectionServer) -> None:
        self.server = server
        self.header = Header(server)

    @ui.page("/")
    def render(self) -> None:
        """Render the dashboard page."""
        self.header.render()

        with ui.column().classes("p-4 w-full"):
            with ui.row().classes("w-full justify-between"):
                ui.label("Dashboard").classes("text-2xl")
                ui.button("Refresh", icon="refresh", on_click=self.refresh_stats)

            # Stats cards
            with ui.row().classes("w-full gap-4 mt-4"):
                with ui.card().classes("flex-1"):
                    ui.label("Resources").classes("text-lg")
                    self.resources_count = ui.label(
                        str(len(self.server.llm_server.runtime.list_resource_names()))
                    ).classes("text-3xl")

                with ui.card().classes("flex-1"):
                    ui.label("Tools").classes("text-lg")
                    self.tools_count = ui.label(
                        str(len(self.server.llm_server.runtime.list_tool_names()))
                    ).classes("text-3xl")

                with ui.card().classes("flex-1"):
                    ui.label("Prompts").classes("text-lg")
                    self.prompts_count = ui.label(
                        str(len(self.server.llm_server.runtime.list_prompt_names()))
                    ).classes("text-3xl")

            # Server info
            with ui.card().classes("w-full mt-4"):
                ui.label("Server Information").classes("text-lg mb-2")
                with ui.row().classes("gap-8"):
                    ui.label(f"Host: {self.server.host}")
                    ui.label(f"Port: {self.server.port}")

    def refresh_stats(self) -> None:
        """Refresh the statistics."""
        self.resources_count.text = str(
            len(self.server.llm_server.runtime.list_resource_names())
        )
        self.tools_count.text = str(len(self.server.llm_server.runtime.list_tool_names()))
        self.prompts_count.text = str(
            len(self.server.llm_server.runtime.list_prompt_names())
        )
        ui.notify("Statistics updated")
