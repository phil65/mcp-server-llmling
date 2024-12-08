"""MCP protocol server implementation."""

from __future__ import annotations

import asyncio
from collections import defaultdict
import contextlib
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any, Literal, Self

from llmling.config.manager import ConfigManager
from llmling.config.runtime import RuntimeConfig
from mcp.server import NotificationOptions, Server
from pydantic import AnyUrl

from mcp_server_llmling import constants
from mcp_server_llmling.handlers import register_handlers
from mcp_server_llmling.log import get_logger
from mcp_server_llmling.observers import PromptObserver, ResourceObserver, ToolObserver
from mcp_server_llmling.transports.sse import SSEServer
from mcp_server_llmling.transports.stdio import StdioServer


if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Coroutine
    import os

    import mcp
    from mcp import Implementation

    from mcp_server_llmling.transports.base import TransportBase

logger = get_logger(__name__)

TransportType = Literal["stdio", "sse"]


class LLMLingServer:
    """MCP protocol server implementation."""

    def __init__(
        self,
        runtime: RuntimeConfig,
        *,
        transport: TransportType = "stdio",
        name: str = constants.SERVER_NAME,
        transport_options: dict[str, Any] | None = None,
        enable_injection: bool = False,
        injection_port: int = 8765,
    ) -> None:
        """Initialize server with runtime configuration.

        Args:
            runtime: Fully initialized runtime configuration
            transport: Transport type to use ("stdio" or "sse")
            name: Server name for MCP protocol
            transport_options: Additional options for transport
            enable_injection: Whether to enable config injection
            injection_port: Port for injection server
        """
        self.name = name
        self.runtime = runtime
        self._subscriptions: defaultdict[str, set[mcp.ServerSession]] = defaultdict(set)
        self._tasks: set[asyncio.Task[Any]] = set()

        # Create MCP server
        self.server = Server(name)
        self.server.notification_options = NotificationOptions(
            prompts_changed=True,
            resources_changed=True,
            tools_changed=True,
        )

        # Create transport
        self.transport = self._create_transport(transport, transport_options or {})
        if enable_injection and isinstance(self.transport, StdioServer):
            from mcp_server_llmling.injection import ConfigInjectionServer

            self.injection_server: ConfigInjectionServer | None = ConfigInjectionServer(
                self,
                port=injection_port,
            )
        else:
            self.injection_server = None
        self._setup_handlers()
        self._setup_observers()

    def _create_transport(
        self, transport_type: TransportType, options: dict[str, Any]
    ) -> TransportBase:
        """Create transport instance."""
        match transport_type:
            case "stdio":
                return StdioServer(self.server)
            case "sse":
                return SSEServer(self.server, **options)
            case _:
                msg = f"Unknown transport type: {transport_type}"
                raise ValueError(msg)

    @classmethod
    @asynccontextmanager
    async def from_config_file(
        cls,
        config_path: str | os.PathLike[str],
        *,
        transport: TransportType = "stdio",
        name: str = constants.SERVER_NAME,
        transport_options: dict[str, Any] | None = None,
    ) -> AsyncIterator[LLMLingServer]:
        """Create and run server from config file with proper context management."""
        manager = ConfigManager.load(config_path)
        async with RuntimeConfig.from_config(manager.config) as runtime:
            server = cls(
                runtime,
                transport=transport,
                name=name,
                transport_options=transport_options,
            )
            try:
                yield server
            finally:
                await server.shutdown()

    def get_client_info(self) -> Implementation:
        """Get information about the connected client.

        Returns:
            Implementation: Client name and version information
                        {name: str, version: str}

        Raises:
            RuntimeError: If there is no active client connection or
                        client info not available
        """
        try:
            session = self.current_session
            if not session.client_params:
                msg = "No client initialization parameters available"
                raise RuntimeError(msg)  # noqa: TRY301
        except Exception as exc:
            msg = "Failed to get client information"
            raise RuntimeError(msg) from exc
        else:
            return session.client_params.clientInfo

    def _create_task(self, coro: Coroutine[None, None, Any]) -> asyncio.Task[Any]:
        """Create and track an asyncio task."""
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    def _setup_handlers(self) -> None:
        """Register MCP protocol handlers."""
        register_handlers(self)

    def _setup_observers(self) -> None:
        """Set up registry observers for MCP notifications."""
        self.resource_observer = ResourceObserver(self)
        self.prompt_observer = PromptObserver(self)
        self.tool_observer = ToolObserver(self)

        self.runtime.add_observer(self.resource_observer.events, "resource")
        self.runtime.add_observer(self.prompt_observer.events, "prompt")
        self.runtime.add_observer(self.tool_observer.events, "tool")

    async def start(self, *, raise_exceptions: bool = False) -> None:
        """Start the server."""
        try:
            # Start injection server in a separate task if enabled
            injection_task = None
            if self.injection_server:
                try:
                    # Create task but don't await it directly
                    injection_task = asyncio.create_task(self.injection_server.start())
                    logger.info(
                        "Config injection server listening on port %d",
                        self.injection_server.port,
                    )
                except Exception:
                    logger.exception("Failed to start injection server")
                    if raise_exceptions:
                        raise

            # Run main server
            await self.transport.serve(raise_exceptions=raise_exceptions)

        finally:
            # Clean shutdown
            if injection_task:
                injection_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await injection_task
            await self.shutdown()

    async def shutdown(self) -> None:
        """Shutdown the server."""
        try:
            if self.injection_server:
                await self.injection_server.stop()

            await self.transport.shutdown()

            # Cancel all pending tasks
            if self._tasks:
                for task in self._tasks:
                    task.cancel()
                await asyncio.gather(*self._tasks, return_exceptions=True)
                self._tasks.clear()

            # Remove observers
            self.runtime.remove_observer(self.resource_observer.events, "resource")
            self.runtime.remove_observer(self.prompt_observer.events, "prompt")
            self.runtime.remove_observer(self.tool_observer.events, "tool")

            # Shutdown runtime
            await self.runtime.shutdown()
        finally:
            self._tasks.clear()

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return self

    async def __aexit__(self, *exc: object) -> None:
        """Async context manager exit."""
        await self.shutdown()

    @property
    def current_session(self) -> mcp.ServerSession:
        """Get client info from request context."""
        try:
            return self.server.request_context.session
        except LookupError as exc:
            msg = "No active request context"
            raise RuntimeError(msg) from exc

    @property
    def client_info(self) -> mcp.Implementation | None:
        """Get current session from request context."""
        session = self.current_session
        if not session.client_params:
            return None
        return session.client_params.clientInfo

    def notify_progress(
        self,
        token: str,
        progress: float,
        total: float | None = None,
        description: str | None = None,
    ) -> None:
        """Send progress notification to client."""
        try:
            # Get current session
            session = self.current_session

            # Create and track the progress notification task
            task = session.send_progress_notification(
                progress_token=token,
                progress=progress,
                total=total,
            )
            self._create_task(task)

            # Optionally send description as log message
            if description:
                coro = session.send_log_message(level="info", data=description)
                self._create_task(coro)

        except Exception:
            logger.exception("Failed to send progress notification")

    async def notify_resource_list_changed(self) -> None:
        """Notify clients about resource list changes."""
        try:
            await self.current_session.send_resource_list_changed()
        except RuntimeError:
            logger.debug("No active session for notification")
        except Exception:
            logger.exception("Failed to send resource list change notification")

    async def notify_resource_change(self, uri: str) -> None:
        """Notify subscribers about resource changes."""
        if uri in self._subscriptions:
            try:
                await self.current_session.send_resource_updated(AnyUrl(uri))
            except Exception:
                msg = "Failed to notify subscribers about resource change: %s"
                logger.exception(msg, uri)

    async def notify_prompt_list_changed(self) -> None:
        """Notify clients about prompt list changes."""
        try:
            self._create_task(self.current_session.send_prompt_list_changed())
        except RuntimeError:
            logger.debug("No active session for notification")
        except Exception:
            logger.exception("Failed to send prompt list change notification")

    async def notify_tool_list_changed(self) -> None:
        """Notify clients about tool list changes."""
        try:
            self._create_task(self.current_session.send_tool_list_changed())
        except RuntimeError:
            logger.debug("No active session for notification")
        except Exception:
            logger.exception("Failed to send tool list change notification")


if __name__ == "__main__":
    import sys

    from llmling import config_resources

    config_path = sys.argv[1] if len(sys.argv) > 1 else config_resources.TEST_CONFIG
