from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any, Literal

from fastapi import FastAPI

from mcp_server_llmling.injection import routes
from mcp_server_llmling.injection.utils import find_free_port
from mcp_server_llmling.log import get_logger
from mcp_server_llmling.transports.stdio import StdioServer


if TYPE_CHECKING:
    import uvicorn

    from mcp_server_llmling.server import LLMLingServer

# from mcp_server_llmling.ui import create_ui_app


logger = get_logger(__name__)


ComponentType = Literal["resource", "tool", "prompt"]


DESCRIPTION = """
API for hot-injecting configuration into running LLMling server.

## Features
* Inject new resources
* Update existing tools
* Real-time configuration updates
* WebSocket support for live updates

## WebSocket Interface
Connect to `/ws` for real-time updates. The WebSocket interface supports:

### Message Types
* update: Update components in real-time
* query: Query current component status
* error: Error reporting from client

### Message Format
```json
{
    "type": "update|query|error",
    "data": {
        "resources": {...},
        "tools": {...}
    },
    "request_id": "optional-correlation-id"
}
```

### Response Format
```json
{
    "type": "success|error|update",
    "data": {...},
    "request_id": "correlation-id",
    "message": "optional status message"
}
```
"""

TAGS = [
    {
        "name": "components",
        "description": "Server component operations (resources/tools/prompts)",
    },
    {"name": "config", "description": "Configuration management endpoints"},
]


def create_app() -> FastAPI:
    """Create FastAPI application for config injection."""
    return FastAPI(
        title="LLMling Config Injection API",
        description=DESCRIPTION,
        version="1.0.0",
        openapi_tags=TAGS,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )


class ConfigInjectionServer:
    """FastAPI server for hot config injection."""

    def __init__(
        self,
        llm_server: LLMLingServer,
        host: str = "localhost",
        port: int = 8765,
    ) -> None:
        """Initialize server."""
        self.llm_server = llm_server
        self.host = host
        self._port = port if port != 0 else find_free_port()
        self.app = create_app()
        routes.setup_routes(self)
        self._server: uvicorn.Server | None = None
        self._server_task: asyncio.Task[Any] | None = None

    @property
    def port(self) -> int:
        """Get server port."""
        return self._port

    async def start(self) -> None:
        """Start FastAPI server."""
        if not isinstance(self.llm_server.transport, StdioServer):
            msg = "Config injection requires stdio transport"
            raise RuntimeError(msg)  # noqa: TRY004

        import uvicorn

        config = uvicorn.Config(
            app=self.app,
            host=self.host,
            port=self._port,
            log_level="info",
            ws_ping_interval=None,  # Disable ping/pong for tests
            ws_ping_timeout=None,  # Disable ping timeout
            timeout_keep_alive=0,  # Don't keep connections alive
        )
        server = uvicorn.Server(config)
        self._server = server

        # Create and start server task
        self._server_task = asyncio.create_task(server.serve())
        # Give the server a moment to start
        await asyncio.sleep(0.1)

    async def stop(self) -> None:
        """Stop FastAPI server."""
        if self._server:
            self._server.should_exit = True

        if self._server_task:
            with contextlib.suppress(asyncio.CancelledError):
                await self._server_task
            self._server_task = None
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
            url = "http://localhost:8765/tools/my_tool"
            response = await client.post(url, json={"import_path": "myapp.tools.analyze"})
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


if __name__ == "__main__":
    import asyncio

    from llmling import Config, RuntimeConfig

    from mcp_server_llmling.server import LLMLingServer

    async def main() -> None:
        # Create minimal config
        config = Config.model_validate({
            "global_settings": {},
            "resources": {"initial": {"type": "text", "content": "Initial resource"}},
        })

        async with RuntimeConfig.from_config(config) as runtime:
            server = LLMLingServer(runtime, enable_injection=True)
            print("Starting server with injection endpoint at http://localhost:8765")
            await server.start(raise_exceptions=True)

    asyncio.run(main())
