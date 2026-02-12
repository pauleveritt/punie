#!/usr/bin/env python3
"""Test if explicit tool instructions help 1.5B model."""

import asyncio
import time
from pathlib import Path

from punie.agent.factory import create_pydantic_agent, create_server_model
from punie.agent.config import AgentConfig
from punie.agent.deps import ACPDeps
from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.training.server_config import ServerConfig
from punie.training.server import ServerProcess
from punie.local import LocalClient


async def test_with_explicit_instructions():
    """Test 1.5B with explicit tool usage instructions."""
    print("=" * 80)
    print("TEST 1: 1.5B Model with EXPLICIT Tool Instructions")
    print("=" * 80)

    model_path = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    workspace = Path.cwd()

    server_config = ServerConfig(
        model_path=model_path,
        adapter_path=None,
        port=8766,
    )

    print("\nStarting server...")
    server = ServerProcess(config=server_config)
    await server.start()

    try:
        model = create_server_model(server_config)
        agent_config = AgentConfig(temperature=0.0)
        agent = create_pydantic_agent(model=model, config=agent_config)

        client = LocalClient(workspace=workspace)

        # Warmup
        print("Warming up...")
        warmup_tracker = ToolCallTracker()
        warmup_deps = ACPDeps(client_conn=client, session_id="warmup", tracker=warmup_tracker)
        await agent.run("What is 2+2?", deps=warmup_deps)

        # Test with explicit instructions
        tracker = ToolCallTracker()
        deps = ACPDeps(client_conn=client, session_id="explicit-test", tracker=tracker)

        question = """Search the codebase to find which classes subclass from Protocol.

Use the run_command tool with grep to search for class definitions that inherit from Protocol.
Search for the pattern 'class' followed by 'Protocol' in Python files."""

        print(f"\nQuestion (explicit instructions):")
        print(question)
        print("\nRunning agent...\n")

        start = time.perf_counter()
        result = await agent.run(question, deps=deps)
        elapsed = time.perf_counter() - start

        # Collect tool calls
        tool_calls = []
        if result.all_messages():
            for msg in result.all_messages():
                if hasattr(msg, "parts"):
                    for part in msg.parts:
                        if hasattr(part, "tool_name"):
                            tool_calls.append({
                                "tool": part.tool_name,
                                "args": getattr(part, "args", {})
                            })

        print("=" * 80)
        print("RESPONSE:")
        print("=" * 80)
        print(result.output)
        print("=" * 80)
        print(f"\nTime: {elapsed:.2f}s")
        print(f"Tool calls: {len(tool_calls)}")
        for i, call in enumerate(tool_calls, 1):
            print(f"  {i}. {call['tool']}")
            if 'command' in call['args']:
                print(f"     command: {call['args']['command']}")

        return len(tool_calls) > 0, tool_calls

    finally:
        await server.stop()


async def test_with_system_prompt():
    """Test 1.5B with enhanced system prompt."""
    print("\n" + "=" * 80)
    print("TEST 2: 1.5B Model with ENHANCED System Prompt")
    print("=" * 80)

    model_path = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    workspace = Path.cwd()

    server_config = ServerConfig(
        model_path=model_path,
        adapter_path=None,
        port=8766,
    )

    print("\nStarting server...")
    server = ServerProcess(config=server_config)
    await server.start()

    try:
        model = create_server_model(server_config)

        # Enhanced system prompt
        system_prompt = """You are a coding assistant with access to tools for exploring codebases.

CRITICAL RULES:
1. ALWAYS use tools to search the codebase before answering code questions
2. NEVER guess or answer from memory - always verify with actual code
3. Use run_command with grep to search for code patterns
4. Use read_file to inspect specific files
5. Only provide answers after you've searched the codebase

When asked about code, your workflow should be:
1. Use run_command to search for relevant files/patterns
2. Read files if needed to verify
3. Then provide your answer based on what you found"""

        agent_config = AgentConfig(temperature=0.0, system_prompt=system_prompt)
        agent = create_pydantic_agent(model=model, config=agent_config)

        client = LocalClient(workspace=workspace)
        tracker = ToolCallTracker()
        deps = ACPDeps(client_conn=client, session_id="system-prompt-test", tracker=tracker)

        question = "Which classes in this codebase subclass from Protocol?"

        print(f"\nSystem prompt: {system_prompt[:100]}...")
        print(f"\nQuestion (simple):")
        print(question)
        print("\nRunning agent...\n")

        start = time.perf_counter()
        result = await agent.run(question, deps=deps)
        elapsed = time.perf_counter() - start

        # Collect tool calls
        tool_calls = []
        if result.all_messages():
            for msg in result.all_messages():
                if hasattr(msg, "parts"):
                    for part in msg.parts:
                        if hasattr(part, "tool_name"):
                            tool_calls.append({
                                "tool": part.tool_name,
                                "args": getattr(part, "args", {})
                            })

        print("=" * 80)
        print("RESPONSE:")
        print("=" * 80)
        print(result.output)
        print("=" * 80)
        print(f"\nTime: {elapsed:.2f}s")
        print(f"Tool calls: {len(tool_calls)}")
        for i, call in enumerate(tool_calls, 1):
            print(f"  {i}. {call['tool']}")
            if 'command' in call['args']:
                print(f"     command: {call['args']['command']}")

        return len(tool_calls) > 0, tool_calls

    finally:
        await server.stop()


async def main():
    """Run both prompting tests."""
    print("Testing if better prompting helps 1.5B model use tools autonomously\n")

    success1, calls1 = await test_with_explicit_instructions()
    success2, calls2 = await test_with_system_prompt()

    print("\n" + "=" * 80)
    print("PROMPTING TEST RESULTS")
    print("=" * 80)
    print(f"Test 1 (Explicit instructions): {'✅ USED TOOLS' if success1 else '❌ NO TOOLS'} ({len(calls1)} calls)")
    print(f"Test 2 (System prompt): {'✅ USED TOOLS' if success2 else '❌ NO TOOLS'} ({len(calls2)} calls)")

    if success1 or success2:
        print("\n✅ CONCLUSION: Prompting CAN fix the issue!")
        print("   The model has tool-calling capability but needs explicit guidance.")
    else:
        print("\n❌ CONCLUSION: Prompting does NOT fix the issue.")
        print("   This is a fundamental model limitation, not a prompting problem.")


if __name__ == "__main__":
    asyncio.run(main())
