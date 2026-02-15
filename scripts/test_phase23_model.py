"""Test Phase 23 model: Code Mode + ty integration.

Tests 5 ty-specific queries:
1. Simple type check
2. Check and show errors
3. Direct answer about Protocol
4. Check multiple files
5. Type-informed fix workflow
"""

import asyncio
from pathlib import Path

# Test queries focused on ty integration
TEST_QUERIES = [
    "Check types in src/punie/agent/",  # Should call typecheck()
    "What type errors are in config.py?",  # Should call typecheck() and list errors
    "What is a Protocol in Python typing?",  # Direct answer (no tool call)
    "Check types in both stubs.py and typed_tools.py",  # Multiple typecheck calls
    "Fix the type errors in factory.py",  # check → read → fix pattern
]


async def test_model():
    """Test Phase 23 model with ty-specific queries."""
    print("=" * 60)
    print("Phase 23 Model Test: ty Integration")
    print("=" * 60)
    print()

    # Note: This is a placeholder - actual testing would use mlx_lm.server
    print("Test queries:")
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"{i}. {query}")

    print()
    print("To test:")
    print("1. Start server: uv run python -m mlx_lm.server \\")
    print("                 --model fused_model_qwen3_phase23_ty_5bit \\")
    print("                 --port 8080")
    print("2. Run queries through PydanticAI agent")
    print("3. Verify:")
    print("   - ty queries use typecheck() (not run_command)")
    print("   - Direct answers don't call tools")
    print("   - Multi-step workflows work correctly")


if __name__ == "__main__":
    asyncio.run(test_model())
