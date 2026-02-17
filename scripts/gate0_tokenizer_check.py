#!/usr/bin/env python3
"""Gate 0: Verify Devstral Small 2 tokenizer has single-token tool delimiters.

Critical check from Phase 25 lesson: Multi-token delimiters corrupt training data.
This 5-minute check prevents wasting 4-7 hours on a doomed evaluation.
"""

from transformers import AutoTokenizer
import sys


def check_delimiter(tokenizer, delimiter: str) -> tuple[bool, list[int]]:
    """Check if delimiter is single token.

    Args:
        tokenizer: HuggingFace tokenizer instance
        delimiter: String to check (e.g., "[TOOL_CALLS]")

    Returns:
        (is_single_token, token_ids) tuple
    """
    token_ids = tokenizer.encode(delimiter, add_special_tokens=False)
    is_single = len(token_ids) == 1
    return is_single, token_ids


def main():
    print("Gate 0: Tokenizer Verification")
    print("=" * 60)
    print()

    # Download tokenizer (no model weights)
    print("Loading tokenizer from mlx-community/Devstral-Small-2-24B-Instruct-2512-4bit...")
    try:
        tokenizer = AutoTokenizer.from_pretrained(
            "mlx-community/Devstral-Small-2-24B-Instruct-2512-4bit",
            trust_remote_code=True
        )
        print(f"✓ Tokenizer loaded: {tokenizer.__class__.__name__}")
    except Exception as e:
        print(f"✗ Failed to load tokenizer: {e}")
        return 1

    print()

    # Check all 4 delimiters
    delimiters = [
        "[TOOL_CALLS]",
        "[/TOOL_CALLS]",
        "[TOOL_RESULTS]",
        "[/TOOL_RESULTS]",
    ]

    results = []
    for delimiter in delimiters:
        is_single, token_ids = check_delimiter(tokenizer, delimiter)
        results.append((delimiter, is_single, token_ids))

        status = "✓ PASS" if is_single else "✗ FAIL"
        print(f"{status}: '{delimiter}'")
        print(f"  Token IDs: {token_ids}")
        print(f"  Count: {len(token_ids)} token{'s' if len(token_ids) > 1 else ''}")
        print()

    # Summary
    print("=" * 60)
    all_passed = all(is_single for _, is_single, _ in results)

    if all_passed:
        print("✓ GATE 0 PASSED: All delimiters are single tokens")
        print()
        print("Decision: Proceed to Gate 1 (MLX Smoke Test)")
        return 0
    else:
        print("✗ GATE 0 FAILED: One or more delimiters are multi-token")
        print()
        print("Decision: STOP - Training infeasible with multi-token delimiters")
        print("Reason: Multi-token delimiters corrupt training data (Phase 25 lesson)")
        print()
        failed = [d for d, ok, _ in results if not ok]
        print(f"Failed delimiters: {', '.join(failed)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
