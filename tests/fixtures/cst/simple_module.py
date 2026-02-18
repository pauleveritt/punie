"""Simple Python module fixture for testing cst_find_pattern and cst_rename."""
import os
from typing import Optional


def greet(name: str) -> str:
    """Return a greeting message."""
    return f"Hello, {name}!"


def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


class Calculator:
    """Simple calculator class."""

    def multiply(self, x: int, y: int) -> int:
        """Multiply two numbers."""
        return x * y

    def divide(self, x: int, y: int) -> Optional[float]:
        """Divide x by y, returning None if y is 0."""
        if y == 0:
            return None
        return x / y
