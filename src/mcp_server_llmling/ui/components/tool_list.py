"""Tool list component."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from mcp_server_llmling.log import get_logger


if TYPE_CHECKING:
    from nicegui.slot import Slot

    from mcp_server_llmling.injection.server import ConfigInjectionServer

logger = get_logger(__name__)


class ToolList:
    """A list of tools with management capabilities."""

    def __init__(self, server: ConfigInjectionServer) -> None:
        """Initialize tool list."""
        self.server = server

    @ui.refreshable
    def render(self) -> None:
        """Render the tool list."""
        tools = self.server.llm_server.runtime.list_tool_names()

        with ui.card().classes("w-full"):
            ui.label("Tools").classes("text-xl mb-4")

            columns = [
                {"name": "name", "label": "Name", "field": "name"},
                {"name": "import_path", "label": "Import Path", "field": "import_path"},
                {"name": "actions", "label": "Actions", "field": "name"},
            ]

            rows = [
                {
                    "name": name,
                    "import_path": self.server.llm_server.runtime._tool_registry[
                        name
                    ].import_path,
                }
                for name in tools
            ]

            with ui.table(columns=columns, rows=rows, row_key="name").classes(
                "w-full"
            ) as table_elem:
                with (
                    table_elem.add_slot("top-right"),
                    ui.input(placeholder="Search")
                    .props("type=search")
                    .bind_value(table_elem, "filter"),
                ):
                    ui.icon("search")

                with table_elem.add_slot("body-cell-actions") as cell, ui.row():
                    self._create_action_buttons(cell)

    def _create_action_buttons(self, cell: Slot) -> None:
        """Create action buttons for a table row."""
        name: str = cell.record["name"]  # type: ignore[attr-defined]

        with (
            ui.button(icon="play_arrow", color="green")
            .props("flat dense")
            .on_click(lambda: self._test_tool(name))
        ):
            ui.tooltip("Test tool")

        with (
            ui.button(icon="delete", color="red")
            .props("flat dense")
            .on_click(lambda: self._delete_tool(name))
        ):
            ui.tooltip("Delete tool")

    async def _delete_tool(self, name: str) -> None:
        """Delete a tool."""
        try:
            del self.server.llm_server.runtime._tool_registry[name]
            ui.notify(f"Tool {name} deleted")
            self.render.refresh()
        except Exception as e:
            logger.exception("Failed to delete tool")
            ui.notify(f"Failed to delete tool: {e}", type="negative")

    async def _test_tool(self, name: str) -> None:
        """Test a tool with default arguments."""
        try:
            result = await self.server.llm_server.runtime.execute_tool(name)
            ui.notify(f"Tool test successful: {result}")
        except Exception as e:
            logger.exception("Tool test failed")
            ui.notify(f"Tool test failed: {e}", type="negative")
