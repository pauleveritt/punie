# Testing Strategy: Init Command

## Test Categories

### Pure Function Tests (9 tests)

**Advantages:**
- Fast, no I/O
- Easy to reason about
- Cover edge cases exhaustively

#### `resolve_punie_command()` (2 tests)

```python
def test_resolve_punie_command_finds_executable(monkeypatch):
    """When punie is on PATH, return absolute path"""
    monkeypatch.setattr(shutil, "which", lambda x: "/usr/local/bin/punie")
    command, args = resolve_punie_command()
    assert command == "/usr/local/bin/punie"
    assert args == []

def test_resolve_punie_command_uvx_fallback(monkeypatch):
    """When punie not found, use uvx fallback"""
    monkeypatch.setattr(shutil, "which", lambda x: None)
    command, args = resolve_punie_command()
    assert command == "uvx"
    assert args == ["punie"]
```

#### `generate_acp_config()` (3 tests)

```python
def test_generate_acp_config_basic():
    """Basic config structure"""
    config = generate_acp_config("/usr/bin/punie", [], {})
    assert config["agent_servers"]["punie"]["command"] == "/usr/bin/punie"
    assert config["default_mcp_settings"]["use_idea_mcp"] is True

def test_generate_acp_config_with_env():
    """PUNIE_MODEL in env"""
    config = generate_acp_config(
        "/usr/bin/punie",
        [],
        {"PUNIE_MODEL": "claude-opus-4"}
    )
    assert config["agent_servers"]["punie"]["env"]["PUNIE_MODEL"] == "claude-opus-4"

def test_generate_acp_config_uvx_args():
    """uvx invocation includes args"""
    config = generate_acp_config("uvx", ["punie"], {})
    assert config["agent_servers"]["punie"]["command"] == "uvx"
    assert config["agent_servers"]["punie"]["args"] == ["punie"]
```

#### `merge_acp_config()` (4 tests)

```python
def test_merge_acp_config_preserves_other_agents():
    """Other agents not affected"""
    existing = {
        "agent_servers": {
            "other": {"command": "/bin/other", "args": []}
        }
    }
    punie_config = generate_acp_config("/usr/bin/punie", [], {})
    merged = merge_acp_config(existing, punie_config)
    assert "other" in merged["agent_servers"]
    assert "punie" in merged["agent_servers"]

def test_merge_acp_config_updates_existing_punie():
    """Punie entry updated if exists"""
    existing = {
        "agent_servers": {
            "punie": {"command": "/old/punie", "args": []}
        }
    }
    punie_config = generate_acp_config("/new/punie", [], {})
    merged = merge_acp_config(existing, punie_config)
    assert merged["agent_servers"]["punie"]["command"] == "/new/punie"

def test_merge_acp_config_adds_missing_defaults():
    """default_mcp_settings added if absent"""
    existing = {"agent_servers": {}}
    punie_config = generate_acp_config("/usr/bin/punie", [], {})
    merged = merge_acp_config(existing, punie_config)
    assert "default_mcp_settings" in merged

def test_merge_does_not_mutate_original():
    """No mutation of input dicts"""
    existing = {"agent_servers": {}}
    punie_config = generate_acp_config("/usr/bin/punie", [], {})
    merged = merge_acp_config(existing, punie_config)
    assert existing is not merged
    assert "punie" not in existing["agent_servers"]
```

### CLI Integration Tests (4 tests)

**Uses:** `typer.testing.CliRunner` with temp files

```python
def test_cli_init_creates_file(tmp_path):
    """punie init writes acp.json"""
    output = tmp_path / "acp.json"
    result = runner.invoke(app, ["init", "--output", str(output)])
    assert result.exit_code == 0
    assert output.exists()
    data = json.loads(output.read_text())
    assert "agent_servers" in data
    assert "punie" in data["agent_servers"]

def test_cli_init_with_model(tmp_path):
    """--model flag sets env"""
    output = tmp_path / "acp.json"
    result = runner.invoke(
        app,
        ["init", "--model", "claude-opus-4", "--output", str(output)]
    )
    data = json.loads(output.read_text())
    assert data["agent_servers"]["punie"]["env"]["PUNIE_MODEL"] == "claude-opus-4"

def test_cli_init_merges_existing(tmp_path):
    """Merges with existing config"""
    output = tmp_path / "acp.json"
    existing = {
        "agent_servers": {
            "other": {"command": "/bin/other", "args": []}
        }
    }
    output.write_text(json.dumps(existing))

    result = runner.invoke(app, ["init", "--output", str(output)])
    data = json.loads(output.read_text())
    assert "other" in data["agent_servers"]
    assert "punie" in data["agent_servers"]

def test_cli_init_help():
    """Help text shows init options"""
    result = runner.invoke(app, ["init", "--help"])
    assert "--model" in result.stdout
    assert "--output" in result.stdout
```

## Test Fixtures

```python
import pytest
from typer.testing import CliRunner

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_punie_path(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda x: "/usr/local/bin/punie")
```

## Coverage Goals

- 100% coverage of pure functions
- CLI integration covers success paths + merge scenario
- Edge cases: missing config, invalid JSON (future enhancement)
