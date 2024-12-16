from llmling import Config, RuntimeConfig
from llmling.prompts.models import DynamicPrompt
import pytest


@pytest.mark.asyncio
async def test_zed_function_wrapping():
    """Test that function wrapping properly handles multiple arguments."""

    # Define a test function
    def test_func(main_arg: str, opt1: str = "default", opt2: bool = False) -> str:
        return f"Main: {main_arg}, Opt1: {opt1}, Opt2: {opt2}"

    # Create a prompt using this function
    prompt = DynamicPrompt(
        name="test",
        description="Test prompt",
        import_path="mcp_server_llmling.testing.test_func",
    )

    # Create runtime config
    config = Config(prompts={"test": prompt})
    async with RuntimeConfig.open(config) as runtime:
        # Enable Zed mode
        from mcp_server_llmling.zed_wrapper import prepare_runtime_for_zed

        print("before", runtime._prompt_registry._items)

        prepare_runtime_for_zed(runtime)
        print("after", runtime._prompt_registry._items)

        print(runtime._prompt_registry._items)
        # Get wrapped prompt
        wrapped = runtime._prompt_registry["test"]

        # Test that it accepts single string input
        messages = await wrapped.format({
            "input": "main_value :: opt1=custom | opt2=true"
        })

        # format returns a list of PromptMessages, so we need to get the content
        result = messages[1].get_text_content()  # user message is second
        assert "Main: main_value" in result
        assert "Opt1: custom" in result
        assert "Opt2: True" in result


@pytest.mark.asyncio
async def test_zed_wrapping_conditions():
    """Test that Zed wrapping only happens for multi-parameter functions."""
    # Create prompts for each
    prompts = {
        "multi": DynamicPrompt(
            name="multi",
            description="Multi-arg prompt",
            import_path="mcp_server_llmling.testing.test_func_multi",
        ),
        "single": DynamicPrompt(
            name="single",
            description="Single-arg prompt",
            import_path="mcp_server_llmling.testing.test_func_single",
        ),
        "zero": DynamicPrompt(
            name="zero",
            description="Zero-arg prompt",
            import_path="mcp_server_llmling.testing.test_func_zero",
        ),
    }

    # Create runtime config with all prompts
    config = Config(prompts=prompts)  # type: ignore
    async with RuntimeConfig.open(config) as runtime:
        # Enable Zed mode
        from mcp_server_llmling.zed_wrapper import prepare_runtime_for_zed

        # Store original import paths
        original_paths = {
            name: prompt.import_path  # type: ignore
            for name, prompt in runtime._prompt_registry.items()
        }

        prepare_runtime_for_zed(runtime)

        # Check multi-arg prompt was wrapped
        multi_prompt = runtime._prompt_registry["multi"]
        assert len(multi_prompt.arguments) == 1
        assert multi_prompt.arguments[0].name == "input"
        assert multi_prompt.import_path != original_paths["multi"]  # type: ignore

        assert "zed_wrapped" in multi_prompt.import_path  # type: ignore

        # Check single-arg prompt was not wrapped
        single_prompt = runtime._prompt_registry["single"]
        assert len(single_prompt.arguments) == 1
        assert single_prompt.arguments[0].name == "arg"
        assert single_prompt.import_path == original_paths["single"]  # type: ignore

        # Check zero-arg prompt was not wrapped
        zero_prompt = runtime._prompt_registry["zero"]
        assert len(zero_prompt.arguments) == 0
        assert zero_prompt.import_path == original_paths["zero"]  # type: ignore

        # Test that multi-arg prompt works with Zed format
        messages = await multi_prompt.format({
            "input": "main_value :: opt1=custom | opt2=true"
        })
        result = messages[1].get_text_content()
        assert "Main: main_value" in result
        assert "Opt1: custom" in result
        assert "Opt2: True" in result

        # Test that single-arg prompt works normally
        messages = await single_prompt.format({"arg": "test"})
        result = messages[1].get_text_content()
        assert "Single: test" in result

        # Test that zero-arg prompt works normally
        messages = await zero_prompt.format({})
        result = messages[1].get_text_content()
        assert "Zero args" in result


if __name__ == "__main__":
    pytest.main(["-v", "-s", __file__])
