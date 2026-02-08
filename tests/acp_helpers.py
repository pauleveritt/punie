"""ACP test helpers: re-exports from punie.testing.

This module provides backward compatibility for existing tests.
All functionality has been moved to punie.testing package.
"""

from punie.testing import FakeAgent, FakeClient, LoopbackServer

# Backward compatibility alias
_Server = LoopbackServer

__all__ = ["FakeAgent", "FakeClient", "LoopbackServer", "_Server"]
