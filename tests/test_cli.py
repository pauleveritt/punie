"""Tests for CLI module.

Tests are organized into groups:
1. Pure function tests (resolve_model, setup_logging, init functions) — no Typer
2. Typer CLI tests (--version, --help, init, serve) — using CliRunner
"""

import json
import logging
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from punie.cli import (
    app,
    generate_acp_config,
    merge_acp_config,
    resolve_model,
    resolve_punie_command,
    run_serve_agent,
    setup_logging,
)

runner = CliRunner()


@pytest.fixture(autouse=True)
def clean_root_logger():
    """Remove all handlers from root logger after test.

    setup_logging() modifies global state (root logger). This fixture ensures
    tests don't leak handlers between test runs.
    """
    yield
    root = logging.getLogger()
    for handler in root.handlers[:]:
        handler.close()
        root.removeHandler(handler)


# === Pure function tests: resolve_model() ===


def test_resolve_model_flag_takes_priority(monkeypatch):
    """CLI flag overrides PUNIE_MODEL env var."""
    monkeypatch.setenv("PUNIE_MODEL", "claude-3-5-sonnet")
    assert resolve_model("test") == "test"


def test_resolve_model_env_var_fallback(monkeypatch):
    """PUNIE_MODEL env var used when no flag provided."""
    monkeypatch.setenv("PUNIE_MODEL", "claude-3-5-sonnet")
    assert resolve_model(None) == "claude-3-5-sonnet"


def test_resolve_model_default(monkeypatch):
    """Returns 'test' when no flag or env var set."""
    monkeypatch.delenv("PUNIE_MODEL", raising=False)
    assert resolve_model(None) == "test"


# === Pure function tests: setup_logging() ===


def test_setup_logging_creates_directory(tmp_path):
    """setup_logging() creates log directory if missing."""
    log_dir = tmp_path / "logs"
    setup_logging(log_dir, "info")
    assert log_dir.exists()
    assert (log_dir / "punie.log").exists()


def test_setup_logging_configures_file_handler(tmp_path):
    """Root logger gets RotatingFileHandler."""
    log_dir = tmp_path / "logs"
    setup_logging(log_dir, "info")

    root = logging.getLogger()
    handlers = root.handlers

    # File handler should be RotatingFileHandler
    file_handlers = [h for h in handlers if hasattr(h, "baseFilename")]
    assert len(file_handlers) == 1
    assert str(log_dir / "punie.log") in str(file_handlers[0].baseFilename)


def test_setup_logging_no_stdout_handler(tmp_path):
    """No handler points to stdout (ACP owns stdout)."""
    log_dir = tmp_path / "logs"
    setup_logging(log_dir, "info")

    root = logging.getLogger()
    for handler in root.handlers:
        if hasattr(handler, "stream"):
            # StreamHandler exists (stderr handler)
            import sys

            assert handler.stream is not sys.stdout


def test_setup_logging_sets_level(tmp_path):
    """Root logger level matches config."""
    log_dir = tmp_path / "logs"
    setup_logging(log_dir, "debug")

    root = logging.getLogger()
    assert root.level == logging.DEBUG


def test_setup_logging_expands_user_path():
    """Tilde paths are expanded."""
    setup_logging(Path("~/.punie/logs"), "info")
    root = logging.getLogger()

    # Find file handler
    file_handlers = [h for h in root.handlers if hasattr(h, "baseFilename")]
    assert len(file_handlers) == 1

    # Path should be expanded (no tilde)
    assert "~" not in str(file_handlers[0].baseFilename)


# === Typer CLI tests ===


def test_cli_version():
    """--version prints version to stderr and exits 0."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "punie 0.1.0" in result.stderr
    # Version should NOT be in stdout (ACP owns stdout)
    assert "punie" not in result.stdout


def test_cli_help():
    """--help shows help text."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "AI coding agent" in result.stdout
    # Phase 28: Main command is now stdio bridge, not agent runner
    assert "--server" in result.stdout  # Connects to server via WebSocket
    assert "--log-dir" in result.stdout
    assert "--log-level" in result.stdout
    assert "--version" in result.stdout


# === Pure function tests: resolve_punie_command() ===


