"""Punie: AI coding agent that delegates tool execution to PyCharm via ACP.

This package provides:
- ACP protocol implementation (vendored from upstream)
- Testing utilities for ACP protocol development
"""

from punie.acp import Agent, Client
from punie.testing import FakeAgent, FakeClient, LoopbackServer

__all__ = ["Agent", "Client", "FakeAgent", "FakeClient", "LoopbackServer"]
__version__ = "0.1.0"
