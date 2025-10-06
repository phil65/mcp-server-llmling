"""MCP protocol server implementation for LLMling."""

from __future__ import annotations

from importlib.metadata import version

__version__ = version("mcp-server-llmling")

import upathtools

from mcp_server_llmling.server import LLMLingServer

upathtools.register_http_filesystems()

__all__ = [
    "LLMLingServer",
    "__version__",
]
