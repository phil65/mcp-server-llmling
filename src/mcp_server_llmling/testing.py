from __future__ import annotations


def test_func(main_arg: str, opt1: str = "default", opt2: bool = False) -> str:
    """Function purely for testing."""
    return f"Main: {main_arg}, Opt1: {opt1}, Opt2: {opt2}"


def test_func_multi(main_arg: str, opt1: str = "default", opt2: bool = False) -> str:
    """Function with multiple parameters."""
    return f"Main: {main_arg}, Opt1: {opt1}, Opt2: {opt2}"


def test_func_single(arg: str) -> str:
    """Function with single parameter."""
    return f"Single: {arg}"


def test_func_zero() -> str:
    """Function with no parameters."""
    return "Zero args"
