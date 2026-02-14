#!/usr/bin/env python3
"""Deep test of tool calling pipeline to verify parser and eval integration.

This script systematically tests each component that led to the overnight
evaluation failure, ensuring the fixes work correctly.
"""

import asyncio
from pathlib import Path

from punie.training.tool_call_parser import parse_tool_calls


def test_parser_standalone():
    """Test 1: Verify parser handles known XML and JSON formats."""
    print("\n" + "=" * 80)
    print("TEST 1: Parser Standalone - Known Inputs")
    print("=" * 80)

    # Test case 1: Qwen XML format with <tool_call> tags
    xml_input = """I'll help you read that file.

<tool_call>
{"name": "read_file", "arguments": {"path": "main.py"}}
</tool_call>"""

    clean_text, calls = parse_tool_calls(xml_input)
    print(f"\nInput (XML format):\n{xml_input}")
    print(f"\nExtracted calls: {calls}")
    print(f"Clean text: {clean_text}")

    assert len(calls) == 1, f"Expected 1 call, got {len(calls)}"
    assert calls[0]["name"] == "read_file", f"Expected read_file, got {calls[0].get('name')}"
    assert calls[0]["arguments"]["path"] == "main.py"
    print("✓ PASS: XML format with <tool_call> tags")

    # Test case 2: Multiple tool calls
    multi_input = """<tool_call>
{"name": "read_file", "arguments": {"path": "test.py"}}
</tool_call>

After reading, I'll run the tests.

<tool_call>
{"name": "run_command", "arguments": {"command": "pytest"}}
</tool_call>"""

    clean_text, calls = parse_tool_calls(multi_input)
    print(f"\n\nInput (multiple calls):\n{multi_input}")
    print(f"\nExtracted calls: {calls}")

    assert len(calls) == 2, f"Expected 2 calls, got {len(calls)}"
    assert calls[0]["name"] == "read_file"
    assert calls[1]["name"] == "run_command"
    print("✓ PASS: Multiple tool calls")

    # Test case 3: No tool calls (plain text)
    plain_input = "This is just a regular response with no tool calls."
    clean_text, calls = parse_tool_calls(plain_input)
    print(f"\n\nInput (plain text):\n{plain_input}")
    print(f"\nExtracted calls: {calls}")

    assert len(calls) == 0, f"Expected 0 calls, got {len(calls)}"
    print("✓ PASS: Plain text with no tool calls")

    print("\n✅ All parser standalone tests passed!\n")


async def test_single_eval_prompt():
    """Test 2: Run a single eval prompt end-to-end and inspect the result."""
    print("\n" + "=" * 80)
    print("TEST 2: Single Eval Prompt - End-to-End")
    print("=" * 80)

    from punie.agent.factory import create_pydantic_agent, create_server_model
    from punie.agent.config import AgentConfig
    from punie.agent.deps import ACPDeps
    from punie.acp.contrib.tool_calls import ToolCallTracker
    from punie.training.eval_prompts import EvalPrompt
    from punie.training.server_config import ServerConfig
    from punie.training.server import ServerProcess
    from punie.local import LocalClient

    # Create a simple tool-calling eval prompt
    prompt = EvalPrompt(
        id="test_read_file",
        category="tool-calling",
        prompt_text="Read the file at src/punie/__init__.py",
        expected_tool_calls=("read_file",),
        expected_keywords=(),
    )

    print(f"\nPrompt: {prompt.prompt_text}")
    print(f"Expected tool calls: {prompt.expected_tool_calls}")

    # Create server config
    model_path = "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
    workspace = Path.cwd()

    print(f"\nModel: {model_path}")
    print(f"Workspace: {workspace}")

    server_config = ServerConfig(
        model_path=model_path,
        adapter_path=None,
        port=8765,
    )

    # Start server
    print("\nStarting MLX server...")
    server = ServerProcess(config=server_config)
    await server.start()

    try:
        # Create agent with server model
        print("Creating agent...")
        model = create_server_model(server_config)
        agent_config = AgentConfig(temperature=0.0)
        agent = create_pydantic_agent(model=model, config=agent_config)

        # Create local client
        client = LocalClient(workspace=workspace)
        tracker = ToolCallTracker()
        deps = ACPDeps(
            client_conn=client,
            session_id="deep-test-session",
            tracker=tracker,
        )

        print("Running agent with prompt...")
        result = await agent.run(prompt.prompt_text, deps=deps)

        print(f"\n{'=' * 80}")
        print("RAW MODEL OUTPUT:")
        print(f"{'=' * 80}")
        print(result.output)
        print(f"{'=' * 80}\n")

        # Extract tool calls using both methods
        print("Method 1: Structured parts (cloud models)")
        structured_calls = []
        if result.all_messages():
            for msg in result.all_messages():
                if hasattr(msg, "parts"):
                    for part in msg.parts:
                        if hasattr(part, "tool_name"):
                            structured_calls.append(part.tool_name)
        print(f"  Structured calls: {structured_calls}")

        print("\nMethod 2: Text parsing (local models - OUR FIX)")
        _, parsed_calls = parse_tool_calls(result.output)
        parsed_call_names = [call["name"] for call in parsed_calls if "name" in call]
        print(f"  Parsed calls: {parsed_call_names}")
        print(f"  Raw parsed data: {parsed_calls}")

        # Verify we got the expected tool call
        all_calls = structured_calls or parsed_call_names
        print(f"\nFinal tool calls detected: {all_calls}")

        success = "read_file" in all_calls
        if success:
            print("✅ SUCCESS: read_file tool call detected!")
        else:
            print("❌ FAILURE: Expected read_file tool call not found")
            print("   This suggests the model didn't call the tool or parser failed")

        return success

    finally:
        # Stop server
        print("\nStopping MLX server...")
        await server.stop()


