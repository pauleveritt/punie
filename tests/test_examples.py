"""Tests that verify all examples work correctly."""

import importlib.util
import inspect
from pathlib import Path
from types import ModuleType

import anyio
import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


def get_example_modules() -> list[ModuleType]:
    """Get all Python example files as imported modules."""
    modules: list[ModuleType] = []

    for py_file in sorted(EXAMPLES_DIR.glob("*.py")):
        # Skip __init__.py and test files
        if py_file.name.startswith("__") or py_file.name.startswith("test_"):
            continue

        module_name = py_file.stem
        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            modules.append(module)

    return modules


@pytest.mark.parametrize("example_module", get_example_modules())
def test_example_runs_without_error(example_module: ModuleType) -> None:
    """Test that each example runs without errors."""
    # Check if module has a main function
    if not hasattr(example_module, "main"):
        pytest.skip(f"Module {example_module.__name__} has no main function")

    main_func = getattr(example_module, "main")

    # Check if main is async
    if inspect.iscoroutinefunction(main_func):
        # Run async main
        anyio.run(main_func)
    else:
        # Run sync main
        main_func()
