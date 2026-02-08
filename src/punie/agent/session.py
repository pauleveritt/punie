"""Session-scoped state management for Punie agents.

This module provides immutable session state caching to avoid redundant
tool discovery calls within a single agent session.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydantic_ai import Agent as PydanticAgent

    from punie.agent.deps import ACPDeps
    from punie.agent.discovery import ToolCatalog


@dataclass(frozen=True)
class SessionState:
    """Immutable session-scoped cached state.

    Holds the discovered tool catalog, and configured PydanticAgent for reuse
    across multiple prompt() calls within the same session.

    >>> # Example construction (with dummy values for illustration)
    >>> from punie.agent.discovery import ToolCatalog
    >>> state = SessionState(
    ...     catalog=ToolCatalog(tools=()),
    ...     agent=None,  # type: ignore[arg-type]
    ...     discovery_tier=1
    ... )
    >>> state.discovery_tier
    1
    >>> state.catalog.tools
    ()
    """

    catalog: "ToolCatalog | None"
    """Tool catalog from discovery (None if Tier 2/3 fallback)."""

    agent: "PydanticAgent[ACPDeps, str]"
    """Configured PydanticAgent instance for this session."""

    discovery_tier: int
    """Discovery tier used: 1=catalog, 2=capabilities, 3=default."""
