from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    import mcp


SERVER_NAME = "llmling-server"
SERVER_CMD = [sys.executable, "-m", "mcp_server_llmling", "start"]


LOG_LEVEL_MAP: dict[mcp.LoggingLevel, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "notice": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
    "alert": logging.CRITICAL,
    "emergency": logging.CRITICAL,
}
