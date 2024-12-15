# mcp-server-llmling

[![PyPI License](https://img.shields.io/pypi/l/mcp-server-llmling.svg)](https://pypi.org/project/mcp-server-llmling/)
[![Package status](https://img.shields.io/pypi/status/mcp-server-llmling.svg)](https://pypi.org/project/mcp-server-llmling/)
[![Daily downloads](https://img.shields.io/pypi/dd/mcp-server-llmling.svg)](https://pypi.org/project/mcp-server-llmling/)
[![Weekly downloads](https://img.shields.io/pypi/dw/mcp-server-llmling.svg)](https://pypi.org/project/mcp-server-llmling/)
[![Monthly downloads](https://img.shields.io/pypi/dm/mcp-server-llmling.svg)](https://pypi.org/project/mcp-server-llmling/)
[![Distribution format](https://img.shields.io/pypi/format/mcp-server-llmling.svg)](https://pypi.org/project/mcp-server-llmling/)
[![Wheel availability](https://img.shields.io/pypi/wheel/mcp-server-llmling.svg)](https://pypi.org/project/mcp-server-llmling/)
[![Python version](https://img.shields.io/pypi/pyversions/mcp-server-llmling.svg)](https://pypi.org/project/mcp-server-llmling/)
[![Implementation](https://img.shields.io/pypi/implementation/mcp-server-llmling.svg)](https://pypi.org/project/mcp-server-llmling/)
[![Releases](https://img.shields.io/github/downloads/phil65/mcp-server-llmling/total.svg)](https://github.com/phil65/mcp-server-llmling/releases)
[![Github Contributors](https://img.shields.io/github/contributors/phil65/mcp-server-llmling)](https://github.com/phil65/mcp-server-llmling/graphs/contributors)
[![Github Discussions](https://img.shields.io/github/discussions/phil65/mcp-server-llmling)](https://github.com/phil65/mcp-server-llmling/discussions)
[![Github Forks](https://img.shields.io/github/forks/phil65/mcp-server-llmling)](https://github.com/phil65/mcp-server-llmling/forks)
[![Github Issues](https://img.shields.io/github/issues/phil65/mcp-server-llmling)](https://github.com/phil65/mcp-server-llmling/issues)
[![Github Issues](https://img.shields.io/github/issues-pr/phil65/mcp-server-llmling)](https://github.com/phil65/mcp-server-llmling/pulls)
[![Github Watchers](https://img.shields.io/github/watchers/phil65/mcp-server-llmling)](https://github.com/phil65/mcp-server-llmling/watchers)
[![Github Stars](https://img.shields.io/github/stars/phil65/mcp-server-llmling)](https://github.com/phil65/mcp-server-llmling/stars)
[![Github Repository size](https://img.shields.io/github/repo-size/phil65/mcp-server-llmling)](https://github.com/phil65/mcp-server-llmling)
[![Github last commit](https://img.shields.io/github/last-commit/phil65/mcp-server-llmling)](https://github.com/phil65/mcp-server-llmling/commits)
[![Github release date](https://img.shields.io/github/release-date/phil65/mcp-server-llmling)](https://github.com/phil65/mcp-server-llmling/releases)
[![Github language count](https://img.shields.io/github/languages/count/phil65/mcp-server-llmling)](https://github.com/phil65/mcp-server-llmling)
[![Github commits this week](https://img.shields.io/github/commit-activity/w/phil65/mcp-server-llmling)](https://github.com/phil65/mcp-server-llmling)
[![Github commits this month](https://img.shields.io/github/commit-activity/m/phil65/mcp-server-llmling)](https://github.com/phil65/mcp-server-llmling)
[![Github commits this year](https://img.shields.io/github/commit-activity/y/phil65/mcp-server-llmling)](https://github.com/phil65/mcp-server-llmling)
[![Package status](https://codecov.io/gh/phil65/mcp-server-llmling/branch/main/graph/badge.svg)](https://codecov.io/gh/phil65/mcp-server-llmling/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyUp](https://pyup.io/repos/github/phil65/mcp-server-llmling/shield.svg)](https://pyup.io/repos/github/phil65/mcp-server-llmling/)

[Read the documentation!](https://phil65.github.io/mcp-server-llmling/)



# LLMling Server Manual


## Overview

mcp-server-llmling is a server for the Machine Chat Protocol (MCP) that provides a YAML-based configuration system for LLM applications.

[LLMLing](https://phil65.github.io/LLMling/), the backend,  provides a YAML-based configuration system for LLM applications.
It allows to set up custom MCP servers serving content defined in YAML files.

- **Static Declaration**: Define your LLM's environment in YAML - no code required
- **MCP Protocol**: Built on the Machine Chat Protocol (MCP) for standardized LLM interaction
- **Component Types**:
  - **Resources**: Content providers (files, text, CLI output, etc.)
  - **Prompts**: Message templates with arguments
  - **Tools**: Python functions callable by the LLM

The YAML configuration creates a complete environment that provides the LLM with:
- Access to content via resources
- Structured prompts for consistent interaction
- Tools for extending capabilities


## Key Features

### 1. Resource Management
- Load and manage different types of resources:
  - Text files (`PathResource`)
  - Raw text content (`TextResource`)
  - CLI command output (`CLIResource`)
  - Python source code (`SourceResource`)
  - Python callable results (`CallableResource`)
  - Images (`ImageResource`)
- Support for resource watching/hot-reload
- Resource processing pipelines
- URI-based resource access

### 2. Tool System
- Register and execute Python functions as LLM tools
- Support for OpenAPI-based tools
- Entry point-based tool discovery
- Tool validation and parameter checking
- Structured tool responses

### 3. Prompt Management
- Static prompts with template support
- Dynamic prompts from Python functions
- File-based prompts
- Prompt argument validation
- Completion suggestions for prompt arguments

### 4. Multiple Transport Options
- Stdio-based communication (default)
- Server-Sent Events (SSE) for web clients
- Support for custom transport implementations




## Usage

### With Zed Editor

Add LLMLing as a context server in your `settings.json`:

```json
{
  "context_servers": {
    "llmling": {
      "command": {
        "env": {},
        "label": "llmling",
        "path": "uvx",
        "args": [
          "mcp-server-llmling",
          "start",
          "path/to/your/config.yml"
        ]
      },
      "settings": {}
    }
  }
}
```

### With Claude Desktop

Configure LLMLing in your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "llmling": {
      "command": "uvx",
      "args": [
        "mcp-server-llmling",
        "start",
        "path/to/your/config.yml"
      ],
      "env": {}
    }
  }
}
```

### Manual Server Start

Start the server directly from command line:

```bash
# Latest version
uvx mcp-server-llmling@latest
```

### 1. Programmatic usage

```python
from llmling import RuntimeConfig
from mcp_server_llmling import LLMLingServer

async def main() -> None:
    async with RuntimeConfig.open(config) as runtime:
        server = LLMLingServer(runtime, enable_injection=True)
        await server.start()

asyncio.run(main())
```

### 2. Using Custom Transport

```python
from llmling import RuntimeConfig
from mcp_server_llmling import LLMLingServer

async def main() -> None:
    async with RuntimeConfig.open(config) as runtime:
        server = LLMLingServer(
            config,
            transport="sse",
            transport_options={
                "host": "localhost",
                "port": 8000,
                "cors_origins": ["http://localhost:3000"]
            }
        )
        await server.start()

asyncio.run(main())
```

### 3. Resource Configuration

```yaml
resources:
  python_code:
    type: path
    path: "./src/**/*.py"
    watch:
      enabled: true
      patterns:
        - "*.py"
        - "!**/__pycache__/**"

  api_docs:
    type: text
    content: |
      API Documentation
      ================
      ...
```

### 4. Tool Configuration

```yaml
tools:
  analyze_code:
    import_path: "mymodule.tools.analyze_code"
    description: "Analyze Python code structure"

toolsets:
  api:
    type: openapi
    spec: "https://api.example.com/openapi.json"
    namespace: "api"
```

## Server Configuration

The server is configured through a YAML file with the following sections:

```yaml
global_settings:
  timeout: 30
  max_retries: 3
  log_level: "INFO"
  requirements: []
  pip_index_url: null
  extra_paths: []

resources:
  # Resource definitions...

tools:
  # Tool definitions...

toolsets:
  # Toolset definitions...

prompts:
  # Prompt definitions...
```

## MCP Protocol

The server implements the MCP protocol which supports:

1. **Resource Operations**
   - List available resources
   - Read resource content
   - Watch for resource changes

2. **Tool Operations**
   - List available tools
   - Execute tools with parameters
   - Get tool schemas

3. **Prompt Operations**
   - List available prompts
   - Get formatted prompts
   - Get completions for prompt arguments

4. **Notifications**
   - Resource changes
   - Tool/prompt list updates
   - Progress updates
   - Log messages
