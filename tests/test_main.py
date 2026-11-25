"""Tests for the CLI entry point."""

from __future__ import annotations

import asyncio
import sys
from typing import TYPE_CHECKING

from mcp_server_llmling import __main__ as main_mod


if TYPE_CHECKING:
    import pytest


def test_loop_factory_windows_uses_selector_loop(monkeypatch: pytest.MonkeyPatch) -> None:
    """On Windows the server runs on a selector loop (no global loop policy)."""
    monkeypatch.setattr(sys, "platform", "win32")
    assert main_mod.loop_factory() is asyncio.SelectorEventLoop


def test_loop_factory_default_elsewhere(monkeypatch: pytest.MonkeyPatch) -> None:
    """Other platforms keep asyncio's default loop."""
    monkeypatch.setattr(sys, "platform", "linux")
    assert main_mod.loop_factory() is None
