"""mcp-server-llmling: main package.

MCP (Model context protocol) server with LLMling backend.
"""

from __future__ import annotations

from importlib.metadata import version

__version__ = version("mcp-server-llmling")
__title__ = "mcp-server-llmling"

__author__ = "Philipp Temminghoff"
__author_email__ = "philipptemminghoff@googlemail.com"
__copyright__ = "Copyright (c) 2024 Philipp Temminghoff"
__license__ = "MIT"
__url__ = "https://github.com/phil65/mcp-server-llmling"

import upathtools

from mcp_server_llmling.server import LLMLingServer

upathtools.register_http_filesystems()

__all__ = [
    "LLMLingServer",
    "__version__",
]
