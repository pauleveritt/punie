"""Punie: AI coding agent that delegates tool execution to PyCharm via ACP.

This package provides:
- ACP protocol implementation (vendored from upstream)
- Pydantic AI agent adapter for ACP protocol
- HTTP server support for dual-protocol operation
- Testing utilities for ACP protocol development
"""

from punie.acp import Agent, Client
from punie.agent import ACPDeps, ACPToolset, PunieAgent, create_pydantic_agent
from punie.http import create_app, run_dual
from punie.testing import FakeAgent, FakeClient, LoopbackServer

__all__ = [
    # ACP Protocol
    "Agent",
    "Client",
    # Pydantic AI Agent
    "ACPDeps",
    "ACPToolset",
    "PunieAgent",
    "create_pydantic_agent",
    # HTTP Server
    "create_app",
    "run_dual",
    # Testing
    "FakeAgent",
    "FakeClient",
    "LoopbackServer",
]
__version__ = "0.1.0"
