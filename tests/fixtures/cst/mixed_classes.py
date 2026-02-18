"""Fixture with a valid component plus a plain helper class.

Used to verify that _ComponentVisitor does not false-positive on
non-component classes (helper classes, exceptions, mixins).
"""
from dataclasses import dataclass

from tdom import Node


@dataclass
class Greeting:
    """Valid tdom component."""

    name: str = "World"

    def __call__(self) -> Node:
        return Node("div", {}, [f"Hello {self.name}!"])


class HelperFormatter:
    """Plain helper class with no component signals.

    Should NOT be flagged by validate_component — it has no @dataclass,
    no __call__, and no html() usage.
    """

    def format_name(self, name: str) -> str:
        return name.strip().title()
