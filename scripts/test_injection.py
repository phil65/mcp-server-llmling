from __future__ import annotations

import asyncio

import httpx


YAML_CONFIG = """
resources:
  dynamic_resource:
    type: text
    content: "This was dynamically added!"

tools:
  example_tool:
    import_path: llmling.testing.tools.example_tool
    description: "A test tool"
"""


async def main() -> None:
    async with httpx.AsyncClient() as client:
        # First check what we have
        print("\nGetting initial components...")
        response = await client.get("http://localhost:8765/components")
        print(f"Current components: {response.json()}")

        # Inject new config
        print("\nInjecting new config...")
        yaml_config = """
        resources:
          dynamic_resource:
            type: text
            content: "This was dynamically added!"

        tools:
          example_tool:
            import_path: llmling.testing.tools.example_tool
            description: "A test tool"
        """

        import yaml

        config = yaml.safe_load(yaml_config)
        print(f"Sending config: {config}")

        response = await client.post("http://localhost:8765/inject-config", json=config)
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {response.headers}")
        print(f"Raw response: {response.text}")

        try:
            print(f"JSON response: {response.json()}")
        except Exception as e:  # noqa: BLE001
            print(f"Failed to parse response as JSON: {e}")
        # Check components again
        print("\nChecking updated components...")
        response = await client.get("http://localhost:8765/components")
        print(f"Updated components: {response.json()}")

        # Try to load the new resource
        print("\nTrying to get our new resource...")
        response = await client.get("http://localhost:8765/resources")
        resources = response.json()
        if "dynamic_resource" in resources:
            print(f"Found our resource: {resources['dynamic_resource']}")

        # Check our new tool
        print("\nTrying to get our new tool...")
        response = await client.get("http://localhost:8765/tools")
        if response.status_code != 200:  # noqa: PLR2004
            print(f"Error getting tools: {response.text}")
        else:
            try:
                tools = response.json()
                if "example_tool" in tools:
                    print(f"Found our tool: {tools['example_tool']}")
                else:
                    print("Tool was not found in the response")
            except Exception as e:  # noqa: BLE001
                print(f"Error parsing tool response: {e}")
                print(f"Raw response: {response.text}")


if __name__ == "__main__":
    asyncio.run(main())
