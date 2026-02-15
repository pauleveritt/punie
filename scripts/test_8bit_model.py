#!/usr/bin/env python3
"""Quick test of 8-bit model for tool-calling behavior."""

import asyncio
from pathlib import Path

from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.agent.config import AgentConfig
from punie.agent.deps import ACPDeps
from punie.agent.factory import create_pydantic_agent, create_server_model
from punie.local import LocalClient
from punie.training.server import ServerProcess
from punie.training.server_config import QWEN_STOP_SEQUENCES, ServerConfig
from punie.training.tool_call_parser import parse_tool_calls


async def test_8bit():
    """Test 8-bit model tool-calling behavior."""
    print("Testing fused_model_qwen3_phase8_8bit...")

    # Create server config
    server_config = ServerConfig(
        model_path="fused_model_qwen3_phase8_8bit",
        port=8080,
        stop_sequences=QWEN_STOP_SEQUENCES,
    )

    # Start server
    print("Starting server...")
    async with ServerProcess(config=server_config) as server:
        print(f"✓ Server ready at {server.config.base_url}")

        # Create agent
        model = create_server_model(server_config)
        agent_config = AgentConfig(
            temperature=0.0,
            stop_sequences=QWEN_STOP_SEQUENCES,
        )
        agent = create_pydantic_agent(model=model, config=agent_config)
        client = LocalClient(workspace=Path.cwd())

        # Test query that should trigger tool usage
        query = "Find all Django view functions"
        print(f"\nQuery: {query}")
        print("Expected: tool call (run_command)")

        tracker = ToolCallTracker()
        deps = ACPDeps(
            client_conn=client,
            session_id="test-8bit",
            tracker=tracker,
        )

        result = await agent.run(query, deps=deps)

        # Check for tool calls
        tool_calls_list = []
        if result.all_messages():
            for msg in result.all_messages():
                if hasattr(msg, "parts"):
                    for part in msg.parts:
                        if hasattr(part, "tool_name"):
                            tool_calls_list.append(part.tool_name)
        if not tool_calls_list:
            _, parsed_calls = parse_tool_calls(result.output)
            tool_calls_list = [call["name"] for call in parsed_calls if "name" in call]

        print(f"Tool calls made: {tool_calls_list if tool_calls_list else 'NONE'}")
        print(f"Response preview: {result.output[:200]}")

        if tool_calls_list:
            print("\n✅ 8-bit model DOES call tools!")
            return True
        else:
            print("\n❌ 8-bit model DOES NOT call tools")
            return False


if __name__ == "__main__":
    success = asyncio.run(test_8bit())
    raise SystemExit(0 if success else 1)
