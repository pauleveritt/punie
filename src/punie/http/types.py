"""HTTP type protocols for Punie.

This module defines protocols for HTTP app factories and related types,
following the protocol-first-design standard.
"""

from typing import NewType, Protocol, runtime_checkable

# Semantic types for HTTP configuration
Host = NewType("Host", str)
"""Network host address (IP or hostname)."""

Port = NewType("Port", int)
"""Network port number (1-65535)."""


@runtime_checkable
class HttpAppFactory(Protocol):
    """Protocol for HTTP app factory functions.

    A factory that creates an ASGI application. This protocol enables
    structural subtyping and runtime type checking.
    """

    def __call__(self) -> object:
        """Create and return an ASGI application.

        Returns:
            An ASGI application (typically Starlette or similar).
        """
        ...
