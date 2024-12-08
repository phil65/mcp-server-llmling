from __future__ import annotations

import asyncio
import socket
import time


MESSAGE_OK = 200


def find_free_port() -> int:
    """Find a free port by letting OS assign one."""
    with socket.socket() as s:
        s.bind(("", 0))  # Bind to any address, random port
        return s.getsockname()[1]  # Return the port number


async def wait_for_injection_server(port: int, timeout: float = 5.0) -> None:
    """Wait for injection server to be ready."""
    import httpx

    start = time.monotonic()
    while True:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"http://localhost:{port}/docs")
                if response.status_code == MESSAGE_OK:
                    return
        except Exception:  # noqa: BLE001
            if time.monotonic() - start > timeout:
                msg = "Injection server did not start"
                raise TimeoutError(msg)  # noqa: B904
            await asyncio.sleep(0.1)
