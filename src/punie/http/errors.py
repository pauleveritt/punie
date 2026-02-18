"""JSON-RPC error types for the HTTP/WebSocket layer.

Provides typed exceptions that map to JSON-RPC 2.0 error codes.
"""

from __future__ import annotations

__all__ = ["MethodNotFoundError"]


class MethodNotFoundError(RuntimeError):
    """Raised when a JSON-RPC method is not recognized.

    Maps to JSON-RPC error code -32601 (Method not found).
    """

    json_rpc_code: int = -32601
