#!/usr/bin/env python3
"""Quick test to determine what tool calling format the 1.5B model uses."""

import asyncio
from pathlib import Path

from punie.agent.factory import create_pydantic_agent, create_server_model
from punie.agent.config import AgentConfig
from punie.agent.deps import ACPDeps
from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.training.server_config import ServerConfig
from punie.training.server import ServerProcess
from punie.local import LocalClient
from punie.training.tool_call_parser import parse_tool_calls


async def main():
    """Test 1.5B model tool calling format."""
    print("Testing Qwen2.5-Coder-1.5B-Instruct-4bit tool calling format")
    print("=" * 80)

    model_path = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"
    workspace = Path.cwd()

    server_config = ServerConfig(
        model_path=model_path,
        adapter_path=None,
        port=8766,
    )

    # Start server
    print("\nStarting MLX server...")
    server = ServerProcess(config=server_config)
    await server.start()

    try:
        # Create agent
        print("Creating agent...")
        model = create_server_model(server_config)
        agent_config = AgentConfig(temperature=0.0)
        agent = create_pydantic_agent(model=model, config=agent_config)

        client = LocalClient(workspace=workspace)
        tracker = ToolCallTracker()
        deps = ACPDeps(
            client_conn=client,
            session_id="1.5b-format-test",
            tracker=tracker,
        )

        # Test prompt
        prompt = "Read the file at src/punie/__init__.py"
        print(f"\nPrompt: {prompt}")
        print("\nRunning agent...")

        result = await agent.run(prompt, deps=deps)

        print(f"\n{'=' * 80}")
        print("RAW MODEL OUTPUT:")
        print(f"{'=' * 80}")
        print(result.output)
        print(f"{'=' * 80}\n")

        # Check Method 1: Structured parts
        print("Method 1: Structured parts (PydanticAI protocol)")
        structured_calls = []
        if result.all_messages():
            for msg in result.all_messages():
                if hasattr(msg, "parts"):
                    for part in msg.parts:
                        if hasattr(part, "tool_name"):
                            structured_calls.append(part.tool_name)
        print(f"  Found: {structured_calls}")

        # Check Method 2: Text parsing
        print("\nMethod 2: Text parsing (XML/JSON extraction)")
        _, parsed_calls = parse_tool_calls(result.output)
        parsed_call_names = [call["name"] for call in parsed_calls if "name" in call]
        print(f"  Found: {parsed_call_names}")
        if parsed_calls:
            print(f"  Raw data: {parsed_calls}")

        # Conclusion
        print("\n" + "=" * 80)
        print("CONCLUSION:")
        print("=" * 80)
        if structured_calls:
            print("✓ 1.5B model uses PydanticAI structured calls (like 30B)")
            print("  Text parser fallback not needed for this model")
        elif parsed_call_names:
            print("✓ 1.5B model outputs XML/JSON text requiring parser")
            print("  Text parser fallback IS needed for this model")
        else:
            print("✗ No tool calls detected by either method")
            print("  Model may not be tool-calling capable or prompt failed")

    finally:
        print("\nStopping server...")
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
