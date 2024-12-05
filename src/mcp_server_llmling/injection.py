from __future__ import annotations

from collections.abc import Sequence  # noqa: TC003
from typing import TYPE_CHECKING, Any, Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from llmling.config.models import (
    CallableResource,
    CLIResource,
    ImageResource,
    PathResource,
    Resource,
    SourceResource,
    TextResource,
    ToolConfig,
)
from llmling.core.log import get_logger
import logfire
from py2openai import OpenAIFunctionTool  # noqa: TC002
from pydantic import BaseModel
from pydantic.fields import Field

from mcp_server_llmling.transports.stdio import StdioServer


if TYPE_CHECKING:
    from mcp_server_llmling.server import LLMLingServer


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


class ConfigInjectionServer:
    """FastAPI server for hot config injection."""

    def __init__(
        self,
        llm_server: LLMLingServer,
        host: str = "localhost",
        port: int = 8765,
    ) -> None:
        """Initialize server.

        Args:
            llm_server: The LLMling server instance
            host: Host to bind to
            port: Port to listen on
        """
        self.llm_server = llm_server
        self.host = host
        self.port = port
        self.app = FastAPI(
            title="LLMling Config Injection",
            description="Hot-inject configuration into running LLMling server",
        )
        self._setup_routes()
        self._server: Any = None  # uvicorn server instance

    def _setup_routes(self) -> None:
        """Set up API routes."""

        @self.app.post("/inject-config")
        @logfire.instrument("Inject raw YAML config")
        async def inject_config(config: dict[str, Any]) -> ComponentResponse:
            """Inject raw YAML configuration."""
            logger.debug("Received config: %s", config)
            try:
                # Update resources
                if resources := config.get("resources"):
                    logger.debug("Processing resources: %s", resources)
                    for name, resource in resources.items():
                        # Validate based on resource type
                        resource_type = resource.get("type")
                        logger.debug(
                            "Processing resource %s of type %s", name, resource_type
                        )
                        match resource_type:
                            case "path":
                                validated = PathResource.model_validate(resource)
                            case "text":
                                validated = TextResource.model_validate(resource)
                            case "cli":
                                validated = CLIResource.model_validate(resource)
                            case "source":
                                validated = SourceResource.model_validate(resource)
                            case "callable":
                                validated = CallableResource.model_validate(resource)
                            case "image":
                                validated = ImageResource.model_validate(resource)
                            case _:
                                msg = f"Unknown resource type: {resource_type}"
                                raise ValueError(msg)  # noqa: TRY301

                        self.llm_server.runtime.register_resource(
                            name, validated, replace=True
                        )
                        logger.debug("Resource %s registered", name)

                # Update tools
                if tools := config.get("tools"):
                    logger.debug("Processing tools: %s", tools)
                    for name, tool in tools.items():
                        logger.debug("Processing tool: %s", name)
                        validated = ToolConfig.model_validate(tool)
                        self.llm_server.runtime._tool_registry.register(
                            name, validated, replace=True
                        )
                        logger.debug("Tool %s registered", name)

                result = ComponentResponse(
                    status="success",
                    message="Config injected successfully",
                    component_type="tool",
                    name="yaml_injection",
                )
                logger.debug("Returning response: %s", result.model_dump())
            except Exception as e:
                logger.exception("Failed to inject config")
                raise HTTPException(status_code=400, detail=str(e)) from e
            else:
                return result

        @self.app.get("/components")
        async def list_components() -> dict[str, Sequence[str]]:
            """List all registered components."""
            return {
                "resources": self.llm_server.runtime.list_resources(),
                "tools": self.llm_server.runtime.list_tools(),
                "prompts": self.llm_server.runtime.list_prompts(),
            }

        # Resource endpoints
        @self.app.post("/resources/{name}", response_model=ComponentResponse)
        @logfire.instrument("Inject resource")
        async def add_resource(name: str, resource: Resource) -> ComponentResponse:
            """Add or update a resource."""
            try:
                self.llm_server.runtime.register_resource(name, resource, replace=True)
                return ComponentResponse(
                    status="success",
                    message=f"Resource {name} registered",
                    component_type="resource",
                    name=name,
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e)) from e

        @self.app.get("/resources")
        async def list_resources() -> dict[str, Resource]:
            """List all resources with their configuration."""
            return {
                name: self.llm_server.runtime._resource_registry[name]
                for name in self.llm_server.runtime.list_resources()
            }

        @self.app.delete("/resources/{name}", response_model=ComponentResponse)
        async def remove_resource(name: str) -> ComponentResponse:
            """Remove a resource."""
            try:
                del self.llm_server.runtime._resource_registry[name]
                return ComponentResponse(
                    status="success",
                    message=f"Resource {name} removed",
                    component_type="resource",
                    name=name,
                )
            except KeyError as e:
                raise HTTPException(
                    status_code=404, detail=f"Resource {name} not found"
                ) from e

        # Tool endpoints
        @self.app.post("/tools/{name}", response_model=ComponentResponse)
        @logfire.instrument("Inject tool")
        async def add_tool(name: str, tool: ToolConfig) -> ComponentResponse:
            """Add or update a tool."""
            try:
                self.llm_server.runtime._tool_registry.register(name, tool, replace=True)
                return ComponentResponse(
                    status="success",
                    message=f"Tool {name} registered",
                    component_type="tool",
                    name=name,
                )
            except Exception as e:
                raise HTTPException(status_code=400, detail=str(e)) from e

        @self.app.get("/tools")
        async def list_tools() -> dict[str, OpenAIFunctionTool]:
            """List all tools with their OpenAPI schemas."""
            try:
                return {
                    name: tool.get_schema()
                    for name, tool in self.llm_server.runtime.tools.items()
                }
            except Exception as e:
                raise HTTPException(
                    status_code=500, detail=f"Failed to get tool schemas: {e}"
                ) from e

        @self.app.delete("/tools/{name}", response_model=ComponentResponse)
        async def remove_tool(name: str) -> ComponentResponse:
            """Remove a tool."""
            try:
                del self.llm_server.runtime._tool_registry[name]
                return ComponentResponse(
                    status="success",
                    message=f"Tool {name} removed",
                    component_type="tool",
                    name=name,
                )
            except KeyError as e:
                raise HTTPException(
                    status_code=404, detail=f"Tool {name} not found"
                ) from e

        # Bulk update endpoint
        @self.app.post("/bulk-update", response_model=BulkUpdateResponse)
        @logfire.instrument("Bulk component update")
        async def bulk_update(request: ConfigUpdateRequest) -> BulkUpdateResponse:
            """Update multiple components at once."""
            responses: list[ComponentResponse] = []
            summary = {"success": 0, "error": 0}

            if request.resources:
                for name, resource in request.resources.items():
                    try:
                        self.llm_server.runtime.register_resource(
                            name, resource, replace=request.replace_existing
                        )
                        responses.append(
                            ComponentResponse(
                                status="success",
                                message=f"Resource {name} registered",
                                component_type="resource",
                                name=name,
                            )
                        )
                        summary["success"] += 1
                    except Exception as e:  # noqa: BLE001
                        responses.append(
                            ComponentResponse(
                                status="error",
                                message=str(e),
                                component_type="resource",
                                name=name,
                            )
                        )
                        summary["error"] += 1

            if request.tools:
                for name, tool in request.tools.items():
                    try:
                        self.llm_server.runtime._tool_registry.register(
                            name, tool, replace=request.replace_existing
                        )
                        responses.append(
                            ComponentResponse(
                                status="success",
                                message=f"Tool {name} registered",
                                component_type="tool",
                                name=name,
                            )
                        )
                        summary["success"] += 1
                    except Exception as e:  # noqa: BLE001
                        responses.append(
                            ComponentResponse(
                                status="error",
                                message=str(e),
                                component_type="tool",
                                name=name,
                            )
                        )
                        summary["error"] += 1

            return BulkUpdateResponse(results=responses, summary=summary)

        # WebSocket endpoint
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket) -> None:
            """Handle WebSocket connections."""
            await websocket.accept()
            try:
                while True:
                    raw_data = await websocket.receive_json()
                    try:
                        message = WebSocketMessage.model_validate(raw_data)
                        match message.type:
                            case "update":
                                if isinstance(message.data, dict):
                                    request = ConfigUpdateRequest.model_validate(
                                        message.data
                                    )
                                    response = await bulk_update(request)
                                    await websocket.send_json(
                                        WebSocketResponse(
                                            type="success",
                                            data=response.results,
                                            request_id=message.request_id,
                                            message="Components updated successfully",
                                        ).model_dump()
                                    )
                            case "query":
                                # Handle component queries
                                components = await list_components()
                                await websocket.send_json(
                                    WebSocketResponse(
                                        type="success",
                                        data=components,
                                        request_id=message.request_id,
                                    ).model_dump()
                                )
                            case "error":
                                logger.error("Client error: %s", message.data)
                    except Exception:
                        error_msg = "Operation failed"
                        logger.exception(error_msg)
                        await websocket.send_json(
                            WebSocketResponse(
                                type="error",
                                data={},
                                message=error_msg,
                                request_id=getattr(message, "request_id", None),
                            ).model_dump()
                        )
            except WebSocketDisconnect:
                logger.debug("WebSocket client disconnected")

    async def start(self) -> None:
        """Start FastAPI server in the same event loop."""
        if not isinstance(self.llm_server.transport, StdioServer):
            msg = "Config injection requires stdio transport"
            raise RuntimeError(msg)  # noqa: TRY004

        import uvicorn

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        self._server = uvicorn.Server(config)
        # Run in same event loop
        await self._server.serve()

    async def stop(self) -> None:
        """Stop FastAPI server."""
        if self._server:
            self._server.should_exit = True
            await self._server.shutdown()
            self._server = None


if __name__ == "__main__":

    async def main() -> None:
        import httpx

        async with httpx.AsyncClient() as client:
            # Add a single resource
            response = await client.post(
                "http://localhost:8765/resources/my_resource",
                json={"type": "text", "content": "Dynamic content"},
            )
            print(response.json())

            # Add a tool
            response = await client.post(
                "http://localhost:8765/tools/my_tool",
                json={"import_path": "myapp.tools.analyze"},
            )
            print(response.json())

            # List all components
            components = await client.get("http://localhost:8765/components")
            print(components.json())

            # Bulk update
            response = await client.post(
                "http://localhost:8765/bulk-update",
                json={
                    "resources": {
                        "resource1": {"type": "text", "content": "Content 1"},
                        "resource2": {"type": "text", "content": "Content 2"},
                    },
                    "tools": {
                        "tool1": {"import_path": "myapp.tools.tool1"},
                        "tool2": {"import_path": "myapp.tools.tool2"},
                    },
                },
            )
            print(response.json())
