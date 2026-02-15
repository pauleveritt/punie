#!/usr/bin/env python3
"""Test server pipeline end-to-end - the critical missing test.

This validates that tool calls flow correctly through:
  Model → <tool_call> token → mlx_lm.server parser → OpenAI API format → PydanticAI

Phase 20 only tested direct mlx_lm.generate() which bypassed the server entirely.
This test ensures the server's XML parser correctly extracts tool_calls from the model output.
"""

import subprocess
import sys
import time
from pathlib import Path

import httpx

# Model to test (should be the newly trained XML-format model)
MODEL_PATH = "fused_model_qwen3_phase21_xml_5bit"

# Test queries - 5-query discrimination test
TEST_CASES = [
    {
        "query": "Find all Django view classes in the data/repos directory",
        "expected": "tool_call",
        "description": "Search query → should call run_command/grep",
    },
    {
        "query": "Show me the UserSerializer class implementation",
        "expected": "tool_call",
        "description": "Read file query → should call read_file",
    },
    {
        "query": "What is dependency injection and when should I use it?",
        "expected": "direct",
        "description": "Concept question → should answer directly",
    },
    {
        "query": "Find all files that use async/await in the codebase",
        "expected": "tool_call",
        "description": "Search query → should call run_command/grep",
    },
    {
        "query": "What's the difference between ORM and raw SQL?",
        "expected": "direct",
        "description": "Comparison question → should answer directly",
    },
]


def start_server(model_path: str, port: int = 8080) -> subprocess.Popen:
    """Start mlx_lm.server as a subprocess.

    Args:
        model_path: Path to the fused model
        port: Port to run server on

    Returns:
        subprocess.Popen object for the server process
    """
    print(f"Starting mlx_lm.server with model: {model_path}")

    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "mlx_lm.server",
        "--model",
        model_path,
        "--port",
        str(port),
    ]

    # Start server in background
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for server to start (check models endpoint instead of /health)
    print("Waiting for server to start...")
    for i in range(30):  # 30 second timeout
        try:
            response = httpx.get(f"http://localhost:{port}/v1/models", timeout=1.0)
            if response.status_code == 200:
                print(f"✓ Server started successfully (took {i + 1}s)")
                return process
        except (httpx.ConnectError, httpx.TimeoutException):
            time.sleep(1)

    # Server didn't start
    process.kill()
    raise RuntimeError("Server failed to start within 30 seconds")


def test_query(client: httpx.Client, query: str, expected: str) -> dict:
    """Test a single query through the server pipeline.

    Args:
        client: HTTP client
        query: User query
        expected: Expected behavior ("tool_call" or "direct")

    Returns:
        Dict with test results
    """
    # Define tools (same as PydanticAI would send)
    tools = [
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Execute a shell command",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "Command to execute"}
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file's contents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "Path to file"}
                    },
                    "required": ["path"],
                },
            },
        },
    ]

    # Send request via OpenAI-compatible API
    request = {
        "model": MODEL_PATH,  # Specify which model to use
        "messages": [
            {
                "role": "system",
                "content": "You are Punie, an AI coding assistant that helps with Python development via PyCharm.",
            },
            {"role": "user", "content": query},
        ],
        "tools": tools,
        "temperature": 0.0,  # Deterministic
    }

    try:
        response = client.post("/v1/chat/completions", json=request, timeout=60.0)
        response.raise_for_status()
        result = response.json()

        # Extract assistant message
        choice = result["choices"][0]
        message = choice["message"]

        # Check if tool_calls exist in response
        has_tool_calls = "tool_calls" in message and len(message["tool_calls"]) > 0

        # Determine actual behavior
        actual = "tool_call" if has_tool_calls else "direct"

        # Check if correct
        correct = actual == expected

        return {
            "query": query,
            "expected": expected,
            "actual": actual,
            "correct": correct,
            "message": message,
        }

    except Exception as e:
        return {
            "query": query,
            "expected": expected,
            "actual": "error",
            "correct": False,
            "error": str(e),
        }


def main():
    # Check model exists
    model_path = Path(MODEL_PATH)
    if not model_path.exists():
        print(f"❌ Model not found: {MODEL_PATH}")
        print("\nPlease train the model first:")
        print("  ./scripts/train_phase21_xml.sh")
        sys.exit(1)

    print("=" * 80)
    print("SERVER PIPELINE TEST - Phase 21 Validation")
    print("=" * 80)
    print("")
    print("This test validates the full pipeline:")
    print("  Model → <tool_call> token → mlx_lm.server parser →")
    print("  OpenAI API response → tool_calls field")
    print("")

    # Start server
    server_port = 8080
    server_process = None

    try:
        server_process = start_server(MODEL_PATH, server_port)

        # Create HTTP client
        client = httpx.Client(base_url=f"http://localhost:{server_port}")

        # Run tests
        print("\n" + "=" * 80)
        print("RUNNING 5-QUERY DISCRIMINATION TEST")
        print("=" * 80)

        results = []
        for i, test_case in enumerate(TEST_CASES, 1):
            print(f"\nTest {i}/5: {test_case['description']}")
            print(f"  Query: {test_case['query']}")
            print(f"  Expected: {test_case['expected']}")

            result = test_query(client, test_case["query"], test_case["expected"])
            results.append(result)

            print(f"  Actual: {result['actual']}")
            print("  ✅ PASS" if result["correct"] else "  ❌ FAIL")

            # Print error details if test errored
            if result["actual"] == "error":
                print(f"  Error: {result.get('error', 'Unknown error')}")

            # Print tool calls if present
            if result["actual"] == "tool_call":
                message = result["message"]
                for tool_call in message.get("tool_calls", []):
                    func = tool_call["function"]
                    print(f"    → Tool: {func['name']}")

        # Summary
        print("\n" + "=" * 80)
        print("TEST RESULTS")
        print("=" * 80)

        correct_count = sum(1 for r in results if r["correct"])
        total_count = len(results)
        accuracy = correct_count / total_count * 100

        print(f"\nAccuracy: {correct_count}/{total_count} ({accuracy:.0f}%)")
        print("")

        for i, result in enumerate(results, 1):
            status = "✅" if result["correct"] else "❌"
            print(f"{status} Test {i}: {result['expected']} → {result['actual']}")

        # Check for success
        print("\n" + "=" * 80)
        if accuracy == 100:
            print("✅ SUCCESS: All tests passed!")
            print("=" * 80)
            print("\nThe model correctly:")
            print("  1. Generates <tool_call> XML tokens")
            print("  2. Server parses XML to structured tool_calls")
            print("  3. API response includes tool_calls field")
            print("  4. Discriminates between tool vs direct queries")
            print("\nPhase 21 tool-calling format fix is working! 🎉")
            sys.exit(0)
        else:
            print("❌ FAILURE: Some tests failed")
            print("=" * 80)
            print("\nThe model may still have issues:")
            print("  - Not generating <tool_call> tokens")
            print("  - Server not parsing XML correctly")
            print("  - Poor discrimination between tool vs direct")
            print("\nCheck training data and model convergence.")
            sys.exit(1)

    finally:
        # Clean up server
        if server_process:
            print("\n\nStopping server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()
            print("✓ Server stopped")


if __name__ == "__main__":
    main()
