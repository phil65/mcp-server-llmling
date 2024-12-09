"""Header component with navigation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui


if TYPE_CHECKING:
    from mcp_server_llmling.injection.server import ConfigInjectionServer


class Header:
    """Application header with navigation."""

    def __init__(self, server: ConfigInjectionServer) -> None:
        """Initialize header.

        Args:
            server: The injection server instance
        """
        self.server = server

    def render(self) -> None:
        """Render the header component."""
        with ui.header().classes(
            "flex justify-between items-center p-4 bg-blue-600 text-white"
        ):
            ui.label("LLMling Config").classes("text-2xl")

            with ui.row().classes("gap-4"):
                ui.link("Dashboard", "/ui").classes("text-white")
                ui.link("Resources", "/ui/resources").classes("text-white")
                ui.link("Tools", "/ui/tools").classes("text-white")

            # Right side status
            with ui.row().classes("gap-2 items-center"):
                ui.icon(
                    "circle", color="green" if self.server.llm_server.runtime else "red"
                )
                ui.label("Server Status")
