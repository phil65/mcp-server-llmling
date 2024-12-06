"""Factory functions for creating server instances."""

from __future__ import annotations

from typing import TYPE_CHECKING

from llmling import config_resources
from llmling.config.manager import ConfigManager
from llmling.config.runtime import RuntimeConfig
import logfire

from mcp_server_llmling.log import get_logger


if TYPE_CHECKING:
    import os


logger = get_logger(__name__)


@logfire.instrument("Creating runtime configuration")
def create_runtime_config(
    config_path: str | os.PathLike[str] | None = None,
) -> RuntimeConfig:
    """Create runtime configuration for server setup.

    This is a helper function for setting up server configuration.
    The caller is responsible for managing the RuntimeConfig context.

    Warning:
            The returned RuntimeConfig must be used within a context manager
            to ensure proper dependency initialization and cleanup:
            ```python
            runtime = create_runtime_config("config.yml")
            async with runtime as r:
                # Use runtime here
                resource = await r.load_resource("name")


    Args:
        config_path: Optional path to config file (uses test config if None)

    Returns:
        Uninitialized RuntimeConfig instance

    Example:
        ```python
        runtime = create_runtime_config("myconfig.yml")
        async with runtime as r:
            server = create_server(r)
            await server.start()
        ```
    """
    path = config_path or config_resources.TEST_CONFIG
    manager = ConfigManager.load(path)
    return RuntimeConfig.from_config(manager.config)


if __name__ == "__main__":
    import depkit

    manager = depkit.DependencyManager()
    print(manager)
