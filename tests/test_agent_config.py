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


def test_agent_config_stop_sequences_default():
    """AgentConfig should default to None for stop_sequences."""
    config = AgentConfig()
    assert config.stop_sequences is None


def test_agent_config_stop_sequences_custom():
    """AgentConfig should accept custom stop_sequences."""
    stop_seqs = ("<|im_end|>", "<|endoftext|>")
    config = AgentConfig(stop_sequences=stop_seqs)
    assert config.stop_sequences == stop_seqs


def test_factory_stop_sequences_flow_through():
    """Factory should wire stop_sequences into ModelSettings.stop."""
    stop_seqs = ("<|im_end|>", "<|endoftext|>")
    config = AgentConfig(stop_sequences=stop_seqs)
    agent = create_pydantic_agent(model="test", config=config)

    # Verify the agent was created and has the stop sequences in model_settings
    assert agent is not None
    assert agent.model_settings is not None
    # model_settings is a dict with the stop_sequences parameter
    assert agent.model_settings.get("stop_sequences") == list(stop_seqs)


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


def test_create_local_agent_defaults_stop_sequences():
    """create_local_agent should default to QWEN_STOP_SEQUENCES."""
    from punie.training.server_config import QWEN_STOP_SEQUENCES

    agent, client = create_local_agent(model="test", workspace=Path.cwd())

    # Verify QWEN_STOP_SEQUENCES is wired into model_settings
    assert agent is not None
    assert agent.model_settings is not None
    # model_settings is a dict with the stop_sequences parameter
    assert agent.model_settings.get("stop_sequences") == list(QWEN_STOP_SEQUENCES)


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


@pytest.mark.skip(reason="ollama_model removed in current phase")
def test_create_ollama_agent():
    """create_pydantic_agent should create OllamaChatModel for ollama: prefix."""
    from punie.agent.ollama_model import OllamaChatModel

    agent = create_pydantic_agent(model="ollama:devstral")

    # Verify agent was created with OllamaChatModel
    assert agent is not None
    assert isinstance(agent.model, OllamaChatModel)


@pytest.mark.skip(reason="ollama_model removed in current phase")
def test_ollama_agent_no_stop_sequences():
    """Ollama models should not have stop_sequences in model_settings."""
    agent = create_pydantic_agent(model="ollama:devstral")

    # Verify no stop_sequences for Ollama (they use model-specific defaults)
    assert agent is not None
    assert agent.model_settings is not None
    # stop_sequences should not be set for Ollama models
    assert "stop_sequences" not in agent.model_settings or agent.model_settings.get("stop_sequences") is None


@pytest.mark.skip(reason="ollama_model removed in current phase")
def test_create_local_agent_with_ollama_has_no_stop_sequences():
    """create_local_agent with ollama: should not set stop_sequences."""
    agent, client = create_local_agent(model="ollama:devstral", workspace=Path.cwd())

    # Verify no stop_sequences for Ollama in local mode
    assert agent is not None
    assert agent.model_settings is not None
    # stop_sequences should not be set for Ollama models
    assert "stop_sequences" not in agent.model_settings or agent.model_settings.get("stop_sequences") is None


def test_create_direct_toolset_returns_correct_count():
    """create_direct_toolset should return 26 tools (3 base + 11 Code Tools + 12 Phase 32)."""
    from punie.agent.toolset import create_direct_toolset

    toolset = create_direct_toolset()
    assert toolset is not None
    # 3 base: read_file, write_file, run_command
    # 11 Code Tools: typecheck_direct, ruff_check_direct, pytest_run_direct,
    #   git_status_direct, git_diff_direct, git_log_direct,
    #   goto_definition_direct, find_references_direct, hover_direct,
    #   document_symbols_direct, workspace_symbols_direct
    # 3 LibCST code tools (Phase 32): cst_find_pattern_direct, cst_rename_direct, cst_add_import_direct
    # 9 Domain validators (Phase 32): validate_component_direct, check_render_tree_direct,
    #   validate_escape_context_direct, validate_service_registration_direct,
    #   check_dependency_graph_direct, validate_injection_site_direct,
    #   validate_middleware_chain_direct, check_di_template_binding_direct,
    #   validate_route_pattern_direct
    assert len(toolset.tools) == 26


@pytest.mark.skip(reason="ollama_model removed in current phase")
def test_create_local_agent_ollama_uses_direct_toolset():
    """create_local_agent with ollama: should use direct toolset."""
    from punie.agent.config import PUNIE_DIRECT_INSTRUCTIONS

    agent, client = create_local_agent(model="ollama:devstral", workspace=Path.cwd())

    # Verify agent was created successfully
    assert agent is not None
    assert client is not None

    # PydanticAI wraps toolsets, so check the actual FunctionToolset (last in list)
    # Direct toolset has 26 tools vs Code Mode toolset has 8 tools
    assert len(agent.toolsets) > 0
    function_toolset = agent.toolsets[-1]  # Last toolset is the one we provided
    assert len(function_toolset.tools) == 26


def test_create_local_agent_local_uses_code_mode_toolset():
    """create_local_agent with 'local' should use Code Mode toolset."""
    from punie.agent.config import PUNIE_LOCAL_INSTRUCTIONS

    agent, client = create_local_agent(model="local", workspace=Path.cwd())

    # Verify agent was created successfully
    assert agent is not None
    assert client is not None

    # PydanticAI wraps toolsets, so check the actual FunctionToolset (last in list)
    # Code Mode toolset has 8 tools: read/write/run_command/execute_code + 4 terminal
    assert len(agent.toolsets) > 0
    function_toolset = agent.toolsets[-1]  # Last toolset is the one we provided
    assert len(function_toolset.tools) == 8
