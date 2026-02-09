"""Tests for ACP agent performance reporting via PUNIE_PERF env var.

NOTE: Performance reporting in ACP mode is temporarily disabled due to
collector lifecycle issues when reusing agents across prompts.
These tests are marked as xfail until the issue is resolved.
"""

from pathlib import Path

import pytest

from punie.acp.schema import TextContentBlock
from punie.agent import PunieAgent
from punie.testing.fakes import FakeClient

pytestmark = pytest.mark.xfail(
    reason="ACP performance reporting temporarily disabled due to collector lifecycle issues"
)


@pytest.mark.asyncio
async def test_acp_agent_with_perf_env_var(tmp_path, monkeypatch):
    """Test that PUNIE_PERF=1 enables performance reporting in ACP mode."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Set PUNIE_PERF=1 environment variable
    monkeypatch.setenv("PUNIE_PERF", "1")

    # Create agent after setting env var (so it picks it up)
    agent = PunieAgent(model="test", name="test-agent")
    client = FakeClient()

    # Connect and initialize
    agent.on_connect(client)
    await agent.initialize(protocol_version=1)

    # Create session
    session_resp = await agent.new_session(cwd=str(tmp_path), mcp_servers=[])
    session_id = session_resp.session_id

    # Send a prompt
    prompt_blocks = [TextContentBlock(type="text", text="What is 2+2?")]
    await agent.prompt(prompt=prompt_blocks, session_id=session_id)

    # Check that HTML file was created
    html_files = list(tmp_path.glob("punie-perf-*.html"))
    assert len(html_files) == 1, "Performance report HTML should be generated"

    # Verify HTML content
    html_content = html_files[0].read_text()
    assert "<!DOCTYPE html>" in html_content
    assert "Punie Performance Report" in html_content
    assert "test" in html_content  # Model name


@pytest.mark.asyncio
async def test_acp_agent_without_perf_env_var(tmp_path, monkeypatch):
    """Test that without PUNIE_PERF=1, no report is generated."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Ensure env var is not set
    monkeypatch.delenv("PUNIE_PERF", raising=False)

    # Create agent
    agent = PunieAgent(model="test", name="test-agent")
    client = FakeClient()

    # Connect and initialize
    agent.on_connect(client)
    await agent.initialize(protocol_version=1)

    # Create session
    session_resp = await agent.new_session(cwd=str(tmp_path), mcp_servers=[])
    session_id = session_resp.session_id

    # Send a prompt
    prompt_blocks = [TextContentBlock(type="text", text="What is 2+2?")]
    await agent.prompt(prompt=prompt_blocks, session_id=session_id)

    # Check that no HTML file was created
    html_files = list(tmp_path.glob("punie-perf-*.html"))
    assert len(html_files) == 0, "No performance report should be generated without PUNIE_PERF"


@pytest.mark.asyncio
async def test_acp_agent_perf_with_zero_disables(tmp_path, monkeypatch):
    """Test that PUNIE_PERF=0 disables performance reporting."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)

    # Set PUNIE_PERF=0 (explicitly disabled)
    monkeypatch.setenv("PUNIE_PERF", "0")

    # Create agent
    agent = PunieAgent(model="test", name="test-agent")
    client = FakeClient()

    # Connect and initialize
    agent.on_connect(client)
    await agent.initialize(protocol_version=1)

    # Create session
    session_resp = await agent.new_session(cwd=str(tmp_path), mcp_servers=[])
    session_id = session_resp.session_id

    # Send a prompt
    prompt_blocks = [TextContentBlock(type="text", text="What is 2+2?")]
    await agent.prompt(prompt=prompt_blocks, session_id=session_id)

    # Check that no HTML file was created
    html_files = list(tmp_path.glob("punie-perf-*.html"))
    assert len(html_files) == 0, "PUNIE_PERF=0 should disable reporting"
