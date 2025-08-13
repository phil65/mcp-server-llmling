"""MCP protocol server implementation for LLMling."""

__version__ = "0.5.14"


import upathtools

from mcp_server_llmling.server import LLMLingServer

upathtools.register_http_filesystems()

__all__ = ["LLMLingServer"]
