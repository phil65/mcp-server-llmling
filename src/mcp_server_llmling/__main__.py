"""MCP server CLI interface."""

from __future__ import annotations

import asyncio
from enum import Enum
import logging
import os
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any

from llmling import RuntimeConfig, config_resources
import typer as t

from mcp_server_llmling import __version__, constants
from mcp_server_llmling.log import get_logger
from mcp_server_llmling.server import LLMLingServer


if TYPE_CHECKING:
    from pathlib import Path

logger = get_logger(__name__)

cli = t.Typer(
    name="MCP Server",
    help=(
        "🚀 MCP Server CLI interface. Run and manage the MCP protocol server! 🚀\n\n"
        "Check out https://github.com/your-repo/mcp-server-llmling !"
    ),
    no_args_is_help=True,
)

# Command groups for list subcommand
list_cli = t.Typer(help="List available components.", no_args_is_help=True)
cli.add_typer(list_cli, name="list")

# Common option definitions
CONFIG_HELP = "Path to LLMling configuration file"
TRANSPORT_HELP = "Transport type (stdio or sse)"
HOST_HELP = "Host address for SSE transport"
PORT_HELP = "Port number for SSE transport"
INJ_PORT_HELP = "Port for config injection server"
INJ_HOST_HELP = "Host for config injection server"
NAME_HELP = "Server name for MCP protocol"
TIMEOUT_HELP = "Connection timeout in seconds"
VERBOSE_HELP = "Enable verbose output"
QUIET_HELP = "Suppress non-essential output"

# Option command tuples
CONFIG_CMDS = "-c", "--config"
TRANSPORT_CMDS = "-t", "--transport"
HOST_CMDS = "-h", "--host"
PORT_CMDS = "-p", "--port"
NAME_CMDS = "-n", "--name"
VERBOSE_CMDS = "-v", "--verbose"
QUIET_CMDS = "-q", "--quiet"


class LogLevel(str, Enum):
    """Valid logging levels."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


def validate_transport(value: str) -> str:
    """Validate transport type."""
    if value not in {"stdio", "sse"}:
        msg = f"Invalid transport type: {value}. Must be 'stdio' or 'sse'"
        raise t.BadParameter(msg)
    return value


def version_callback(value: bool) -> None:
    """Print version and exit if --version is used."""
    if value:
        t.echo(f"MCP Server version: {__version__}")
        raise t.Exit


def verbose_callback(ctx: t.Context, _param: t.CallbackParam, value: bool) -> bool:
    """Set up verbose logging."""
    if value:
        logging.getLogger().setLevel(logging.DEBUG)
    return value


def quiet_callback(ctx: t.Context, _param: t.CallbackParam, value: bool) -> bool:
    """Set up quiet logging."""
    if value:
        logging.getLogger().setLevel(logging.ERROR)
    return value


@cli.command()
def start(
    # ""..."" for required
    config_path: str = t.Argument(config_resources.TEST_CONFIG, help=CONFIG_HELP),
    transport: str = t.Option(
        "stdio",
        *TRANSPORT_CMDS,
        help=TRANSPORT_HELP,
        callback=validate_transport,
    ),
    host: str = t.Option("localhost", *HOST_CMDS, help=HOST_HELP),
    port: int = t.Option(8000, *PORT_CMDS, help=PORT_HELP),
    injection_host: str = t.Option("localhost", help=INJ_HOST_HELP),
    injection_port: int = t.Option(8765, help=INJ_PORT_HELP),
    server_name: str = t.Option(constants.SERVER_NAME, *NAME_CMDS, help=NAME_HELP),
    log_level: LogLevel = t.Option(  # noqa: B008
        LogLevel.INFO,
        "-l",
        "--log-level",
        case_sensitive=False,
    ),
    timeout: float = t.Option(30.0, help=TIMEOUT_HELP),
    enable_injection: bool = t.Option(False, help="Enable config injection server"),
    zed_mode: bool = t.Option(
        False,
        "--zed-mode",
        help="Enable Zed editor compatibility mode",
    ),
    verbose: bool = t.Option(
        False, *VERBOSE_CMDS, help=VERBOSE_HELP, callback=verbose_callback
    ),
    quiet: bool = t.Option(False, *QUIET_CMDS, help=QUIET_HELP, callback=quiet_callback),
    version: bool = t.Option(None, "--version", callback=version_callback, is_eager=True),  # type: ignore
) -> None:
    """Start the MCP protocol server."""
    try:
        logging.getLogger().setLevel(log_level.value.upper())
        transport_options: dict[str, Any] = {}
        if transport == "sse":
            transport_options = {"host": host, "port": port}

        with RuntimeConfig.open_sync(config_path) as runtime:
            server = LLMLingServer(
                runtime=runtime,
                transport=transport,  # type: ignore
                name=server_name,
                transport_options=transport_options,
                enable_injection=enable_injection,
                injection_port=injection_port,
                zed_mode=zed_mode,
            )
            asyncio.run(server.start(raise_exceptions=True))
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception:
        logger.exception("Server startup failed")
        sys.exit(1)


@cli.command()
def info(
    verbose: bool = t.Option(
        False, *VERBOSE_CMDS, help=VERBOSE_HELP, callback=verbose_callback
    ),
):
    """Show server information and capabilities."""
    info_data = {
        "Version": __version__,
        "Python": sys.version,
        "Platform": sys.platform,
        "Supported transports": ["stdio", "sse"],
        "Default ports": {
            "SSE": 8000,
            "Injection": 8765,
        },
    }
    for key, value in info_data.items():
        t.echo(f"{key}: {value}")


@cli.command()
def inject(
    config_path: Path = t.Argument(  # noqa: B008
        ..., help="Path to configuration file to inject", exists=True
    ),
    host: str = t.Option("localhost", *HOST_CMDS, help=HOST_HELP),
    port: int = t.Option(8765, *PORT_CMDS, help=PORT_HELP),
    verbose: bool = t.Option(
        False, *VERBOSE_CMDS, help=VERBOSE_HELP, callback=verbose_callback
    ),
):
    """Inject configuration into a running server."""
    import httpx

    try:
        with config_path.open("rb") as f:
            data = f.read()
        url = f"http://{host}:{port}/inject-config"
        response = httpx.post(url, content=data)
        response.raise_for_status()
        t.echo("Configuration injected successfully")
    except Exception as e:  # noqa: BLE001
        t.echo(f"Failed to inject configuration: {e}", err=True)
        sys.exit(1)


def run() -> None:
    """Entry point for the CLI."""
    if os.name == "nt":  # Windows
        policy = asyncio.WindowsSelectorEventLoopPolicy()  # type: ignore[attr-defined]
        asyncio.set_event_loop_policy(policy)
    cli()


if __name__ == "__main__":
    run()
