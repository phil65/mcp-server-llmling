"""Smoke test: the package imports and reports its version."""

import mcp_server_llmling


def test_package_imports() -> None:
    """The package can be imported and exposes a version string."""
    assert isinstance(mcp_server_llmling.__version__, str)
