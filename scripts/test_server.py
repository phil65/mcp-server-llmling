from __future__ import annotations

import asyncio

from llmling import Config, RuntimeConfig

from mcp_server_llmling import LLMLingServer


async def main() -> None:
    # Create minimal config
    res = {"type": "text", "content": "Initial resource"}
    config = Config.model_validate({"global_settings": {}, "resources": {"initial": res}})

    async with RuntimeConfig.from_config(config) as runtime:
        server = LLMLingServer(
            runtime,
            transport="stdio",
            enable_injection=True,  # Enable our injection server
            injection_port=8765,
        )
        print("Starting server with injection endpoint at http://localhost:8765")
        await server.start(raise_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
