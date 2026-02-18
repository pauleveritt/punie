"""Tests for managed MLX server integration.

Covers:
- find_local_model() discovery logic
- _maybe_start_mlx_server() integration behavior (mocked)
- build_server_command() uses sys.executable
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from punie.training.server import build_server_command
from punie.training.server_config import ServerConfig, find_local_model


# ── find_local_model() ────────────────────────────────────────────────────────


def test_find_local_model_env_var(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns path from PUNIE_MODEL_PATH env var when set and exists."""
    model_dir = tmp_path / "my_custom_model"
    model_dir.mkdir()
    monkeypatch.setenv("PUNIE_MODEL_PATH", str(model_dir))

    result = find_local_model()
    assert result == model_dir


def test_find_local_model_env_var_missing_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Falls through to glob when PUNIE_MODEL_PATH points to non-existent path."""
    monkeypatch.setenv("PUNIE_MODEL_PATH", str(tmp_path / "does_not_exist"))
    result = find_local_model(search_dir=tmp_path)
    assert result is None


def test_find_local_model_glob_picks_latest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Auto-detects most recent fused_model_* by lexicographic sort."""
    monkeypatch.delenv("PUNIE_MODEL_PATH", raising=False)
    (tmp_path / "fused_model_phase27_cleaned_5bit").mkdir()
    (tmp_path / "fused_model_phase33_5bit").mkdir()
    (tmp_path / "fused_model_phase40_8b_5bit").mkdir()

    result = find_local_model(search_dir=tmp_path)
    assert result is not None
    assert result.name == "fused_model_phase40_8b_5bit"


def test_find_local_model_returns_none_when_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns None when no fused_model_* directories exist."""
    monkeypatch.delenv("PUNIE_MODEL_PATH", raising=False)
    result = find_local_model(search_dir=tmp_path)
    assert result is None


def test_find_local_model_single_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Returns the only candidate when exactly one fused_model_* exists."""
    monkeypatch.delenv("PUNIE_MODEL_PATH", raising=False)
    (tmp_path / "fused_model_phase33b_5bit").mkdir()

    result = find_local_model(search_dir=tmp_path)
    assert result is not None
    assert result.name == "fused_model_phase33b_5bit"


# ── build_server_command() ────────────────────────────────────────────────────


def test_build_server_command_uses_sys_executable() -> None:
    """build_server_command uses sys.executable, not bare 'python'."""
    config = ServerConfig(model_path="fused_model_phase33b_5bit", port=5001)
    cmd = build_server_command(config)

    assert cmd[0] == sys.executable
    assert cmd[0] != "python"


def test_build_server_command_includes_model_and_port() -> None:
    """build_server_command includes required model and port flags."""
    config = ServerConfig(model_path="my_model", port=5001)
    cmd = build_server_command(config)

    assert "--model" in cmd
    assert "my_model" in cmd
    assert "--port" in cmd
    assert "5001" in cmd


# ── _maybe_start_mlx_server() ────────────────────────────────────────────────
# Note: patches target the original module paths because the function uses
# lazy 'from X import Y' imports inside the function body.


def _make_socket_mock(port_in_use: bool) -> MagicMock:
    """Return a socket context manager mock with connect_ex configured."""
    mock_sock = MagicMock()
    mock_sock.__enter__ = MagicMock(return_value=mock_sock)
    mock_sock.__exit__ = MagicMock(return_value=False)
    mock_sock.connect_ex.return_value = 0 if port_in_use else 1
    mock_cls = MagicMock(return_value=mock_sock)
    return mock_cls


@pytest.mark.asyncio
async def test_maybe_start_mlx_server_port_occupied() -> None:
    """When port is occupied, returns model string for existing server, no new process."""
    from punie.cli import _maybe_start_mlx_server

    with patch("punie.cli.socket.socket", _make_socket_mock(port_in_use=True)):
        model_url, server = await _maybe_start_mlx_server(mlx_port=5001)

    assert server is None
    assert "localhost:5001" in model_url
    assert model_url.startswith("local:")


@pytest.mark.asyncio
async def test_maybe_start_mlx_server_no_model_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """When no model found and port free, returns 'local' fallback and None server."""
    from punie.cli import _maybe_start_mlx_server

    monkeypatch.delenv("PUNIE_MODEL_PATH", raising=False)

    with patch("punie.cli.socket.socket", _make_socket_mock(port_in_use=False)):
        # Patch in the module where find_local_model is looked up at import time
        with patch("punie.training.server_config.find_local_model", return_value=None):
            model_url, server = await _maybe_start_mlx_server(mlx_port=5001)

    assert server is None
    assert model_url == "local"


@pytest.mark.asyncio
async def test_maybe_start_mlx_server_starts_managed_server(tmp_path: Path) -> None:
    """When model found and port free, creates and starts a ServerProcess."""
    from punie.cli import _maybe_start_mlx_server

    fake_model = tmp_path / "fused_model_phase33b_5bit"
    fake_model.mkdir()

    mock_server = MagicMock()
    mock_server.start = AsyncMock()
    mock_server.stop = AsyncMock()

    with patch("punie.cli.socket.socket", _make_socket_mock(port_in_use=False)):
        with patch("punie.training.server_config.find_local_model", return_value=fake_model):
            with patch("punie.training.server.ServerProcess", return_value=mock_server):
                model_url, server = await _maybe_start_mlx_server(mlx_port=5001)

    assert server is mock_server
    mock_server.start.assert_awaited_once()
    assert "fused_model_phase33b_5bit" in model_url
    assert model_url.startswith("local:")
    assert "localhost:5001" in model_url