def test_resolve_punie_command_finds_executable(monkeypatch):
    """When punie is on PATH, return absolute path."""
    monkeypatch.setattr(shutil, "which", lambda x: "/usr/local/bin/punie")
    command, args = resolve_punie_command()
    assert command == "/usr/local/bin/punie"
    assert args == []


def test_resolve_punie_command_uvx_fallback(monkeypatch):
    """When punie not found, use uvx fallback."""
    monkeypatch.setattr(shutil, "which", lambda x: None)
    command, args = resolve_punie_command()
    assert command == "uvx"
    assert args == ["punie"]


# === Pure function tests: generate_acp_config() ===


def test_generate_acp_config_basic():
    """Basic config structure."""
    config = generate_acp_config("/usr/bin/punie", [], {})
    assert config["agent_servers"]["punie"]["command"] == "/usr/bin/punie"
    assert config["agent_servers"]["punie"]["args"] == []
    assert config["agent_servers"]["punie"]["env"] == {}
    assert config["default_mcp_settings"]["use_idea_mcp"] is True
    assert config["default_mcp_settings"]["use_custom_mcp"] is True


def test_generate_acp_config_with_env():
    """PUNIE_MODEL in env."""
    config = generate_acp_config("/usr/bin/punie", [], {"PUNIE_MODEL": "claude-opus-4"})
    assert config["agent_servers"]["punie"]["env"]["PUNIE_MODEL"] == "claude-opus-4"


def test_generate_acp_config_uvx_args():
    """uvx invocation includes args."""
    config = generate_acp_config("uvx", ["punie"], {})
    assert config["agent_servers"]["punie"]["command"] == "uvx"
    assert config["agent_servers"]["punie"]["args"] == ["punie"]


# === Pure function tests: merge_acp_config() ===


def test_merge_acp_config_preserves_other_agents():
    """Other agents not affected."""
    existing = {"agent_servers": {"other": {"command": "/bin/other", "args": []}}}
    punie_config = generate_acp_config("/usr/bin/punie", [], {})
    merged = merge_acp_config(existing, punie_config)
    assert "other" in merged["agent_servers"]
    assert "punie" in merged["agent_servers"]


def test_merge_acp_config_updates_existing_punie():
    """Punie entry updated if exists."""
    existing = {"agent_servers": {"punie": {"command": "/old/punie", "args": []}}}
    punie_config = generate_acp_config("/new/punie", [], {})
    merged = merge_acp_config(existing, punie_config)
    assert merged["agent_servers"]["punie"]["command"] == "/new/punie"


def test_merge_acp_config_adds_missing_defaults():
    """default_mcp_settings added if absent."""
    existing = {"agent_servers": {}}
    punie_config = generate_acp_config("/usr/bin/punie", [], {})
    merged = merge_acp_config(existing, punie_config)
    assert "default_mcp_settings" in merged
    assert merged["default_mcp_settings"]["use_idea_mcp"] is True


def test_merge_does_not_mutate_original():
    """No mutation of input dicts."""
    existing = {"agent_servers": {}}
    punie_config = generate_acp_config("/usr/bin/punie", [], {})
    merged = merge_acp_config(existing, punie_config)
    assert existing is not merged
    assert "punie" not in existing["agent_servers"]


# === CLI integration tests: init command ===


def test_cli_init_creates_file(tmp_path, monkeypatch):
    """punie init writes acp.json with local model by default."""
    monkeypatch.setattr(shutil, "which", lambda x: "/usr/local/bin/punie")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)  # No venv for clean test
    output = tmp_path / "acp.json"
    result = runner.invoke(app, ["init", "--output", str(output), "--no-venv"])
    assert result.exit_code == 0
    assert output.exists()
    data = json.loads(output.read_text())
    assert "agent_servers" in data
    assert "punie" in data["agent_servers"]
    assert data["agent_servers"]["punie"]["command"] == "/usr/local/bin/punie"
    # Verify local model is default
    assert data["agent_servers"]["punie"]["env"]["PUNIE_MODEL"] == "local"


