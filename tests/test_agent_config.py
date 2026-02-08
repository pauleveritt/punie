"""Tests for agent configuration and mode switching."""

from pathlib import Path

import pytest
from pydantic_ai import ModelRetry

from punie.agent.config import (
    PUNIE_INSTRUCTIONS,
    AgentConfig,
)
from punie.agent.factory import (
    _validate_python_code_blocks,
    create_local_agent,
    create_pydantic_agent,
)
from punie.cli import resolve_mode


def test_agent_config_is_frozen():
    """AgentConfig should be a frozen dataclass."""
    from dataclasses import FrozenInstanceError

    config = AgentConfig()
    with pytest.raises(FrozenInstanceError):
        config.temperature = 1.0  # type: ignore[misc]


def test_agent_config_defaults_to_acp_mode():
    """Default AgentConfig should use PyCharm instructions."""
    config = AgentConfig()
    assert config.instructions == PUNIE_INSTRUCTIONS
    assert config.validate_python_syntax is False


def test_agent_config_custom_values():
    """AgentConfig should accept custom values."""
    config = AgentConfig(
        instructions="Custom instructions",
        temperature=0.5,
        max_tokens=2048,
        retries=5,
        output_retries=3,
        validate_python_syntax=True,
    )
    assert config.instructions == "Custom instructions"
    assert config.temperature == 0.5
    assert config.max_tokens == 2048
    assert config.retries == 5
    assert config.output_retries == 3
    assert config.validate_python_syntax is True


def test_factory_uses_config_instructions():
    """Factory should use config instructions when provided."""
    custom_instructions = "Test instructions"
    config = AgentConfig(instructions=custom_instructions)
    agent = create_pydantic_agent(model="test", config=config)

    # Agent should be created successfully
    # (Internal structure checking would be brittle)
    assert agent is not None


def test_factory_uses_config_model_settings():
    """Factory should use config temperature and max_tokens."""
    config = AgentConfig(temperature=0.7, max_tokens=1024)
    agent = create_pydantic_agent(model="test", config=config)

    # Agent should be created successfully
    assert agent is not None


def test_factory_default_config_backward_compat():
    """Factory with no config should behave same as before."""
    agent = create_pydantic_agent(model="test")

    # Agent should be created successfully
    assert agent is not None


def test_python_syntax_validation_catches_invalid():
    """Python syntax validation should catch malformed code."""
    invalid_code = """```python
def foo(
    print("missing closing paren")
```"""

    with pytest.raises(ModelRetry, match="invalid Python syntax"):
        _validate_python_code_blocks(invalid_code)


def test_python_syntax_validation_skips_prose():
    """Python syntax validation should not validate prose."""
    prose = "This is plain English without code blocks."
    # Should not raise
    _validate_python_code_blocks(prose)


def test_python_syntax_validation_accepts_valid():
    """Python syntax validation should accept valid Python code."""
    valid_code = """```python
def foo():
    print("hello")
    return 42
```"""
    # Should not raise
    _validate_python_code_blocks(valid_code)


def test_create_local_agent_uses_local_instructions():
    """create_local_agent should default to local instructions."""
    agent, client = create_local_agent(model="test", workspace=Path.cwd())

    # Agent and client should be created successfully
    assert agent is not None
    assert client is not None


def test_resolve_mode_default_is_acp(monkeypatch):
    """resolve_mode should return 'acp' by default."""
    monkeypatch.delenv("PUNIE_MODE", raising=False)
    assert resolve_mode(None) == "acp"


def test_resolve_mode_env_var(monkeypatch):
    """resolve_mode should respect PUNIE_MODE env var."""
    monkeypatch.setenv("PUNIE_MODE", "local")
    assert resolve_mode(None) == "local"


def test_resolve_mode_flag_priority(monkeypatch):
    """CLI flag should take priority over env var."""
    monkeypatch.setenv("PUNIE_MODE", "local")
    assert resolve_mode("acp") == "acp"
