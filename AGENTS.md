# AGENTS.md

## Overview

`mcp-server-llmling` is an MCP (Model Context Protocol) server whose resources, prompts and
tools come from an [LLMling](https://github.com/phil65/LLMling) YAML config (`llmling.RuntimeConfig`).
It runs on FastMCP 3 / `mcp` 1.x and registers its own low-level MCP request handlers. Optional
extras: a FastAPI "config injection" server for hot-adding components, and a Zed compatibility mode.

## Architecture

All code lives in `src/mcp_server_llmling/`.

- `server.py`: `LLMLingServer`, the core class. Wraps a `RuntimeConfig`, creates a `FastMCP`
  instance, and uses its low-level server (`self.server = self.fastmcp._mcp_server`). Hooks llmling
  registry events (resources/prompts/tools added/changed/removed) to MCP list-changed notifications.
  `start()` connects federated servers, starts the injection server, then
  `fastmcp.run_async(transport, **transport_options)`.
- `handlers.py`: `register_handlers()` attaches the MCP handlers (list/call tools, prompts,
  resources, resource templates, read_resource, completion, subscribe, logging level) to the
  low-level server via decorators. Errors are raised as `mcp.McpError`.
- `conversions.py`: llmling models to `mcp.types` (tools, prompts, resources) and URI mapping
  (`to_mcp_uri` / `from_mcp_uri`, including Windows path handling).
- `log.py`: `MCPHandler`, forwards Python logging to the MCP client as log notifications.
- `server_federation.py` + `http_client.py`: connect to external MCP servers declared under
  `external_servers` in the config (extra key, read from `runtime._config.model_extra`).
- `injection/`: FastAPI app (`server.py` = `ConfigInjectionServer`, `routes.py` = REST + `/ws`
  WebSocket endpoints, `models.py` = request/response models). Only started for stdio transport
  with `enable_injection=True`.
- `zed_wrapper.py`: `prepare_runtime_for_zed()`, wraps multi-arg dynamic prompts into a
  single-string-argument form for Zed.
- `__main__.py`: Typer CLI (`start`, `info`, `inject`, empty `list` group); entry point
  `mcp-server-llmling = mcp_server_llmling.__main__:cli`.
- `cli/install.py`: unregistered Typer app for installing into Claude Desktop config.
- `mcp_inproc_session.py`: `MCPInProcSession`, runs the server as a subprocess over stdio and
  speaks JSON-RPC to it; used by tests.
- `ui/`: experimental NiceGUI dashboard (`gui` extra); not wired into the CLI.
- `testing.py`: sample functions used by tests / Zed mode tests.
- `constants.py`: server name, subprocess command, log level maps.

## Where to look

| Task | File |
| --- | --- |
| Add/change an MCP request handler | `src/mcp_server_llmling/handlers.py` |
| Change how llmling objects map to MCP types / URIs | `src/mcp_server_llmling/conversions.py` |
| Server lifecycle, notifications, transports | `src/mcp_server_llmling/server.py` |
| CLI options | `src/mcp_server_llmling/__main__.py` |
| Injection REST/WebSocket API | `src/mcp_server_llmling/injection/routes.py` |
| External server federation | `src/mcp_server_llmling/server_federation.py`, `http_client.py` |
| Test fixtures (runtime config, in-process client) | `tests/conftest.py` |
| Manual smoke scripts | `scripts/test_server.py`, `scripts/test_injection.py` |

## Commands

```bash
uv sync --all-extras                       # setup (default groups: dev, lint, docs)
uv run pytest                              # tests (addopts: -m "not slow")
uv run ruff check . && uv run ruff format --check .
uv run ty check                            # type check src/ (warnings fail too)
uv run deptry src                          # dependency hygiene
uv run mkdocs-mknodes build                # docs (CI: documentation.yml)
uv build
uv run mcp-server-llmling start [CONFIG] -t streamable-http -p 3001
```

`duties.py` wraps these (`duty test`, `duty lint`, `duty lint_check`, `duty build`, `duty serve`,
`duty version <bump>`). CI (`.github/workflows/build.yml`) runs ruff, ty and pytest on
Python 3.13/3.14 (3.14 is `continue-on-error`) across Linux/macOS/Windows.

## Conventions

- Python >= 3.13, `from __future__ import annotations`, ruff line length 100, Google docstrings.
- Type checker is ty (pinned with ruff in the `lint` group; don't bump per repo). Use targeted
  `# ty: ignore[rule]`, not blanket ignores.
- Tests: `tests/test_*.py`, pytest-asyncio in auto mode; markers `slow`, `unit`, `integration`.
  Protocol tests start a real server subprocess via `MCPInProcSession`.
- Conventional commits (commitizen hook).

## Specs

| Spec | URL | Targets | Code | Update check |
|---|---|---|---|---|
| Model Context Protocol | https://modelcontextprotocol.io/specification/2025-11-25 | 2025-11-25 (`mcp.types.LATEST_PROTOCOL_VERSION` of the locked `mcp` 1.30.0; follows the SDK) | `src/mcp_server_llmling/handlers.py`, `http_client.py`, `mcp_inproc_session.py` | https://modelcontextprotocol.io/specification/latest (redirects to the newest revision), https://github.com/modelcontextprotocol/python-sdk/releases |

## Pitfalls

- `mcp` is capped `<2` and `fastmcp` `<4`: `handlers.py`, `log.py`, `server.py` and
  `http_client.py` use the mcp 1.x low-level API (decorators, `request_context`,
  `streamablehttp_client`), which mcp 2 removed. Moving to FastMCP 4 means porting these.
- FastMCP 3 wraps `read_resource` itself: the handler must return `types.ReadResourceResult`.
- `FastMCP()` no longer accepts `include_tags`, `dependencies`, `tool_serializer`;
  `LLMLingServer` keeps those parameters for compatibility (tags go through `fastmcp.enable`).
- Copier-managed (template `copier-phil65`): `pyproject.toml` skeleton, workflows, `duties.py`,
  `.pre-commit-config.yaml`, `mkdocs.yml`. Don't hand-edit template-owned parts; add
  dependencies below the `# Only add below (Copier)` markers. `uvx tombi format pyproject.toml`
  sorts arrays.
- deptry ignores `schemez`, `universal-pathlib`, `websockets` on purpose (see `[tool.deptry]`).
- Importing the package calls `upathtools.register_http_filesystems()`.
- `nicegui` (`ui/`) is an optional extra; never import it from eagerly loaded modules.
- Logfire instruments the injection app; it warns unless `logfire.configure()` was called.
