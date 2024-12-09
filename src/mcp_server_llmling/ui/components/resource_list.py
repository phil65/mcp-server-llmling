"""Resource list component."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nicegui import ui

from mcp_server_llmling.log import get_logger


if TYPE_CHECKING:
    from nicegui.slot import Slot

    from mcp_server_llmling.injection.server import ConfigInjectionServer

logger = get_logger(__name__)


class ResourceList:
    """A list of resources with management capabilities."""

    def __init__(self, server: ConfigInjectionServer) -> None:
        """Initialize resource list."""
        self.server = server
        self._setup_dialogs()

    def _setup_dialogs(self) -> None:
        """Create reusable dialogs."""
        with ui.dialog() as self.preview_dialog, ui.card():
            self.preview_title = ui.label().classes("text-xl mb-4")
            self.preview_metadata = ui.row().classes("gap-4")
            self.preview_content = ui.column().classes("w-full")
            with ui.row().classes("w-full justify-end"):
                ui.button("Close", on_click=self.preview_dialog.close)

    @ui.refreshable
    def render(self) -> None:
        """Render the resource list."""
        try:
            resources = self.server.llm_server.runtime.list_resource_names()

            with ui.card().classes("w-full"):
                ui.label("Resources").classes("text-xl mb-4")

                columns = [
                    {"name": "name", "label": "Name", "field": "name"},
                    {"name": "type", "label": "Type", "field": "type"},
                    {"name": "uri", "label": "URI", "field": "uri"},
                    {"name": "actions", "label": "Actions", "field": "name"},
                ]

                rows = []
                for name in resources:
                    try:
                        registry = self.server.llm_server.runtime._resource_registry
                        rows.append({
                            "name": name,
                            "type": registry[name].__class__.__name__,
                            "uri": self.server.llm_server.runtime.get_resource_uri(name),
                        })
                    except Exception:
                        logger.exception("Failed to get resource info for %s", name)
                        # Add row with error indication
                        rows.append({
                            "name": name,
                            "type": "Error",
                            "uri": "Unable to load",
                        })

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

        except Exception as e:
            logger.exception("Failed to render resource list")
            with ui.card().classes("w-full bg-red-50"):
                ui.label(f"Error loading resources: {e!s}").classes("text-red-600")

    def _create_action_buttons(self, cell: Slot) -> None:
        """Create action buttons for a table row."""
        name: str = cell.record["name"]  # type: ignore[attr-defined]

        with (
            ui.button(icon="visibility", color="blue")
            .props("flat dense")
            .on_click(lambda: self._preview_resource(name))
        ):
            ui.tooltip("Preview resource")

        with (
            ui.button(icon="delete", color="red")
            .props("flat dense")
            .on_click(lambda: self._delete_resource(name))
        ):
            ui.tooltip("Delete resource")

    async def _delete_resource(self, name: str) -> None:
        """Delete a resource."""
        try:
            del self.server.llm_server.runtime._resource_registry[name]
            ui.notify(f"Resource {name} deleted")
            self.render.refresh()
        except Exception as e:
            logger.exception("Failed to delete resource")
            ui.notify(f"Failed to delete resource: {e}", type="negative")

    async def _preview_resource(self, name: str) -> None:
        """Preview resource content."""
        try:
            resource = await self.server.llm_server.runtime.load_resource(name)

            # Update dialog content
            self.preview_title.text = f"Resource: {name}"

            self.preview_metadata.clear()
            with self.preview_metadata:
                ui.label(f"Type: {resource.metadata.mime_type}")
                if resource.metadata.mime_type:
                    ui.label(f"MIME Type: {resource.metadata.mime_type}")

            self.preview_content.clear()
            with self.preview_content:
                if resource.metadata.mime_type and resource.metadata.mime_type.startswith(
                    "image/"
                ):
                    ui.image(resource.content)
                else:
                    ui.textarea(value=str(resource.content)).props("readonly").classes(
                        "w-full"
                    )

            self.preview_dialog.open()

        except Exception as e:
            logger.exception("Failed to preview resource")
            ui.notify(f"Failed to preview resource: {e}", type="negative")
