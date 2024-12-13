"""NiceGUI app for configuration injection."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from mcp_server_llmling.log import get_logger
from mcp_server_llmling.ui.components.header import Header
from mcp_server_llmling.ui.components.resource_list import ResourceList
from mcp_server_llmling.ui.components.tool_list import ToolList


if TYPE_CHECKING:
    from mcp_server_llmling.injection.server import ConfigInjectionServer

logger = get_logger(__name__)


def create_ui_app(server: ConfigInjectionServer) -> None:
    """Create the NiceGUI app for configuration injection."""
    from nicegui import app as nicegui_app

    nicegui_app.title = "LLMling Configuration Manager"

    @ui.page("/")  # Root of the NiceGUI app (/ui/)
    def dashboard() -> None:
        """Render dashboard page."""
        header = Header(server)
        header.render()

        with ui.card().classes("w-full"):
            ui.label("LLMling Configuration Manager").classes("text-2xl")
            with ui.row():
                ui.label(
                    f"Resources: {len(server.llm_server.runtime.list_resource_names())}"
                )
                ui.label(f"Tools: {len(server.llm_server.runtime.list_tool_names())}")
                ui.label(f"Prompts: {len(server.llm_server.runtime.list_prompt_names())}")

    @ui.page("/resources")  # Will be /ui/resources
    def resources() -> None:
        """Render resources page."""
        header = Header(server)
        header.render()

        resource_list = ResourceList(server)
        resource_list.render()  # type: ignore

    @ui.page("/tools")  # Will be /ui/tools
    def tools() -> None:
        """Render tools page."""
        header = Header(server)
        header.render()

        tool_list = ToolList(server)
        tool_list.render()  # type: ignore
