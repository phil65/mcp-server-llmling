"""Models for component configuration and API communication."""

from __future__ import annotations

from collections.abc import Sequence  # noqa: F401
from typing import Any, Literal

from llmling.config.models import BaseResource, ToolConfig  # noqa: TC002
from pydantic import BaseModel, ConfigDict, Field

from mcp_server_llmling.log import get_logger


logger = get_logger(__name__)

ComponentType = Literal["resource", "tool", "prompt"]
StatusType = Literal["success", "error"]


class BaseSchema(BaseModel):
    """Base schema with shared configuration."""

    model_config = ConfigDict(use_enum_values=True, use_attribute_docstrings=True)


class BaseMessage(BaseSchema):
    """Base class for all message types."""

    status: StatusType
    """Status of the operation (success/error)."""

    message: str
    """Descriptive message about the operation result."""


class ComponentResponse(BaseMessage):
    """Response model for component operations."""

    component_type: ComponentType
    """Type of the component (resource/tool/prompt)."""

    name: str
    """Name of the component."""


class SuccessResponse(ComponentResponse):
    """Response model for successful component operations."""

    status: Literal["success"] = Field(default="success", init=False)
    """Operation status (always 'success')."""


class ErrorResponse(ComponentResponse):
    """Response model for failed component operations."""

    status: Literal["error"] = Field(default="error", init=False)
    """Operation status (always 'error')."""


class ConfigUpdate(BaseSchema):
    """Model for config updates."""

    resources: dict[str, BaseResource] | None = None
    """Dictionary of resource updates."""

    tools: dict[str, ToolConfig] | None = None
    """Dictionary of tool updates."""


class BulkUpdateResponse(BaseSchema):
    """Response model for bulk updates."""

    results: list[ComponentResponse]
    """List of individual component update results."""

    summary: dict[str, int] = Field(default_factory=lambda: {"success": 0, "error": 0})
    """Summary of update results by status."""


class ConfigUpdateRequest(BaseSchema):
    """Request model for config updates."""

    resources: dict[str, BaseResource] | None = None
    """Dictionary of resources to update."""

    tools: dict[str, ToolConfig] | None = None
    """Dictionary of tools to update."""

    replace_existing: bool = True
    """Whether to replace existing components."""


class WebSocketMessage(BaseSchema):
    """Message format for WebSocket communication."""

    type: Literal["update", "query", "error"]
    """Type of the WebSocket message."""

    data: ConfigUpdateRequest | dict[str, Any]
    """Message payload data."""

    request_id: str | None = None
    """Optional request identifier for correlation."""


class WebSocketResponse(BaseSchema):
    """Response format for WebSocket communication."""

    type: Literal["success", "error", "update"]
    """Type of the WebSocket response."""

    data: ComponentResponse | list[ComponentResponse] | dict[str, Any]
    """Response payload data."""

    request_id: str | None = None
    """Correlated request identifier."""

    message: str | None = None
    """Optional response message."""


class PackageInstallRequest(BaseSchema):
    """Request model for package installation."""

    package: str
    """Package specification with optional version constraints."""


class PackageInstallResponse(BaseSchema):
    """Response model for package installation."""

    status: StatusType
    """Operation status."""

    message: str
    """Installation result or error message."""

    package: str
    """Package that was attempted to be installed."""


class CodeToolRequest(BaseSchema):
    """Request model for registering a tool from code."""

    name: str
    """Name for the new tool."""

    code: str
    """Python code defining the tool function."""

    description: str | None = None
    """Optional tool description."""


class ImportToolRequest(BaseSchema):
    """Request model for registering a tool from import path."""

    import_path: str
    """Import path to the function (e.g. 'mypackage.module.function')."""

    description: str | None = None
    """Optional tool description."""


class ComponentListResponse(ComponentResponse):
    """Response model for component list operations."""

    components: dict[str, list[str]] = Field(default_factory=dict)
    """Dictionary of components grouped by type."""
