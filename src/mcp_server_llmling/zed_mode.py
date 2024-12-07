"""Zed mode functionality for MCP server."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from llmling.prompts.models import (
    BasePrompt,
    DynamicPrompt,
    FilePrompt,
    PromptMessage,
    PromptParameter,
    StaticPrompt,
)


if TYPE_CHECKING:
    from collections.abc import Sequence


class ZedPromptMixin:
    """Mixin providing Zed compatibility for prompts."""

    original_prompt: BasePrompt

    @property
    def arguments(self) -> Sequence[PromptParameter]:
        """Get simplified argument list for Zed."""
        args = ", ".join(a.name for a in self.original_prompt.arguments)
        # Only show single input argument
        return [
            PromptParameter(
                name="input",
                description=(
                    "Format: 'first_arg :: key1=value1 | key2=value2' "
                    f"(Original args: {args})"
                ),
                required=True,
            )
        ]


class ZedStaticPrompt(ZedPromptMixin, StaticPrompt):
    """Static prompt wrapper for Zed."""

    async def format(
        self, arguments: dict[str, Any] | None = None
    ) -> list[PromptMessage]:
        """Format messages using encoded arguments."""
        decoded = decode_zed_args(arguments)
        return await self.original_prompt.format(decoded)


class ZedDynamicPrompt(ZedPromptMixin, DynamicPrompt):
    """Dynamic prompt wrapper for Zed."""

    async def format(
        self, arguments: dict[str, Any] | None = None
    ) -> list[PromptMessage]:
        """Execute callable with decoded arguments."""
        decoded = decode_zed_args(arguments)
        return await self.original_prompt.format(decoded)


class ZedFilePrompt(ZedPromptMixin, FilePrompt):
    """File prompt wrapper for Zed."""

    async def format(
        self, arguments: dict[str, Any] | None = None
    ) -> list[PromptMessage]:
        """Format file content with decoded arguments."""
        decoded = decode_zed_args(arguments)
        return await self.original_prompt.format(decoded)


def decode_zed_args(arguments: dict[str, Any] | None) -> dict[str, Any]:
    """Decode Zed-encoded arguments.

    Args:
        arguments: Dictionary with encoded "input" parameter

    Returns:
        Decoded argument dictionary
    """
    if not arguments or "input" not in arguments:
        return {}

    input_str = arguments["input"]
    if " :: " not in input_str:
        # Single argument case
        first_arg_name = next(iter(arguments)).name
        return {first_arg_name: input_str}

    # Multiple arguments case
    parts = input_str.split(" :: ", 1)
    first_arg_name = next((arg.name for arg in arguments if arg.required), "input")
    result = {first_arg_name: parts[0]}

    if len(parts) > 1:
        for pair in parts[1].split(" | "):
            if not pair:
                continue
            key, value = pair.split("=", 1)
            # Convert value types
            match value.lower():
                case "true":
                    result[key] = True
                case "false":
                    result[key] = False
                case "null":
                    result[key] = None
                case _:
                    try:
                        if "." in value:
                            result[key] = float(value)
                        else:
                            result[key] = int(value)
                    except ValueError:
                        result[key] = value

    return result


def wrap_for_zed(prompt: BasePrompt) -> BasePrompt:
    """Create Zed-compatible wrapper for prompt if needed.

    Args:
        prompt: Original prompt

    Returns:
        Wrapped prompt if multiple arguments, original otherwise
    """
    if len(prompt.arguments) <= 1:
        return prompt

    # Create appropriate wrapper based on prompt type
    match prompt:
        case StaticPrompt():
            wrapper = ZedStaticPrompt(
                name=prompt.name,
                description=prompt.description,
                messages=prompt.messages,
                arguments=prompt.arguments,
                metadata=prompt.metadata,
            )
        case DynamicPrompt():
            wrapper = ZedDynamicPrompt(
                name=prompt.name,
                description=prompt.description,
                import_path=prompt.import_path,
                template=prompt.template,
                completions=prompt.completions,
                arguments=prompt.arguments,
                metadata=prompt.metadata,
            )
        case FilePrompt():
            wrapper = ZedFilePrompt(
                name=prompt.name,
                description=prompt.description,
                path=prompt.path,
                fmt=prompt.fmt,
                watch=prompt.watch,
                arguments=prompt.arguments,
                metadata=prompt.metadata,
            )
        case _:
            msg = f"Unsupported prompt type: {type(prompt)}"
            raise ValueError(msg)

    wrapper.original_prompt = prompt
    return wrapper
