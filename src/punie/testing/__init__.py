"""Testing utilities for ACP protocol implementations.

Provides fake implementations and test infrastructure for ACP protocol testing.
"""

from .fakes import FakeAgent, FakeClient
from .server import LoopbackServer

__all__ = ["FakeAgent", "FakeClient", "LoopbackServer"]
