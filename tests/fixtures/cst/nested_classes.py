"""Fixture with a nested class inside a valid component.

Used to verify that _class_stack correctly handles nested classes:
- Inner class leaving should NOT clobber outer class tracking
- Outer class __call__ should still be detected after inner class is visited
"""
from dataclasses import dataclass

from tdom import Node


@dataclass
class OuterComponent:
    """Valid tdom component with a nested helper class."""

    name: str = "World"

    class _Formatter:
        """Nested helper — no component signals, should be skipped."""

        def format(self, s: str) -> str:
            return s.upper()

    def __call__(self) -> Node:
        return Node("div", {}, [f"Hello {self.name}!"])
