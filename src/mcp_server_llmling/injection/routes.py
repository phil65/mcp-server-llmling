from __future__ import annotations

from collections.abc import Sequence  # noqa: TC003
from typing import TYPE_CHECKING, Any, Literal

from fastapi import HTTPException, WebSocket, WebSocketDisconnect
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
from py2openai import OpenAIFunctionTool  # noqa: TC002

from mcp_server_llmling.injection.models import (
    BulkUpdateResponse,
    ComponentResponse,
    ConfigUpdateRequest,
    ErrorResponse,
    SuccessResponse,
    WebSocketMessage,
    WebSocketResponse,
)
from mcp_server_llmling.log import get_logger


if TYPE_CHECKING:
    from mcp_server_llmling.injection.server import ConfigInjectionServer


logger = get_logger(__name__)


ComponentType = Literal["resource", "tool", "prompt"]


def setup_routes(server: ConfigInjectionServer) -> None:
    """Set up API routes."""

    @server.app.post(
        "/inject-config",
        response_model=ComponentResponse,
        tags=["config"],
        summary="Inject new configuration",
        description="Inject new configuration into the running server.",
        responses={
            200: {
                "description": "Configuration successfully injected",
                "content": {
                    "application/json": {
                        "example": {
                            "status": "success",
                            "message": "Config injected successfully",
                            "component_type": "resource",
                            "name": "example_resource",
                        }
                    }
                },
            },
            400: {"description": "Invalid configuration"},
        },
    )
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
                    logger.debug("Processing resource %s of type %s", name, resource_type)
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

                    server.llm_server.runtime.register_resource(
                        name, validated, replace=True
                    )
                    logger.debug("Resource %s registered", name)

            # Update tools
            if tools := config.get("tools"):
                logger.debug("Processing tools: %s", tools)
                for name, tool in tools.items():
                    logger.debug("Processing tool: %s", name)
                    validated = ToolConfig.model_validate(tool)
                    server.llm_server.runtime._tool_registry.register(
                        name, validated, replace=True
                    )
                    logger.debug("Tool %s registered", name)
            msg = "Config injected successfully"
            name = "yaml_injection"
            result = SuccessResponse(message=msg, component_type="tool", name=name)
            logger.debug("Returning response: %s", result.model_dump())
        except Exception as e:
            logger.exception("Failed to inject config")
            raise HTTPException(status_code=400, detail=str(e)) from e
        else:
            return result

    @server.app.get(
        "/components",
        tags=["components"],
        summary="List all components",
        description="Get a list of all registered components grouped by type.",
        response_description="Dictionary containing arrays of component names",
        responses={
            200: {
                "description": "List of all components",
                "content": {
                    "application/json": {
                        "example": {
                            "resources": ["resource1", "resource2"],
                            "tools": ["tool1", "tool2"],
                            "prompts": ["prompt1", "prompt2"],
                        }
                    }
                },
            }
        },
    )
    async def list_components() -> dict[str, Sequence[str]]:
        """List all registered components."""
        return {
            "resources": server.llm_server.runtime.list_resource_names(),
            "tools": server.llm_server.runtime.list_tool_names(),
            "prompts": server.llm_server.runtime.list_prompt_names(),
        }

    # Resource endpoints
    @server.app.post(
        "/resources/{name}",
        response_model=ComponentResponse,
        tags=["components"],
        summary="Add or update resource",
        description="""
        Register a new resource or update an existing one.
        Supports various resource types including path, text, CLI, source,
        callable, and image.
        """,
        responses={
            200: {"description": "Resource successfully registered"},
            400: {"description": "Invalid resource configuration"},
        },
    )
    async def add_resource(name: str, resource: Resource) -> ComponentResponse:
        """Add or update a resource."""
        try:
            server.llm_server.runtime.register_resource(name, resource, replace=True)
            msg = f"Resource {name} registered"
            return SuccessResponse(message=msg, component_type="resource", name=name)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @server.app.get(
        "/resources",
        tags=["components"],
        summary="List all resources",
        description="Get a list of all registered resources with their full config.",
        responses={
            200: {
                "description": "Dictionary of resources",
                "content": {
                    "application/json": {
                        "example": {
                            "resource1": {
                                "type": "text",
                                "content": "Example content",
                            },
                            "resource2": {"type": "path", "path": "/example/path"},
                        }
                    }
                },
            }
        },
    )
    async def list_resources() -> dict[str, Resource]:
        """List all resources with their configuration."""
        return {
            name: server.llm_server.runtime._resource_registry[name]
            for name in server.llm_server.runtime.list_resource_names()
        }

    @server.app.delete(
        "/resources/{name}",
        response_model=ComponentResponse,
        tags=["components"],
        summary="Remove resource",
        description="Remove a registered resource by name.",
        responses={
            200: {"description": "Resource successfully removed"},
            404: {"description": "Resource not found"},
        },
    )
    async def remove_resource(name: str) -> ComponentResponse:
        """Remove a resource."""
        try:
            del server.llm_server.runtime._resource_registry[name]
            msg = f"Resource {name} removed"
            return SuccessResponse(message=msg, component_type="resource", name=name)
        except KeyError as e:
            raise HTTPException(
                status_code=404, detail=f"Resource {name} not found"
            ) from e

    # Tool endpoints
    @server.app.post(
        "/tools/{name}",
        response_model=ComponentResponse,
        tags=["components"],
        summary="Add or update tool",
        description="Register a new tool or update an existing one.",
        responses={
            200: {"description": "Tool successfully registered"},
            400: {"description": "Invalid tool configuration"},
        },
    )
    async def add_tool(name: str, tool: ToolConfig) -> ComponentResponse:
        """Add or update a tool."""
        try:
            server.llm_server.runtime._tool_registry.register(name, tool, replace=True)
            msg = f"Tool {name} registered"
            return SuccessResponse(message=msg, component_type="tool", name=name)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

    @server.app.get(
        "/tools",
        tags=["components"],
        summary="List all tools",
        description="Get a list of all registered tools with their OpenAPI schemas.",
        responses={
            200: {
                "description": "Dictionary of tools with their schemas",
                "content": {
                    "application/json": {
                        "example": {
                            "tool1": {
                                "name": "tool1",
                                "description": "Example tool",
                                "parameters": {
                                    "type": "object",
                                    "properties": {},
                                },
                            }
                        }
                    }
                },
            },
            500: {"description": "Failed to get tool schemas"},
        },
    )
    async def list_tools() -> dict[str, OpenAIFunctionTool]:
        """List all tools with their OpenAPI schemas."""
        try:
            return {
                name: tool.get_schema()
                for name, tool in server.llm_server.runtime.tools.items()
            }
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to get tool schemas: {e}"
            ) from e

    @server.app.delete(
        "/tools/{name}",
        response_model=ComponentResponse,
        tags=["components"],
        summary="Remove tool",
        description="Remove a registered tool by name.",
        responses={
            200: {"description": "Tool successfully removed"},
            404: {"description": "Tool not found"},
        },
    )
    async def remove_tool(name: str) -> ComponentResponse:
        """Remove a tool."""
        try:
            del server.llm_server.runtime._tool_registry[name]
            msg = f"Tool {name} removed"
            return SuccessResponse(message=msg, component_type="tool", name=name)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=f"Tool {name} not found") from e

    # Bulk update endpoint
    @server.app.post(
        "/bulk-update",
        response_model=BulkUpdateResponse,
        tags=["config"],
        summary="Bulk update components",
        description="""
        Update multiple components in a single request.

        This endpoint allows you to register multiple resources and tools at once.
        Failed operations will be reported in the response but won't affect others.
        """,
        responses={
            200: {
                "description": "Bulk update results",
                "content": {
                    "application/json": {
                        "example": {
                            "results": [
                                {
                                    "status": "success",
                                    "message": "Resource registered",
                                    "component_type": "resource",
                                    "name": "example",
                                }
                            ],
                            "summary": {"success": 1, "error": 0},
                        }
                    }
                },
            },
        },
    )
    async def bulk_update(request: ConfigUpdateRequest) -> BulkUpdateResponse:
        """Update multiple components at once."""
        responses: list[ComponentResponse] = []
        summary = {"success": 0, "error": 0}
        res: ComponentResponse
        if request.resources:
            for name, resource in request.resources.items():
                try:
                    server.llm_server.runtime.register_resource(
                        name, resource, replace=request.replace_existing
                    )
                    msg = f"Resource {name} registered"
                    res = SuccessResponse(
                        message=msg, component_type="resource", name=name
                    )
                    responses.append(res)
                    summary["success"] += 1
                except Exception as e:  # noqa: BLE001
                    er = ErrorResponse(
                        message=str(e), component_type="resource", name=name
                    )
                    responses.append(er)
                    summary["error"] += 1

        if request.tools:
            for name, tool in request.tools.items():
                try:
                    server.llm_server.runtime._tool_registry.register(
                        name, tool, replace=request.replace_existing
                    )
                    msg = f"Tool {name} registered"
                    res = SuccessResponse(message=msg, component_type="tool", name=name)
                    responses.append(res)
                    summary["success"] += 1
                except Exception as e:  # noqa: BLE001
                    er = ErrorResponse(message=str(e), component_type="tool", name=name)
                    responses.append(er)
                    summary["error"] += 1

        return BulkUpdateResponse(results=responses, summary=summary)

    # WebSocket endpoint
    @server.app.websocket(
        "/ws",
        name="component_updates",
        dependencies=None,
    )
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
                                req = ConfigUpdateRequest.model_validate(message.data)
                                response = await bulk_update(req)
                                data = WebSocketResponse(
                                    type="success",
                                    data=response.results,
                                    request_id=message.request_id,
                                    message="Components updated successfully",
                                ).model_dump()
                                await websocket.send_json(data)
                        case "query":
                            # Handle component queries
                            components = await list_components()
                            data = WebSocketResponse(
                                type="success",
                                data=components,
                                request_id=message.request_id,
                            ).model_dump()
                            await websocket.send_json(data)
                        case "error":
                            logger.error("Client error: %s", message.data)
                except Exception:
                    error_msg = "Operation failed"
                    logger.exception(error_msg)
                    response = WebSocketResponse(
                        type="error",
                        data={},
                        message=error_msg,
                        request_id=getattr(message, "request_id", None),
                    ).model_dump()
                    await websocket.send_json(response)
        except WebSocketDisconnect:
            logger.debug("WebSocket client disconnected")