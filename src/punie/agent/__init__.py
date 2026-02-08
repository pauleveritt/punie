"""Punie agent implementation bridging ACP to Pydantic AI.

This package provides the adapter layer that allows Punie to speak ACP externally
(to PyCharm) while using Pydantic AI internally (for LLM interaction).

Main components:
- ACPDeps: Frozen dataclass holding ACP client connection and session state
- ACPToolset: Pydantic AI toolset exposing ACP Client methods as tools
- PunieAgent: Adapter class implementing ACP Agent protocol
- create_pydantic_agent: Factory function for Pydantic AI agent instances
- ToolCatalog: Immutable catalog of available tools (dynamic discovery)
- ToolDescriptor: Tool metadata and parameter schema
- create_toolset_from_catalog: Build toolset from discovery (Tier 1)
- create_toolset_from_capabilities: Build toolset from capabilities (Tier 2)
"""

from .adapter import PunieAgent
from .deps import ACPDeps
from .discovery import ToolCatalog, ToolDescriptor, parse_tool_catalog
from .factory import create_pydantic_agent
from .toolset import (
    ACPToolset,
    create_toolset,
    create_toolset_from_capabilities,
    create_toolset_from_catalog,
)

__all__ = [
    "ACPDeps",
    "ACPToolset",
    "PunieAgent",
    "ToolCatalog",
    "ToolDescriptor",
    "create_pydantic_agent",
    "create_toolset",
    "create_toolset_from_capabilities",
    "create_toolset_from_catalog",
    "parse_tool_catalog",
]
