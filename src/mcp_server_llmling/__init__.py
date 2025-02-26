"""MCP protocol server implementation for LLMling."""

__version__ = "0.5.7"

from fsspec_httpx import register

register()

from mcp_server_llmling.server import LLMLingServer


__all__ = ["LLMLingServer"]
