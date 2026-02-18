#!/usr/bin/env python3
"""Phase 40 preflight: verify Qwen3-8B tokenizer compatibility.

Checks that the 8B and 30B models share identical special token IDs and
produce identical ChatML output for the same messages. If any check fails,
exits with code 1 — the training pipeline should not proceed.

Usage:
    uv run python scripts/phase40_tokenizer_check.py

Exit codes:
    0  All checks passed — safe to proceed with training
    1  One or more checks failed — STOP, investigate before training
"""

import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Expected special token IDs (Qwen3 family, all models share these)
# ---------------------------------------------------------------------------
EXPECTED_TOKENS: dict[str, int] = {
    "<|im_start|>": 151644,
    "<|im_end|>": 151645,
    "<tool_call>": 151657,
    "</tool_call>": 151658,
    "<tool_response>": 151665,
    "</tool_response>": 151666,
}

MODEL_8B = "mlx-community/Qwen3-8B-4bit"
MODEL_30B = "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"
TRAIN_DATA = Path("data/phase33_merged/train.jsonl")


def check_special_tokens(tokenizer: object, model_label: str) -> bool:
    """Verify that all required special tokens encode as single IDs."""
    passed = True
    print(f"\n[{model_label}] Special token ID check:")
    for token_str, expected_id in EXPECTED_TOKENS.items():
        ids = tokenizer.encode(token_str, add_special_tokens=False)  # type: ignore[attr-defined]
        if len(ids) == 1 and ids[0] == expected_id:
            print(f"  ✓  {token_str!r:30s} → {ids[0]}")
        else:
            print(f"  ✗  {token_str!r:30s} → {ids} (expected [{expected_id}])")
            passed = False
    return passed


def check_chat_template(tok8b: object, tok30b: object) -> bool:
    """Verify apply_chat_template produces identical ChatML for both tokenizers."""
    print("\n[ChatML template check]")
    messages = [
        {"role": "system", "content": "You are Punie, an AI coding assistant."},
        {"role": "user", "content": "Check types in src/main.py"},
    ]
    # Use tokenize=False to get the string output
    out8b = tok8b.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)  # type: ignore[attr-defined]
    out30b = tok30b.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)  # type: ignore[attr-defined]

    if out8b == out30b:
        print(f"  ✓  ChatML output is identical ({len(out8b)} chars)")
        print(f"     Preview: {out8b[:120]!r}...")
        return True
    else:
        print("  ✗  ChatML output DIFFERS between 8B and 30B tokenizers!")
        print(f"     8B:  {out8b[:200]!r}")
        print(f"     30B: {out30b[:200]!r}")
        return False


def check_train_sample_encoding(tok8b: object, tok30b: object) -> bool:
    """Cross-encode first training sample, verify special token positions match."""
    print("\n[Train sample cross-encoding check]")
    if not TRAIN_DATA.exists():
        print(f"  ⚠  Training data not found at {TRAIN_DATA} — skipping cross-check")
        return True  # Not a hard failure; data may not be present on all machines

    with TRAIN_DATA.open() as f:
        line = f.readline().strip()

    example = json.loads(line)
    messages = example.get("messages", [])
    if not messages:
        print("  ⚠  First line has no messages — skipping cross-check")
        return True

    text = tok8b.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)  # type: ignore[attr-defined]

    ids8b = tok8b.encode(text)  # type: ignore[attr-defined]
    ids30b = tok30b.encode(text)  # type: ignore[attr-defined]

    # Find positions of special tokens in each encoding
    special_ids = set(EXPECTED_TOKENS.values())

    pos8b = [i for i, t in enumerate(ids8b) if t in special_ids]
    pos30b = [i for i, t in enumerate(ids30b) if t in special_ids]

    if pos8b == pos30b:
        print(f"  ✓  Special token positions match ({len(pos8b)} found)")
        return True
    else:
        print("  ✗  Special token positions DIFFER!")
        print(f"     8B positions:  {pos8b[:20]}")
        print(f"     30B positions: {pos30b[:20]}")
        return False


def main() -> int:
    """Run all preflight checks. Returns 0 if all pass, 1 otherwise."""
    try:
        from transformers import AutoTokenizer
    except ImportError:
        print("ERROR: transformers not installed. Run: uv add transformers")
        return 1

    print("=" * 60)
    print("Phase 40 Preflight: Qwen3-8B Tokenizer Compatibility Check")
    print("=" * 60)
    print(f"\nLoading 8B tokenizer: {MODEL_8B}")

    try:
        tok8b = AutoTokenizer.from_pretrained(MODEL_8B, trust_remote_code=True)
    except Exception as e:
        print(f"ERROR: Could not load {MODEL_8B}: {e}")
        print("\nFix: Download the model with:")
        print(f"  uv run python -c \"from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('{MODEL_8B}')\"")
        return 1

    print(f"Loading 30B tokenizer: {MODEL_30B}")
    try:
        tok30b = AutoTokenizer.from_pretrained(MODEL_30B, trust_remote_code=True)
    except Exception as e:
        print(f"ERROR: Could not load {MODEL_30B}: {e}")
        print("The 30B tokenizer is needed only for cross-check. If not available,")
        print("you can skip cross-check by running with --no-crosscheck (not yet implemented).")
        return 1

    results: list[bool] = []

    results.append(check_special_tokens(tok8b, "Qwen3-8B"))
    results.append(check_special_tokens(tok30b, "Qwen3-30B"))
    results.append(check_chat_template(tok8b, tok30b))
    results.append(check_train_sample_encoding(tok8b, tok30b))

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)

    if all(results):
        print(f"PREFLIGHT PASSED ({passed}/{total} checks) ✓")
        print("\nSafe to proceed with Phase 40 training:")
        print("  bash scripts/run_phase40_8b_pipeline.sh")
        return 0
    else:
        print(f"PREFLIGHT FAILED ({passed}/{total} checks passed) ✗")
        print("\nDo NOT proceed with training until all checks pass.")
        print("Review the failures above and investigate tokenizer differences.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
