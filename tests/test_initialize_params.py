"""The MCP initialize request we send must match the MCP spec."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from mcp import types
from mcp.shared.version import SUPPORTED_PROTOCOL_VERSIONS

from mcp_server_llmling.http_client import HTTPClientConfig
from mcp_server_llmling.mcp_inproc_session import MCPInProcSession, initialize_params


if TYPE_CHECKING:
    import pytest


def test_initialize_params_are_valid_mcp() -> None:
    params = initialize_params()
    assert set(params) == {"protocolVersion", "capabilities", "clientInfo"}
    assert params["protocolVersion"] == types.LATEST_PROTOCOL_VERSION
    assert params["protocolVersion"] in SUPPORTED_PROTOCOL_VERSIONS
    request = types.InitializeRequest(params=types.InitializeRequestParams.model_validate(params))
    assert request.method == "initialize"


async def test_do_handshake_sends_mcp_initialize(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MCPInProcSession()
    sent: list[tuple[str, dict[str, Any] | None]] = []

    async def send_request(method: str, params: dict[str, Any] | None = None, **_: Any) -> Any:
        sent.append((method, params))
        return {"protocolVersion": types.LATEST_PROTOCOL_VERSION}

    async def send_notification(method: str, params: dict[str, Any] | None = None) -> None:
        sent.append((method, params))

    monkeypatch.setattr(session, "send_request", send_request)
    monkeypatch.setattr(session, "send_notification", send_notification)
    await session.do_handshake()
    assert sent == [("initialize", initialize_params()), ("notifications/initialized", {})]


def test_http_client_config_defaults_to_latest_revision() -> None:
    assert HTTPClientConfig(server_url="http://x").protocol_version in (SUPPORTED_PROTOCOL_VERSIONS)
