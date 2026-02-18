#!/usr/bin/env python3
"""Run Phase 33 evaluation suite against the newly trained model.

Usage:
    uv run python scripts/run_phase33_eval.py [--model PATH] [--port PORT]

Defaults:
    --model fused_model_qwen3_phase33_5bit
    --port  8080

Outputs:
    logs/phase33_eval_results.json   — Full JSON results
    logs/phase33_eval_summary.txt    — Human-readable summary
"""

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from punie.training.eval_runner import EvalRunConfig, run_evaluation
from punie.training.eval_suites import create_phase33_suite
from punie.training.server_config import QWEN_STOP_SEQUENCES, ServerConfig


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run Phase 33 eval suite")
    p.add_argument(
        "--model",
        default="fused_model_qwen3_phase33_5bit",
        help="Path to the model (default: fused_model_qwen3_phase33_5bit)",
    )
    p.add_argument("--port", type=int, default=8080, help="Server port (default: 8080)")
    p.add_argument("--no-manage-server", action="store_true", help="Server already running")
    return p.parse_args()


async def main() -> int:
    args = parse_args()

    model_path = args.model
    if not Path(model_path).exists():
        print(f"ERROR: Model not found: {model_path}", file=sys.stderr)
        print("Run the training pipeline first:", file=sys.stderr)
        print("  bash scripts/run_phase33_overnight.sh", file=sys.stderr)
        return 1

    print(f"Phase 33 Evaluation")
    print(f"  Model: {model_path}")
    print(f"  Port:  {args.port}")
    print(f"  Suite: phase33 (26 prompts)")
    print()

    server_config = ServerConfig(
        model_path=model_path,
        port=args.port,
        host="127.0.0.1",
        stop_sequences=QWEN_STOP_SEQUENCES,
    )

    suite = create_phase33_suite()
    workspace = Path(".")

    run_config = EvalRunConfig(
        server_config=server_config,
        suite=suite,
        workspace=workspace,
        manage_server=not args.no_manage_server,
    )

    print(f"Starting evaluation ({len(suite.prompts)} prompts)...")
    start = datetime.now()
    report = await run_evaluation(run_config)
    elapsed = (datetime.now() - start).total_seconds()

    # ------------------------------------------------------------------ #
    # Summary
    # ------------------------------------------------------------------ #
    print()
    print("=" * 60)
    print(f"Phase 33 Eval Results — {report.timestamp.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    print(f"Model:        {report.model_name}")
    print(f"Suite:        {report.suite_name}")
    print(f"Prompts:      {len(report.results)}")
    print(f"Overall:      {report.overall_score:.1%}")
    print(f"Success rate: {report.success_rate:.1%}")
    print(f"Elapsed:      {elapsed:.0f}s ({elapsed/len(report.results):.1f}s avg)")
    print()

    # Per-category breakdown
    category_results: dict[str, list] = defaultdict(list)
    for i, result in enumerate(report.results):
        prompt = suite.prompts[i]
        category_results[prompt.category].append(result)

    print("Category breakdown:")
    all_passed = True
    for category, results in sorted(category_results.items()):
        avg_score = sum(r.score for r in results) / len(results)
        avg_ms = sum(r.duration_ms for r in results) / len(results)
        passed = sum(1 for r in results if r.score >= 0.5)
        status = "✓" if avg_score >= 0.7 else "✗"
        if avg_score < 0.7:
            all_passed = False
        print(f"  {status} {category:30s}: {avg_score:.1%} ({passed}/{len(results)} passed, {avg_ms:.0f}ms avg)")

    print()

    # Per-prompt detail
    print("Per-prompt results:")
    for i, result in enumerate(report.results):
        prompt = suite.prompts[i]
        status = "✓" if result.score >= 0.5 else "✗"
        calls = ", ".join(result.tool_calls_made) if result.tool_calls_made else "none"
        print(f"  {status} [{result.prompt_id}] score={result.score:.2f} tools=[{calls}] {result.duration_ms:.0f}ms")
        if result.score < 0.5 and not result.success:
            # Show error snippet
            snippet = result.response_text[:100].replace("\n", " ")
            print(f"      ERROR: {snippet}")

    print()

    # Final verdict
    target_score = 0.80
    if report.overall_score >= target_score:
        print(f"✅ PASS: {report.overall_score:.1%} ≥ {target_score:.0%} target")
        verdict = "PASS"
    else:
        print(f"❌ FAIL: {report.overall_score:.1%} < {target_score:.0%} target")
        verdict = "FAIL"

    # ------------------------------------------------------------------ #
    # Save results
    # ------------------------------------------------------------------ #
    Path("logs").mkdir(exist_ok=True)

    # JSON results
    results_data = {
        "model": report.model_name,
        "suite": report.suite_name,
        "timestamp": report.timestamp.isoformat(),
        "overall_score": report.overall_score,
        "success_rate": report.success_rate,
        "verdict": verdict,
        "elapsed_seconds": elapsed,
        "prompts": [
            {
                "id": suite.prompts[i].id,
                "category": suite.prompts[i].category,
                "score": r.score,
                "success": r.success,
                "tool_calls": list(r.tool_calls_made),
                "duration_ms": r.duration_ms,
                "response_snippet": r.response_text[:200],
            }
            for i, r in enumerate(report.results)
        ],
    }

    json_path = Path("logs/phase33_eval_results.json")
    json_path.write_text(json.dumps(results_data, indent=2))
    print(f"\nResults saved to {json_path}")

    # Text summary
    summary_path = Path("logs/phase33_eval_summary.txt")
    with open(summary_path, "w") as f:
        f.write(f"Phase 33 Evaluation Summary\n")
        f.write(f"{'=' * 40}\n")
        f.write(f"Date:         {report.timestamp.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"Model:        {report.model_name}\n")
        f.write(f"Overall:      {report.overall_score:.1%}\n")
        f.write(f"Success rate: {report.success_rate:.1%}\n")
        f.write(f"Verdict:      {verdict}\n")
        f.write(f"\nCategory scores:\n")
        for category, results in sorted(category_results.items()):
            avg = sum(r.score for r in results) / len(results)
            f.write(f"  {category}: {avg:.1%}\n")
    print(f"Summary saved to {summary_path}")

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
