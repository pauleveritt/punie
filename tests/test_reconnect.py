"""Tests for punie.client.reconnect — reconnection with exponential backoff."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest

from punie.client.reconnect import DEFAULT_RECONNECT, ReconnectConfig, reconnecting_session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_success_session(websocket_stub: Any, session_id: str = "test-session"):
    """Return a punie_session context manager that yields successfully."""
    @asynccontextmanager
    async def _session(url: str, cwd: str) -> AsyncIterator[tuple[Any, str]]:
        yield websocket_stub, session_id

    return _session


def make_failing_session(exc: Exception, succeed_after: int = 0):
    """Return a punie_session that fails `succeed_after` times then succeeds."""
    call_count = 0
    fake_ws = AsyncMock()

    @asynccontextmanager
    async def _session(url: str, cwd: str) -> AsyncIterator[tuple[Any, str]]:
        nonlocal call_count
        call_count += 1
        if call_count <= succeed_after:
            raise exc
        yield fake_ws, "recovered-session"

    return _session, fake_ws


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconnecting_session_connects_first_try():
    """Should succeed immediately when server is available."""
    fake_ws = AsyncMock()
    config = ReconnectConfig(max_retries=3, initial_delay=0.01)

    with patch("punie.client.reconnect.punie_session", make_success_session(fake_ws)):
        async with reconnecting_session(
            "ws://localhost:8000/ws", "/workspace", config
        ) as (ws, sid):
            assert sid == "test-session"
            assert ws is fake_ws


@pytest.mark.asyncio
async def test_reconnecting_session_retries_after_failure():
    """Should retry after connection failure and eventually succeed."""
    failing_session, fake_ws = make_failing_session(
        ConnectionError("connection refused"), succeed_after=2
    )
    config = ReconnectConfig(max_retries=5, initial_delay=0.01, jitter=False)
    states: list[str] = []

    with patch("punie.client.reconnect.punie_session", failing_session):
        async with reconnecting_session(
            "ws://localhost:8000/ws",
            "/workspace",
            config,
            on_state_change=states.append,
        ) as (ws, sid):
            assert sid == "recovered-session"

    assert "reconnecting" in states
    assert "connected" in states


@pytest.mark.asyncio
async def test_reconnecting_session_raises_after_max_retries():
    """Should raise ConnectionError when max_retries exceeded."""
    _, fake_ws = make_failing_session(ConnectionError("refused"), succeed_after=999)
    config = ReconnectConfig(max_retries=3, initial_delay=0.01, jitter=False)
    states: list[str] = []

    @asynccontextmanager
    async def _always_fail(url: str, cwd: str) -> AsyncIterator:
        raise ConnectionError("connection refused")
        yield  # unreachable but satisfies generator type

    with patch("punie.client.reconnect.punie_session", _always_fail):
        with pytest.raises(ConnectionError, match="after 3 attempts"):
            async with reconnecting_session(
                "ws://localhost:8000/ws",
                "/workspace",
                config,
                on_state_change=states.append,
            ) as _:
                pass

    assert "failed" in states


@pytest.mark.asyncio
async def test_reconnecting_session_state_change_sequence():
    """Should emit 'connecting' then 'connected' on first attempt."""
    fake_ws = AsyncMock()
    config = ReconnectConfig(max_retries=3, initial_delay=0.01)
    states: list[str] = []

    with patch("punie.client.reconnect.punie_session", make_success_session(fake_ws)):
        async with reconnecting_session(
            "ws://localhost:8000/ws",
            "/workspace",
            config,
            on_state_change=states.append,
        ) as _:
            pass

    assert states[0] == "connecting"
    assert "connected" in states


@pytest.mark.asyncio
async def test_reconnecting_session_exponential_backoff():
    """Delays should grow exponentially up to max_delay."""
    call_count = 0
    delays_slept: list[float] = []
    fake_ws = AsyncMock()
    succeed_on = 4

    @asynccontextmanager
    async def _flaky_session(url: str, cwd: str) -> AsyncIterator:
        nonlocal call_count
        call_count += 1
        if call_count < succeed_on:
            raise ConnectionError("temporary failure")
        yield fake_ws, "session-ok"

    original_sleep = asyncio.sleep

    async def capture_sleep(delay: float) -> None:
        delays_slept.append(delay)
        await original_sleep(0)  # Don't actually wait

    config = ReconnectConfig(
        max_retries=5,
        initial_delay=1.0,
        max_delay=10.0,
        backoff_factor=2.0,
        jitter=False,
    )

    with patch("punie.client.reconnect.punie_session", _flaky_session):
        with patch("asyncio.sleep", capture_sleep):
            async with reconnecting_session(
                "ws://localhost:8000/ws", "/workspace", config
            ) as _:
                pass

    # Should have slept 3 times (3 failures before 4th success)
    assert len(delays_slept) == 3
    # Each delay should grow: 1.0, 2.0, 4.0
    assert delays_slept[0] == pytest.approx(1.0)
    assert delays_slept[1] == pytest.approx(2.0)
    assert delays_slept[2] == pytest.approx(4.0)


def test_reconnect_config_defaults():
    """DEFAULT_RECONNECT should have sensible values."""
    assert DEFAULT_RECONNECT.initial_delay == 1.0
    assert DEFAULT_RECONNECT.max_delay == 30.0
    assert DEFAULT_RECONNECT.backoff_factor == 2.0
    assert DEFAULT_RECONNECT.max_retries == 10
    assert DEFAULT_RECONNECT.jitter is True


def test_reconnect_config_is_frozen():
    """ReconnectConfig should be immutable."""
    with pytest.raises((AttributeError, TypeError)):
        DEFAULT_RECONNECT.max_retries = 99  # type: ignore[misc]
