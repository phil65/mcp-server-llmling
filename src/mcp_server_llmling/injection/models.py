from __future__ import annotations

from typing import Any, Literal

from llmling.config.models import Resource, ToolConfig  # noqa: TC002
from pydantic import BaseModel
from pydantic.fields import Field

from mcp_server_llmling.log import get_logger


# from mcp_server_llmling.ui import create_ui_app


logger = get_logger(__name__)


ComponentType = Literal["resource", "tool", "prompt"]


class ComponentResponse(BaseModel):
    """Response model for component operations."""

    status: Literal["success", "error"]
    message: str
    component_type: ComponentType
    name: str


class ConfigUpdate(BaseModel):
    """Model for config updates."""

    resources: dict[str, Resource] | None = Field(
        default=None, description="Resource updates"
    )
    tools: dict[str, ToolConfig] | None = Field(default=None, description="Tool updates")


class BulkUpdateResponse(BaseModel):
    """Response model for bulk updates."""

    results: list[ComponentResponse]
    summary: dict[str, int] = Field(default_factory=lambda: {"success": 0, "error": 0})


class ConfigUpdateRequest(BaseModel):
    """Request model for config updates."""

    resources: dict[str, Resource] | None = None
    tools: dict[str, ToolConfig] | None = None
    replace_existing: bool = Field(
        default=True, description="Whether to replace existing components"
    )


class WebSocketMessage(BaseModel):
    """Message format for WebSocket communication."""

    type: Literal["update", "query", "error"]
    data: ConfigUpdateRequest | dict[str, Any]
    request_id: str | None = None


class WebSocketResponse(BaseModel):
    """Response format for WebSocket communication."""

    type: Literal["success", "error", "update"]
    data: ComponentResponse | list[ComponentResponse] | dict[str, Any]
    request_id: str | None = None
    message: str | None = None
