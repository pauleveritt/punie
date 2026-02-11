"""Example 15: Local Model Server (LM Studio / mlx-lm.server)

This example demonstrates connecting to a local model server using LM Studio
or mlx-lm.server. Both expose OpenAI-compatible APIs, allowing Punie to use
Pydantic AI's built-in OpenAIChatModel.

Prerequisites:
    1. Start LM Studio (https://lmstudio.ai/) OR
    2. Run mlx-lm.server:
       $ uv pip install mlx-lm
       $ mlx-lm.server --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit

Run:
    $ uv run python examples/15_local_model_server.py
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from punie.agent.factory import (
    DEFAULT_LOCAL_BASE_URL,
    DEFAULT_LOCAL_MODEL,
    _parse_local_spec,
    create_local_agent,
)


def demo_parsing() -> None:
    """Demonstrate local model spec parsing."""
    print("=" * 80)
    print("Local Model Spec Parsing Examples")
    print("=" * 80)
    print()

    examples = [
        ("", "Default LM Studio configuration"),
        ("my-model", "LM Studio with specific model name"),
        ("http://localhost:8080/v1/qwen", "mlx-lm.server (default port 8080)"),
        ("http://127.0.0.1:1234/v1/custom", "Custom localhost configuration"),
    ]

    for spec, description in examples:
        parsed = _parse_local_spec(spec)
        print(f"Input:  '{spec}'")
        print(f"  → {description}")
        print(f"  → base_url:   {parsed.base_url}")
        print(f"  → model_name: {parsed.model_name}")
        print()

    print("Constants:")
    print(f"  DEFAULT_LOCAL_BASE_URL: {DEFAULT_LOCAL_BASE_URL}")
    print(f"  DEFAULT_LOCAL_MODEL:    {DEFAULT_LOCAL_MODEL}")
    print()


async def demo_agent() -> None:
    """Demonstrate creating and using a local model agent."""
    print("=" * 80)
    print("Local Model Agent Example")
    print("=" * 80)
    print()

    # Create agent with default LM Studio configuration
    # This assumes LM Studio is running at http://localhost:1234
    agent, client = create_local_agent(
        model="local",  # Uses default LM Studio URL + "default" model
        workspace=Path.cwd(),
    )

    print("Created agent with:")
    print("  Model:     local (LM Studio default)")
    print(f"  Workspace: {Path.cwd()}")
    print()

    # Simple prompt to test the connection
    prompt = "List all Python files in this directory (just filenames, no paths)"

    print(f"Prompt: {prompt}")
    print()
    print("Response:")
    print("-" * 80)

    try:
        from punie.acp.contrib.tool_calls import ToolCallTracker
        from punie.agent.deps import ACPDeps

        # Create dependencies for the agent
        tracker = ToolCallTracker()
        session_id = f"example-15-{datetime.now(timezone.utc).isoformat()}"
        deps = ACPDeps(client_conn=client, session_id=session_id, tracker=tracker)

        # Run the agent
        result = await agent.run(prompt, deps=deps)

        print(result.output)
        print("-" * 80)
        print()
        print(f"Tool calls made: {len(tracker._calls)}")
        for call_id, call_info in tracker._calls.items():
            print(f"  - {call_info.name}")

    except Exception as e:
        print(f"Error: {e}")
        print()
        print("Make sure LM Studio is running with a model loaded:")
        print("  1. Download LM Studio from https://lmstudio.ai/")
        print("  2. Load a model in the UI")
        print("  3. Start the server (default: http://localhost:1234)")
        print()
        print("Or use mlx-lm.server:")
        print("  $ uv pip install mlx-lm")
        print("  $ mlx-lm.server --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")
        print("  Then update model spec to: local:http://localhost:8080/v1/default")


def demo_model_formats() -> None:
    """Show different ways to specify local models."""
    print("=" * 80)
    print("Model Specification Formats")
    print("=" * 80)
    print()

    formats = [
        ("local", "Use LM Studio defaults (http://localhost:1234/v1 + 'default')"),
        ("local:", "Same as 'local' (trailing colon is optional)"),
        (
            "local:my-model",
            "Use LM Studio with specific model name loaded in UI",
        ),
        (
            "local:http://localhost:8080/v1/qwen",
            "Use mlx-lm.server (custom host/port/model)",
        ),
    ]

    print("In CLI:")
    for spec, description in formats:
        print(f"  $ punie serve --model {spec}")
        print(f"    → {description}")
        print()

    print()
    print("In code:")
    print(
        """
    from punie.agent.factory import create_local_agent

    # Default LM Studio
    agent, client = create_local_agent(model='local')

    # LM Studio with specific model
    agent, client = create_local_agent(model='local:my-model')

    # mlx-lm.server
    agent, client = create_local_agent(model='local:http://localhost:8080/v1/qwen')
    """
    )


if __name__ == "__main__":
    print()
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 15 + "Local Model Server Example" + " " * 36 + "║")
    print("║" + " " * 20 + "(LM Studio / mlx-lm.server)" + " " * 30 + "║")
    print("╚" + "=" * 78 + "╝")
    print()

    # Show parsing examples
    demo_parsing()

    # Show model format options
    demo_model_formats()

    # Run live agent example (requires server running)
    print("=" * 80)
    print("Live Agent Test")
    print("=" * 80)
    print()
    print("This will attempt to connect to LM Studio...")
    print()
    asyncio.run(demo_agent())

    print()
    print("=" * 80)
    print("Example Complete")
    print("=" * 80)
    print()
