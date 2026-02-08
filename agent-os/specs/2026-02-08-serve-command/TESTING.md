# Testing Strategy: Serve Command

## Test Categories

### Async Helper Tests (1 test)

**Purpose:** Test agent creation without CliRunner complexity

```python
async def test_run_serve_agent_creates_agent(monkeypatch):
    """run_serve_agent creates PunieAgent and calls run_dual"""
    from punie.http.types import Host, Port

    agent_created = False
    run_dual_called = False

    class MockAgent:
        def __init__(self, model, name):
            nonlocal agent_created
            agent_created = True
            assert model == "test"
            assert name == "test-agent"

    async def mock_run_dual(agent, app, host, port, log_level):
        nonlocal run_dual_called
        run_dual_called = True
        assert isinstance(agent, MockAgent)
        assert host == Host("127.0.0.1")
        assert port == Port(8000)
        assert log_level == "info"

    monkeypatch.setattr("punie.cli.PunieAgent", MockAgent)
    monkeypatch.setattr("punie.cli.run_dual", mock_run_dual)

    await run_serve_agent("test", "test-agent", "127.0.0.1", 8000, "info")

    assert agent_created
    assert run_dual_called
```

### CLI Integration Tests (5 tests)

**Uses:** `typer.testing.CliRunner`

```python
def test_cli_serve_help():
    """Help text shows serve-specific flags"""
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "--host" in result.stdout
    assert "--port" in result.stdout
    assert "--model" in result.stdout
    assert "--name" in result.stdout
    assert "dual protocol" in result.stdout.lower()


def test_cli_help_shows_subcommands():
    """Main help lists init and serve"""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "init" in result.stdout
    assert "serve" in result.stdout


def test_serve_sets_up_logging(tmp_path, monkeypatch):
    """Logging configured before agent starts"""
    log_dir = tmp_path / "logs"

    # Mock run_serve_agent to avoid actually starting server
    async def mock_run_serve_agent(*args):
        pass

    monkeypatch.setattr("punie.cli.run_serve_agent", mock_run_serve_agent)

    result = runner.invoke(
        app, ["serve", "--log-dir", str(log_dir), "--log-level", "debug"]
    )

    # Log directory should be created
    assert log_dir.exists()
    assert (log_dir / "punie.log").exists()


def test_serve_resolves_model(monkeypatch):
    """Model resolution chain works"""
    resolved_model = None

    async def capture_model(model, name, host, port, log_level):
        nonlocal resolved_model
        resolved_model = model

    monkeypatch.setattr("punie.cli.run_serve_agent", capture_model)
    monkeypatch.setenv("PUNIE_MODEL", "claude-opus-4")

    result = runner.invoke(app, ["serve"])

    assert resolved_model == "claude-opus-4"


def test_serve_model_flag_overrides_env(monkeypatch):
    """--model flag takes priority"""
    resolved_model = None

    async def capture_model(model, name, host, port, log_level):
        nonlocal resolved_model
        resolved_model = model

    monkeypatch.setattr("punie.cli.run_serve_agent", capture_model)
    monkeypatch.setenv("PUNIE_MODEL", "claude-opus-4")

    result = runner.invoke(app, ["serve", "--model", "claude-haiku-3"])

    assert resolved_model == "claude-haiku-3"
```

## Test Fixtures

```python
import pytest


@pytest.fixture
def mock_http_imports(monkeypatch):
    """Mock punie.http imports to avoid server startup in tests"""

    async def mock_run_dual(agent, app, host, port, log_level):
        pass

    def mock_create_app():
        return None

    monkeypatch.setattr("punie.cli.run_dual", mock_run_dual)
    monkeypatch.setattr("punie.cli.create_app", mock_create_app)
```

## Testing Strategy

**Unit level:**
- Mock `run_dual` to avoid starting actual server
- Test flag parsing and model resolution
- Verify logging setup

**Integration level:**
- Manual testing with `uv run punie serve`
- Verify HTTP endpoints respond
- Verify ACP stdio still works

## Coverage Goals

- Async helper tested with monkeypatch
- CLI integration covers flag combinations
- Help text verified
- Model resolution chain tested
