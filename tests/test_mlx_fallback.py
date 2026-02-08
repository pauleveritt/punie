"""Tests for graceful MLX model fallback when mlx-lm is not installed."""

import builtins

import pytest

from punie.agent import PunieAgent
from punie.testing import FakeClient


@pytest.mark.asyncio
async def test_local_model_missing_mlx_lm_graceful_fallback(monkeypatch):
    """When model='local' but mlx-lm isn't installed, should fall back to test model."""
    # Mock mlx_lm import to simulate it not being installed
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "mlx_lm.utils" or name.startswith("mlx_lm"):
            raise ImportError(f"No module named '{name}'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    # Create agent with local model (will fail to load MLX)
    agent = PunieAgent(model="local", name="test-agent")
    fake = FakeClient()
    agent.on_connect(fake)

    # Initialize and create session - should not raise, should fall back gracefully
    await agent.initialize(protocol_version=1)
    response = await agent.new_session(cwd="/test", mcp_servers=[])

    # Should get a valid session
    assert response.session_id.startswith("punie-session-")

    # No messages sent during new_session (they're sent during first prompt)
    assert len(fake.notifications) == 0

    # Agent should still work with fallback test model
    session_id = response.session_id
    from punie.acp.schema import TextContentBlock

    prompt_response = await agent.prompt(
        prompt=[TextContentBlock(type="text", text="Hello")],
        session_id=session_id,
    )
    assert prompt_response.stop_reason == "end_turn"

    # Now messages should be sent (error + greeting + response)
    assert len(fake.notifications) >= 2

    # First message should be mlx-lm error
    error_notification = fake.notifications[0]
    error_text = str(error_notification).lower()
    assert "mlx-lm" in error_text
    assert "local model support not available" in error_text

    # Second message should be greeting
    greeting_notification = fake.notifications[1]
    greeting_text = str(greeting_notification).lower()
    assert "punie agent connected" in greeting_text


@pytest.mark.asyncio
async def test_local_model_with_suffix_missing_mlx_lm(monkeypatch):
    """When model='local:model-name' but mlx-lm isn't installed, should fall back."""
    # Mock mlx_lm import to simulate it not being installed
    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "mlx_lm.utils" or name.startswith("mlx_lm"):
            raise ImportError(f"No module named '{name}'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mock_import)

    agent = PunieAgent(model="local:mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")
    fake = FakeClient()
    agent.on_connect(fake)

    await agent.initialize(protocol_version=1)
    response = await agent.new_session(cwd="/test", mcp_servers=[])

    # Should succeed with fallback (messages sent during first prompt, not here)
    assert response.session_id.startswith("punie-session-")
    assert len(fake.notifications) == 0
