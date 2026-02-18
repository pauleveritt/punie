"""Toad initialization diagnostic capture.

Records every WebSocket message and phase milestone during the Toad
initialization sequence with millisecond timestamps. Writes a JSONL log
on exit so the stuck-initializing problem can be diagnosed post-mortem.

Usage (automatic via run_toad_websocket.py):
    Log is written to ~/.punie/logs/toad-debug.jsonl on exit.

Log format — one JSON object per line:
    {"event": "start",  "wall": "...", "server_url": "..."}
    {"event": "phase",  "elapsed_ms": 12.3, "phase": "connect_start"}
    {"event": "send",   "elapsed_ms": 14.1, "method": "initialize", "id": "...", "body": "..."}
    {"event": "recv",   "elapsed_ms": 18.7, "method": null, "id": "...", "has_result": true, "body": "..."}
    {"event": "error",  "elapsed_ms": 30000.1, "where": "acp_initialize", "type": "TimeoutError", "message": "..."}
    {"event": "exit",   "elapsed_ms": 30001.2, "last_phase": "acp_initialize_start", "reached_ready": false}

Phase sequence (happy path):
    connect_start → connect_done
    initialize_start → initialize_done
    new_session_start → new_session_done
    listen_loop_start
    acp_initialize_start → acp_initialize_done
    acp_new_session_start → acp_new_session_done
    agent_ready

If the log ends before agent_ready, the last phase shows where it hung.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__all__ = ["ToadCapture", "DiagnosticWebSocket"]

# Truncate message bodies longer than this to keep log files readable
_BODY_LIMIT = 800


def _parse_message_summary(data: str) -> dict[str, Any]:
    """Extract key fields from a JSON-RPC message for the summary column."""
    try:
        msg = json.loads(data)
        return {
            "method": msg.get("method"),
            "id": msg.get("id"),
            "has_result": "result" in msg,
            "has_error": "error" in msg,
            "error": msg.get("error"),
            # Include result keys for initialize/new_session responses
            "result_keys": list(msg["result"].keys()) if msg.get("result") else None,
        }
    except Exception:
        return {"raw_prefix": data[:80]}


@dataclass
class ToadCapture:
    """Captures all WebSocket messages and phase transitions for one Toad session.

    Thread-safe for diagnostic purposes (CPython GIL protects list.append).
    Designed to be created once at script startup and written on exit.
    """

    server_url: str = ""
    _t0: float = field(default_factory=time.monotonic, init=False)
    _events: list[dict[str, Any]] = field(default_factory=list, init=False)

    def _now(self) -> float:
        return round((time.monotonic() - self._t0) * 1000, 1)

    def start(self, server_url: str) -> None:
        """Record session start (call immediately after construction)."""
        self.server_url = server_url
        self._events.append({
            "event": "start",
            "elapsed_ms": 0.0,
            "wall": datetime.now(timezone.utc).isoformat(),
            "server_url": server_url,
        })

    def phase(self, name: str, **extra: Any) -> None:
        """Record a named phase milestone."""
        self._events.append({
            "event": "phase",
            "elapsed_ms": self._now(),
            "phase": name,
            **extra,
        })

    def on_send(self, data: str | bytes) -> None:
        """Record an outbound WebSocket message."""
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")
        summary = _parse_message_summary(data)
        self._events.append({
            "event": "send",
            "elapsed_ms": self._now(),
            **summary,
            "body": data[:_BODY_LIMIT] + ("…" if len(data) > _BODY_LIMIT else ""),
        })

    def on_recv(self, data: str) -> None:
        """Record an inbound WebSocket message."""
        summary = _parse_message_summary(data)
        self._events.append({
            "event": "recv",
            "elapsed_ms": self._now(),
            **summary,
            "body": data[:_BODY_LIMIT] + ("…" if len(data) > _BODY_LIMIT else ""),
        })

    def on_route(
        self, message_type: str, method: str | None, destination: str
    ) -> None:
        """Record a routing decision made in _listen_loop.

        Args:
            message_type: "response", "request", "notification", or "invalid".
            method: JSON-RPC method name if present, else None.
            destination: Human-readable routing destination (e.g. "API.process_response").
        """
        self._events.append({
            "event": "route",
            "elapsed_ms": self._now(),
            "message_type": message_type,
            "method": method,
            "destination": destination,
        })

    def on_error(self, where: str, exc: BaseException) -> None:
        """Record an exception."""
        self._events.append({
            "event": "error",
            "elapsed_ms": self._now(),
            "where": where,
            "type": type(exc).__name__,
            "message": str(exc),
        })

    def wrap(self, ws: Any) -> "DiagnosticWebSocket":
        """Wrap a websockets ClientConnection with capture instrumentation."""
        return DiagnosticWebSocket(ws, self)

    def write(self, path: Path | None = None) -> Path:
        """Write captured events to JSONL log. Returns the path written."""
        if path is None:
            path = Path.home() / ".punie" / "logs" / "toad-debug.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)

        phases = [e["phase"] for e in self._events if e["event"] == "phase"]
        last_phase = phases[-1] if phases else "none"
        reached_ready = "agent_ready" in phases
        error_count = sum(1 for e in self._events if e["event"] == "error")

        # Final exit summary event
        exit_event = {
            "event": "exit",
            "elapsed_ms": self._now(),
            "last_phase": last_phase,
            "reached_ready": reached_ready,
            "error_count": error_count,
            "total_messages": sum(
                1 for e in self._events if e["event"] in ("send", "recv")
            ),
        }

        with open(path, "w") as f:
            for event in self._events:
                f.write(json.dumps(event) + "\n")
            f.write(json.dumps(exit_event) + "\n")

        return path


class DiagnosticWebSocket:
    """Transparent proxy around a websockets ClientConnection.

    Intercepts send() and recv() to record all messages with timing.
    All other attribute accesses fall through to the underlying socket.
    """

    def __init__(self, ws: Any, capture: ToadCapture) -> None:
        # Store as object.__setattr__ to avoid triggering __setattr__ on the proxy
        object.__setattr__(self, "_ws", ws)
        object.__setattr__(self, "_capture", capture)

    async def send(self, data: str | bytes) -> None:
        self._capture.on_send(data)
        await self._ws.send(data)

    async def recv(self) -> str:
        data = await self._ws.recv()
        self._capture.on_recv(data)
        return data

    async def close(self, *args: Any, **kwargs: Any) -> None:
        await self._ws.close(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(object.__getattribute__(self, "_ws"), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(object.__getattribute__(self, "_ws"), name, value)
