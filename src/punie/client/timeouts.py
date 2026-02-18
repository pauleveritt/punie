"""Centralized timeout configuration for Punie client connections.

All timeout values used by the client layer live here. Import from this
module instead of hardcoding floats in individual files.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Timeouts", "CLIENT_TIMEOUTS"]


@dataclass(frozen=True)
class Timeouts:
    """Centralized timeout values (seconds) for WebSocket client operations.

    Attributes:
        connect_timeout: TCP connection establishment timeout.
        request_timeout: Individual JSON-RPC request/response cycle.
        streaming_timeout: Per-message timeout during streaming responses.
        send_timeout: Single WebSocket frame send timeout.
        idle_timeout: Server-side idle connection timeout.
        grace_period: Session preservation window after client disconnect.
        cleanup_interval: How often the server checks for expired sessions.
        aggregate_timeout: Hard deadline for an entire prompt operation.
    """

    connect_timeout: float = 10.0
    request_timeout: float = 30.0
    streaming_timeout: float = 300.0
    send_timeout: float = 5.0
    idle_timeout: float = 300.0
    grace_period: float = 300.0
    cleanup_interval: float = 60.0
    aggregate_timeout: float = 600.0


#: Default timeouts used throughout the client layer.
CLIENT_TIMEOUTS = Timeouts()
