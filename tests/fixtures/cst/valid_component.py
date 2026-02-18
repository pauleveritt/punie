"""Valid tdom component fixture.

A properly-formed tdom component with @dataclass, __call__ -> Node,
and html() rendering. Uses a regular string for compatibility with
LibCST (t-strings are Python 3.14 only).
"""
from dataclasses import dataclass

from tdom import Node


@dataclass
class Greeting:
    """Greeting component that displays a welcome message."""

    name: str = "World"

    def __call__(self) -> Node:
        return Node("div", {}, [Node("h1", {}, [f"Hello {self.name}!"])])
