"""Punie agent implementation bridging ACP to Pydantic AI.

This package provides the adapter layer that allows Punie to speak ACP externally
(to PyCharm) while using Pydantic AI internally (for LLM interaction).

Main components:
- ACPDeps: Frozen dataclass holding ACP client connection and session state
- ACPToolset: Pydantic AI toolset exposing ACP Client methods as tools
- PunieAgent: Adapter class implementing ACP Agent protocol
- create_pydantic_agent: Factory function for Pydantic AI agent instances
"""

from .adapter import PunieAgent
from .deps import ACPDeps
from .factory import create_pydantic_agent
from .toolset import ACPToolset, create_toolset

__all__ = [
    "ACPDeps",
    "ACPToolset",
    "PunieAgent",
    "create_pydantic_agent",
    "create_toolset",
]