async def test_eval_runner_integration():
    """Test 3: Verify eval_runner.py correctly uses the parser fallback."""
    print("\n" + "=" * 80)
    print("TEST 3: Eval Runner Integration")
    print("=" * 80)

    from punie.training.eval_runner import run_evaluation, EvalRunConfig
    from punie.training.eval_prompts import EvalSuite, EvalPrompt
    from punie.training.server_config import ServerConfig

    # Create a minimal eval suite with 2 prompts
    suite = EvalSuite(
        name="minimal-test",
        prompts=(
            EvalPrompt(
                id="test_read",
                category="tool-calling",
                prompt_text="Read the file at src/punie/__init__.py",
                expected_tool_calls=("read_file",),
                expected_keywords=(),
            ),
            EvalPrompt(
                id="test_list",
                category="tool-calling",
                prompt_text="List all Python files in the src directory",
                expected_tool_calls=("run_command",),
                expected_keywords=("find", ".py"),
            ),
        ),
    )

    model = "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
    workspace = Path.cwd()

    server_config = ServerConfig(
        model_path=model,
        adapter_path=None,
        port=8765,
    )

    config = EvalRunConfig(
        suite=suite,
        server_config=server_config,
        workspace=workspace,
        manage_server=True,
    )

    print(f"\nRunning minimal eval with {len(suite.prompts)} prompts...")
    print(f"Suite: {suite.name}")
    for p in suite.prompts:
        print(f"  - {p.id}: expects {p.expected_tool_calls}")

    report = await run_evaluation(config)

    print(f"\n{'=' * 80}")
    print("EVAL RESULTS:")
    print(f"{'=' * 80}")
    print(f"Model: {report.model_name}")
    print(f"Total prompts: {len(report.results)}")
    print(f"Overall score: {report.overall_score:.2f}")
    print(f"Success rate: {report.success_rate * 100:.1f}%")

    print("\nPer-prompt breakdown:")
    for result in report.results:
        status = "✓" if result.success else "✗"
        print(f"  {status} {result.prompt_id}: score={result.score:.2f}, tools={result.tool_calls_made}")

    # Verify we got non-zero scores (proves parser is working)
    if report.overall_score > 0:
        print("\n✅ SUCCESS: Got non-zero scores (parser is working!)")
        return True
    else:
        print("\n❌ FAILURE: All scores are 0.0 (parser may not be working)")
        return False


async def main():
    """Run all deep tests in sequence."""
    print("\n" + "=" * 80)
    print("DEEP TEST: Tool Calling Pipeline Verification")
    print("=" * 80)
    print("\nThis test suite recreates the paths that led to the overnight")
    print("evaluation failure and verifies each component of the fix.")

    try:
        # Test 1: Parser standalone
        test_parser_standalone()

        # Test 2: Single eval prompt
        print("\nProceeding to Test 2 (this will start the MLX server)...")
        success = await test_single_eval_prompt()
        if not success:
            print("\n❌ Test 2 failed. Stopping here.")
            return

        # Test 3: Eval runner integration
        print("\n\nProceeding to Test 3 (this will run a minimal eval)...")
        success = await test_eval_runner_integration()
        if not success:
            print("\n❌ Test 3 failed.")
            return

        print("\n" + "=" * 80)
        print("✅ ALL DEEP TESTS PASSED!")
        print("=" * 80)
        print("\nThe tool calling pipeline is working correctly:")
        print("  ✓ Parser extracts tool calls from XML/JSON formats")
        print("  ✓ Agent produces tool calls that parser recognizes")
        print("  ✓ Eval runner uses parser fallback correctly")
        print("  ✓ Scores are non-zero for tool-capable models")
        print("\nYou can now trust the evaluation reports.")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
