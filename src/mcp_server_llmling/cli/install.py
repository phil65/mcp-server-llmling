"""Installation commands for integrating with different editors."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import typer as t

from mcp_server_llmling.log import get_logger


logger = get_logger(__name__)

install_cli = t.Typer(help="Install MCP server in different editors.", name="install")


def get_claude_config_path() -> Path | None:
    """Get the Claude config directory based on platform."""
    match sys.platform:
        case "win32":
            path = Path(Path.home(), "AppData", "Roaming", "Claude")
            return path if path.exists() else None
        case "darwin":
            path = Path(Path.home(), "Library", "Application Support", "Claude")
            return path if path.exists() else None
        case _:
            return None


@install_cli.command()
def claude(
    config_file: Path = t.Argument(  # noqa: B008
        ...,
        exists=True,
        help="Path to LLMling config file",
    ),
    injection: bool = t.Option(False, help="Enable config injection server"),
    injection_port: int = t.Option(
        8765, help="Port for injection server", show_default=True
    ),
    version: str = t.Option("latest", help="Package version to use"),
    dry_run: bool = t.Option(False, help="Show changes without applying them"),
    force: bool = t.Option(False, help="Overwrite existing server if present"),
) -> None:
    """Install MCP server in Claude Desktop."""
    config_dir = get_claude_config_path()
    if not config_dir:
        msg = (
            "Claude Desktop config directory not found. "
            "Please ensure Claude Desktop is installed and has been run at least once."
        )
        t.echo(msg)
        raise t.Exit(code=1)

    config_file_path = config_dir / "claude_desktop_config.json"
    if not config_file_path.exists():
        try:
            config_file_path.write_text("{}")
        except Exception as e:
            msg = f"Failed to create Claude config file: {e}"
            t.echo(msg)
            raise t.Exit(code=1) from e

    try:
        config = json.loads(config_file_path.read_text())
        if "mcpServers" not in config:
            config["mcpServers"] = {}

        server_name = "llmling"
        if server_name in config["mcpServers"] and not force and not dry_run:
            msg = f"Server '{server_name}' already exists. Use --force to overwrite."
            t.echo(msg)
            raise t.Exit(code=1)  # noqa: TRY301

        # Build server command
        path = str(config_file.resolve())
        args = [f"mcp-server-llmling@{version}", "start", path]
        if injection:
            args.extend(["--enable-injection", "--injection-port", str(injection_port)])

        server_config = {"command": "uvx", "args": args}

        if dry_run:
            t.echo(f"Would write to: {config_file_path}")
            t.echo(f"\nServer configuration '{server_name}':")
            t.echo(json.dumps(server_config, indent=2))
            return

        config["mcpServers"][server_name] = server_config
        config_file_path.write_text(json.dumps(config, indent=2))
        t.echo(
            f"Successfully installed '{server_name}' server in Claude Desktop config.",
        )

    except Exception as e:
        msg = f"Failed to update Claude config: {e}"
        t.echo(msg)
        raise t.Exit(code=1) from e


if __name__ == "__main__":
    install_cli()
