#!/usr/bin/env python3
"""Test Phase 22 Code Mode model accuracy.

Tests both single-tool and multi-step query capabilities.
Validates that the model generates correct execute_code calls with Python.

Note: This script requires mlx_lm.server to be running with the Phase 22 model.
"""

import json
import sys
from pathlib import Path


def test_single_tool_accuracy():
    """Test single-tool queries (should maintain Phase 21's 100% accuracy)."""
    print("=" * 80)
    print("TEST 1: Single-Tool Accuracy (Target: 100%)")
    print("=" * 80)
    print()

    test_cases = [
        {
            "query": "Read the README.md file",
            "expected_pattern": "execute_code",
            "expected_content": "read_file",
            "description": "Should generate execute_code with read_file call",
        },
        {
            "query": "Run the command to find all Python files",
            "expected_pattern": "execute_code",
            "expected_content": "run_command",
            "description": "Should generate execute_code with run_command call",
        },
        {
            "query": "What is dependency injection?",
            "expected_pattern": "direct_answer",
            "expected_content": None,
            "description": "Should answer directly without tool calls",
        },
        {
            "query": "Find all classes that inherit from Exception",
            "expected_pattern": "execute_code",
            "expected_content": "run_command",
            "description": "Should generate execute_code with grep command",
        },
        {
            "query": "Explain the difference between ORM and raw SQL",
            "expected_pattern": "direct_answer",
            "expected_content": None,
            "description": "Should answer directly about concepts",
        },
    ]

    print("Test cases:")
    for i, tc in enumerate(test_cases, 1):
        print(f"{i}. {tc['query']}")
        print(f"   Expected: {tc['expected_pattern']}")
        print()

    print("⚠️  Manual validation required:")
    print("   1. Start server: mlx_lm.server --model fused_model_qwen3_phase22_code_5bit")
    print("   2. Test each query through PydanticAI or curl")
    print("   3. Verify tool call patterns match expectations")
    print()

    return test_cases


def test_multi_step_accuracy():
    """Test multi-step queries (new Code Mode capability)."""
    print("=" * 80)
    print("TEST 2: Multi-Step Accuracy (Target: 80%+)")
    print("=" * 80)
    print()

    test_cases = [
        {
            "query": "Find all Python files and count the total lines of code",
            "expected_python": [
                "run_command",
                "for",
                "read_file",
                "split",
                "len",
                "print",
            ],
            "description": "Should generate loop over files with read + count",
        },
        {
            "query": "Find all test files and count how many test functions they contain",
            "expected_python": [
                "run_command",
                "for",
                "read_file",
                ".count(",
                "test_",
                "print",
            ],
            "description": "Should generate loop with count('def test_')",
        },
        {
            "query": "If config.py exists, read it; otherwise create a default one",
            "expected_python": [
                "try",
                "read_file",
                "except",
                "write_file",
                "print",
            ],
            "description": "Should generate try/except with conditional write",
        },
        {
            "query": "Count how many Python files have docstrings",
            "expected_python": [
                "run_command",
                "for",
                "read_file",
                "if",
                "count",
                "print",
            ],
            "description": "Should generate loop with conditional counting",
        },
        {
            "query": "Find all directories and count lines of code in each",
            "expected_python": [
                "run_command",
                "for",
                "read_file",
                "total",
                "print",
            ],
            "description": "Should generate nested loops with aggregation",
        },
    ]

    print("Test cases:")
    for i, tc in enumerate(test_cases, 1):
        print(f"{i}. {tc['query']}")
        print(f"   Expected patterns: {', '.join(tc['expected_python'][:3])}, ...")
        print()

    print("⚠️  Manual validation required:")
    print("   1. Start server with Phase 22 model")
    print("   2. Test each multi-step query")
    print("   3. Verify generated Python contains expected patterns")
    print("   4. Verify code executes successfully")
    print()

    return test_cases