def test_cli_init_with_model(tmp_path, monkeypatch):
    """--model flag sets env."""
    monkeypatch.setattr(shutil, "which", lambda x: "/usr/local/bin/punie")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    output = tmp_path / "acp.json"
    result = runner.invoke(
        app,
        ["init", "--model", "claude-opus-4", "--output", str(output), "--no-venv"],
    )
    assert result.exit_code == 0
    data = json.loads(output.read_text())
    assert data["agent_servers"]["punie"]["env"]["PUNIE_MODEL"] == "claude-opus-4"


def test_cli_init_merges_existing(tmp_path, monkeypatch):
    """Merges with existing config."""
    monkeypatch.setattr(shutil, "which", lambda x: "/usr/local/bin/punie")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    output = tmp_path / "acp.json"
    existing = {"agent_servers": {"other": {"command": "/bin/other", "args": []}}}
    output.write_text(json.dumps(existing))

    result = runner.invoke(app, ["init", "--output", str(output), "--no-venv"])
    assert result.exit_code == 0
    data = json.loads(output.read_text())
    assert "other" in data["agent_servers"]
    assert "punie" in data["agent_servers"]


def test_cli_init_help():
    """Help text shows init options."""
    result = runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0
    assert "--model" in result.stdout
    assert "--output" in result.stdout
    assert "JetBrains ACP configuration" in result.stdout


# === Async helper tests: run_serve_agent() ===


@pytest.mark.asyncio
async def test_run_serve_agent_creates_agent(monkeypatch):
    """run_serve_agent creates PunieAgent and calls run_http."""
    from punie.http.types import Host, Port

    agent_created = False
    run_http_called = False

    class MockAgent:
        def __init__(self, model, name):
            nonlocal agent_created
            agent_created = True
            assert model == "test"
            assert name == "test-agent"

    async def mock_run_http(agent, app, host, port, log_level):
        nonlocal run_http_called
        run_http_called = True
        assert isinstance(agent, MockAgent)
        assert host == Host("127.0.0.1")
        assert port == Port(8000)
        assert log_level == "info"

    monkeypatch.setattr("punie.cli.PunieAgent", MockAgent)
    monkeypatch.setattr("punie.cli.run_http", mock_run_http)

    await run_serve_agent("test", "test-agent", "127.0.0.1", 8000, "info")

    assert agent_created
    assert run_http_called


# === CLI integration tests: serve command ===


def test_cli_serve_help():
    """Help text shows serve-specific flags."""
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--host" in result.stdout
    assert "--port" in result.stdout
    assert "--model" in result.stdout
    assert "--name" in result.stdout
    # Phase 28: Serve now runs HTTP/WebSocket only (not dual protocol)
    assert "websocket" in result.stdout.lower()


def test_cli_help_shows_subcommands():
    """Main help lists init and serve."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.stdout
    assert "serve" in result.stdout


def test_serve_sets_up_logging(tmp_path, monkeypatch):
    """Logging configured before agent starts."""
    log_dir = tmp_path / "logs"

    # Mock run_serve_agent to avoid actually starting server
    async def mock_run_serve_agent(*args):
        pass

    monkeypatch.setattr("punie.cli.run_serve_agent", mock_run_serve_agent)

    runner.invoke(app, ["serve", "--log-dir", str(log_dir), "--log-level", "debug"])

    # Log directory should be created
    assert log_dir.exists()
    assert (log_dir / "punie.log").exists()


def test_serve_resolves_model(monkeypatch):
    """Model resolution chain works."""
    resolved_model = None

    async def capture_model(model, name, host, port, log_level):
        nonlocal resolved_model
        resolved_model = model

    monkeypatch.setattr("punie.cli.run_serve_agent", capture_model)
    monkeypatch.setenv("PUNIE_MODEL", "claude-opus-4")

    runner.invoke(app, ["serve"])

    assert resolved_model == "claude-opus-4"


def test_serve_model_flag_overrides_env(monkeypatch):
    """--model flag takes priority."""
    resolved_model = None

    async def capture_model(model, name, host, port, log_level):
        nonlocal resolved_model
        resolved_model = model

    monkeypatch.setattr("punie.cli.run_serve_agent", capture_model)
    monkeypatch.setenv("PUNIE_MODEL", "claude-opus-4")

    runner.invoke(app, ["serve", "--model", "claude-haiku-3"])

    assert resolved_model == "claude-haiku-3"
