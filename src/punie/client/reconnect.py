"""Reconnection logic with exponential backoff for Punie clients.

Wraps punie_session() with automatic retry on connection failure,
using exponential backoff with optional jitter.
"""

from __future__ import annotations

import asyncio
import logging
import random
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator, Callable

from punie.client.connection import punie_session

logger = logging.getLogger(__name__)

__all__ = ["ReconnectConfig", "reconnecting_session", "DEFAULT_RECONNECT"]

#: Callback type for state change notifications.
StateCallback = Callable[[str], None]


@dataclass(frozen=True)
class ReconnectConfig:
    """Configuration for reconnection behavior.

    Attributes:
        initial_delay: First retry delay in seconds.
        max_delay: Maximum retry delay in seconds.
        backoff_factor: Multiplier applied to delay after each failure.
        max_retries: Maximum number of reconnection attempts (0 = unlimited).
        jitter: If True, add random jitter to avoid thundering herd.
    """

    initial_delay: float = 1.0
    max_delay: float = 30.0
    backoff_factor: float = 2.0
    max_retries: int = 10
    jitter: bool = True


#: Default reconnection config used when none is specified.
DEFAULT_RECONNECT = ReconnectConfig()


@asynccontextmanager
async def reconnecting_session(
    server_url: str,
    cwd: str,
    config: ReconnectConfig | None = None,
    on_state_change: StateCallback | None = None,
) -> AsyncIterator[tuple[Any, str]]:
    """Context manager that wraps punie_session() with reconnection.

    Attempts to connect to the server, retrying with exponential backoff
    on failure. Once connected, yields (websocket, session_id).

    Args:
        server_url: WebSocket URL (e.g., ws://localhost:8000/ws)
        cwd: Current working directory for session
        config: Reconnection configuration. Defaults to DEFAULT_RECONNECT.
        on_state_change: Optional callback(state_str) for state transitions.
                         States: "connecting", "connected", "reconnecting", "failed"

    Yields:
        (websocket, session_id) tuple from punie_session()

    Raises:
        ConnectionError: If max_retries exceeded without successful connection.

    Example:
        async with reconnecting_session("ws://localhost:8000/ws", "/workspace") as (ws, sid):
            await receive_messages(ws, ...)

        # With state notifications:
        def on_state(state: str) -> None:
            print(f"Connection state: {state}")

        async with reconnecting_session(url, cwd, on_state_change=on_state) as (ws, sid):
            ...
    """
    if config is None:
        config = DEFAULT_RECONNECT

    attempt = 0
    delay = config.initial_delay

    while True:
        state = "connecting" if attempt == 0 else "reconnecting"
        logger.info(f"Session state: {state} (attempt {attempt + 1})")
        if on_state_change:
            try:
                on_state_change(state)
            except Exception as exc:
                logger.warning(f"on_state_change error: {exc}")

        try:
            async with punie_session(server_url, cwd) as (websocket, session_id):
                logger.info(f"Connected: session_id={session_id}")
                if on_state_change:
                    try:
                        on_state_change("connected")
                    except Exception as exc:
                        logger.warning(f"on_state_change error: {exc}")

                yield websocket, session_id
                return  # Clean exit — no retry needed

        except (ConnectionError, OSError) as exc:
            attempt += 1
            logger.warning(f"Connection failed (attempt {attempt}): {exc}")

            # Check max retries (0 = unlimited)
            if config.max_retries > 0 and attempt >= config.max_retries:
                logger.error(f"Max retries ({config.max_retries}) exceeded")
                if on_state_change:
                    try:
                        on_state_change("failed")
                    except Exception as cb_exc:
                        logger.warning(f"on_state_change error: {cb_exc}")
                raise ConnectionError(
                    f"Failed to connect to {server_url} after {attempt} attempts: {exc}"
                ) from exc

            # Calculate backoff delay
            actual_delay = min(delay, config.max_delay)
            if config.jitter:
                actual_delay *= 0.5 + random.random() * 0.5  # 50%-100% of delay

            logger.info(f"Retrying in {actual_delay:.1f}s...")
            await asyncio.sleep(actual_delay)

            # Increase delay for next attempt
            delay = min(delay * config.backoff_factor, config.max_delay)