def analyze_training_data():
    """Analyze Phase 22 training data distribution."""
    print("=" * 80)
    print("TRAINING DATA ANALYSIS")
    print("=" * 80)
    print()

    data_dir = Path("data/phase22_merged")

    if not data_dir.exists():
        print(f"⚠️  Data directory not found: {data_dir}")
        return

    for split in ["train", "valid", "test"]:
        file_path = data_dir / f"{split}.jsonl"
        if not file_path.exists():
            continue

        examples = []
        with open(file_path) as f:
            for line in f:
                examples.append(json.loads(line))

        # Count patterns
        execute_code_count = sum(1 for ex in examples if "execute_code" in ex["text"])
        tool_call_count = sum(1 for ex in examples if "<tool_call>" in ex["text"])
        direct_count = len(examples) - tool_call_count

        # Count Python patterns in execute_code examples
        loop_count = sum(1 for ex in examples if "execute_code" in ex["text"] and " for " in ex["text"])
        conditional_count = sum(1 for ex in examples if "execute_code" in ex["text"] and " if " in ex["text"])

        print(f"{split.upper()} split ({len(examples)} examples):")
        print(f"  Tool-calling: {tool_call_count} ({int(tool_call_count/len(examples)*100)}%)")
        print(f"    - execute_code: {execute_code_count}")
        print(f"    - Other tools: {tool_call_count - execute_code_count}")
        print(f"  Direct answers: {direct_count} ({int(direct_count/len(examples)*100)}%)")
        print(f"  Python patterns:")
        print(f"    - Loops (for): {loop_count}")
        print(f"    - Conditionals (if): {conditional_count}")
        print()


def show_model_info():
    """Show Phase 22 model information."""
    print("=" * 80)
    print("PHASE 22 MODEL INFORMATION")
    print("=" * 80)
    print()

    model_path = Path("fused_model_qwen3_phase22_code_5bit")

    if model_path.exists():
        import subprocess
        result = subprocess.run(
            ["du", "-sh", str(model_path)],
            capture_output=True,
            text=True,
        )
        size = result.stdout.split()[0] if result.stdout else "Unknown"
        print(f"Model: {model_path}")
        print(f"Size: {size}")
        print(f"Quantization: 5-bit")
        print(f"Base: Qwen3-Coder-30B-A3B-Instruct")
        print()

        # Check for adapter
        adapter_path = Path("adapters_phase22_code")
        if adapter_path.exists():
            result = subprocess.run(
                ["du", "-sh", str(adapter_path)],
                capture_output=True,
                text=True,
            )
            adapter_size = result.stdout.split()[0] if result.stdout else "Unknown"
            print(f"LoRA Adapter: {adapter_path}")
            print(f"Size: {adapter_size}")
            print()
    else:
        print(f"⚠️  Model not found: {model_path}")
        print("   Run: ./scripts/train_phase22.sh")
        print()


def main():
    """Run all Phase 22 tests."""
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "PHASE 22 CODE MODE TESTING" + " " * 32 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    # Show model info
    show_model_info()

    # Analyze training data
    analyze_training_data()

    # Run tests
    single_tool_cases = test_single_tool_accuracy()
    multi_step_cases = test_multi_step_accuracy()

    # Summary
    print("=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print()
    print(f"Single-tool tests: {len(single_tool_cases)} queries (Target: 100% accuracy)")
    print(f"Multi-step tests: {len(multi_step_cases)} queries (Target: 80%+ accuracy)")
    print()
    print("Next steps:")
    print("  1. Start mlx_lm.server with Phase 22 model:")
    print("     uv run python -m mlx_lm.server \\")
    print("       --model fused_model_qwen3_phase22_code_5bit \\")
    print("       --port 8080")
    print()
    print("  2. Test queries through PydanticAI or curl")
    print()
    print("  3. Benchmark latency vs Phase 21:")
    print("     uv run python scripts/benchmark_phase22_vs_21.py")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)
