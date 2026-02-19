#!/usr/bin/env python3
"""Phase 44 Deep Dive — autonomous overnight analysis.

Runs after Phase 44 training + eval completes. Performs:
  1. Methodology audit — are eval scores trustworthy?
  2. False-positive / false-negative detection
  3. Think-mode analysis — did <think> truncation help or hurt?
  4. Temperature=0.0 consistency check (3 re-runs of 5 prompts)
  5. Performance benchmark — warm query time and GPU memory
  6. Cross-model comparison — Phase 44 vs Phase 33b production
  7. Writes docs/research/phase44-deep-dive.md

Usage:
    uv run python scripts/phase44_deep_dive.py
    uv run python scripts/phase44_deep_dive.py --phase44-model PATH --phase33b-model PATH
"""

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_PHASE44_MODEL = "fused_model_qwen3_phase44_format_fix_5bit"
DEFAULT_PHASE33B_MODEL = "fused_model_qwen3_phase33b_5bit"
EVAL_RESULTS_JSON = "logs/phase33_direct_eval_results.json"
REPORT_PATH = "docs/research/phase44-deep-dive.md"
SERVER_PORT = 8080
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}/v1"

EVAL_SYSTEM_PROMPT = (
    "You are Punie, an AI coding assistant. "
    "Use execute_code(code) to call tools. "
    "Available tools: read_file, write_file, run_command, typecheck, ruff_check, pytest_run, "
    "goto_definition, find_references, hover, document_symbols, workspace_symbols, "
    "git_status, git_diff, git_log, "
    "cst_find_pattern, cst_rename, cst_add_import, "
    "validate_component, check_render_tree, validate_escape_context, "
    "validate_service_registration, check_dependency_graph, "
    "validate_injection_site, validate_middleware_chain, "
    "check_di_template_binding, validate_route_pattern."
)

# 5 representative prompts for consistency + performance benchmarking
BENCHMARK_PROMPTS = [
    ("git-01", "Check git status and tell me which files have been modified."),
    ("valid-01", "Run type checking on src/ and report any type errors."),
    ("cst-01", "Find all class definitions in src/punie/http/websocket.py."),
    ("dom-01", "Check if src/views/error_page.py is a valid tdom component."),
    ("multi-01", "Find the definition of HomeView, read it, validate as a tdom component, then run tests."),
]

# Keywords that indicate likely prose mention vs real tool call
PROSE_INDICATORS = [
    "would use", "should use", "I'll use", "we could", "to call",
    "needs to", "want to", "going to", "can use", "let me",
    "i would", "i should", "i need",
]


# ---------------------------------------------------------------------------
# Server management
# ---------------------------------------------------------------------------

def start_server(model_path: str, port: int) -> subprocess.Popen:
    cmd = [
        "uv", "run", "python", "-m", "mlx_lm", "server",
        "--model", model_path,
        "--port", str(port),
        "--host", "127.0.0.1",
    ]
    print(f"  Starting: {' '.join(cmd[-4:])}")
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


async def wait_for_server(url: str, timeout: float = 120.0) -> bool:
    deadline = time.time() + timeout
    async with httpx.AsyncClient() as client:
        while time.time() < deadline:
            try:
                r = await client.get(f"{url}/models", timeout=3.0)
                if r.status_code == 200:
                    return True
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
            await asyncio.sleep(1.0)
    return False


async def get_model_id(url: str, expected_name: str) -> str:
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{url}/models", timeout=10.0)
            all_ids = [m["id"] for m in r.json().get("data", [])]
            # Find the local model path in the list (mlx_lm includes all cached models)
            for mid in all_ids:
                if expected_name in mid:
                    return mid
            return all_ids[0] if all_ids else expected_name
        except Exception:
            return expected_name


# ---------------------------------------------------------------------------
# Prompt runner
# ---------------------------------------------------------------------------

async def run_prompt_once(
    client: httpx.AsyncClient,
    query: str,
    max_tokens: int = 512,
    model_id: str = "local",
) -> tuple[float, dict]:
    payload = {
        "model": model_id,
        "messages": [
            {"role": "system", "content": EVAL_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "stop": ["<|im_end|>", "<|endoftext|>", "<think>"],
    }
    start = time.time()
    try:
        r = await client.post(
            f"{SERVER_URL}/chat/completions",
            json=payload,
            timeout=120.0,
        )
        elapsed = time.time() - start
        if r.status_code != 200:
            return elapsed, {"error": f"HTTP {r.status_code}"}
        return elapsed, r.json()
    except httpx.TimeoutException:
        return time.time() - start, {"error": "TIMEOUT"}
    except Exception as e:
        return time.time() - start, {"error": str(e)}


def extract_response_body(response_json: dict) -> tuple[bool, str, str]:
    """Extract response. Returns (has_execute_code, code_body, raw_content)."""
    choices = response_json.get("choices", [])
    if not choices:
        return False, "", ""

    msg = choices[0].get("message", {})
    raw_content = msg.get("content", "") or ""

    # Native tool_calls
    for tc in msg.get("tool_calls", []):
        fn = tc.get("function", {})
        args_raw = fn.get("arguments", "{}")
        if fn.get("name") == "execute_code":
            try:
                args = json.loads(args_raw)
                code = args.get("code") or next((v for v in args.values() if isinstance(v, str)), "")
                return True, code or args_raw, raw_content
            except json.JSONDecodeError:
                return True, args_raw, raw_content
        if fn.get("name"):
            return False, fn["name"] + "\n" + args_raw, raw_content

    # XML in content
    m = re.search(
        r"<tool_call>\s*<function=execute_code>\s*<parameter=code>\s*(.*?)\s*(?:</parameter>|$)",
        raw_content, re.DOTALL,
    )
    if m:
        return True, m.group(1), raw_content

    return False, raw_content, raw_content


def classify_keyword_occurrence(keyword: str, code_body: str) -> str:
    """Classify how a keyword appears: 'real_call', 'prose', 'comment', 'string', 'none'."""
    if keyword not in code_body:
        return "none"

    lines = code_body.splitlines()
    for line in lines:
        stripped = line.strip()
        if keyword not in stripped:
            continue

        # Comment
        if stripped.startswith("#") and keyword in stripped:
            return "comment"

        # String literal
        idx = stripped.find(keyword)
        before = stripped[:idx]
        in_string = (before.count('"') % 2 == 1) or (before.count("'") % 2 == 1)
        if in_string:
            return "string"

        # Prose indicators (if code_body looks like prose not code)
        body_lower = code_body.lower()
        if any(indicator in body_lower for indicator in PROSE_INDICATORS):
            # Check if keyword is near a prose phrase
            for indicator in PROSE_INDICATORS:
                pos_ind = body_lower.find(indicator)
                pos_kw = body_lower.find(keyword)
                if pos_ind != -1 and abs(pos_ind - pos_kw) < 100:
                    return "prose"

        # Real call: keyword followed by ( or as identifier
        real_call_pattern = re.search(rf"\b{re.escape(keyword)}\s*\(", stripped)
        if real_call_pattern:
            return "real_call"

        # Default: appears in code context
        return "code_context"

    return "none"


# ---------------------------------------------------------------------------
# Analysis sections
# ---------------------------------------------------------------------------

async def section_methodology_audit(eval_results: dict) -> dict:
    """Audit the eval results for false positives / false negatives."""
    print("\n[1/5] Methodology Audit")

    prompts = eval_results.get("prompts", [])
    findings = []
    false_positives = []
    false_negatives = []
    score_distribution = defaultdict(int)

    for p in prompts:
        score = p["score"]
        code_body = p.get("code_snippet", "")
        has_ec = p.get("has_execute_code", False)
        pid = p["id"]

        score_distribution[score] += 1

        # Reconstruct what keywords were expected
        # (We don't have this in results JSON, so we note the score tier)
        finding = {
            "id": pid,
            "score": score,
            "has_execute_code": has_ec,
            "code_snippet": code_body[:300] if code_body else "",
            "flags": [],
        }

        # Check 1: score=0.0 with empty code_body → think-mode or no response
        if score == 0.0 and not code_body.strip():
            finding["flags"].append("no_response_or_think_truncated")

        # Check 2: score=0.5 (direct call) — code body shows prose?
        if score == 0.5 and code_body:
            code_lower = code_body.lower()
            if any(ind in code_lower for ind in PROSE_INDICATORS):
                finding["flags"].append("possible_prose_false_positive")
                false_positives.append(pid)

        # Check 3: score=1.0 — is execute_code syntactically valid?
        if score == 1.0 and has_ec and code_body:
            # Check for comments/strings containing keyword (false positive risk)
            if "# " in code_body and not re.search(r"\b\w+\s*\(", code_body):
                finding["flags"].append("execute_code_only_comments")
                false_positives.append(pid)

        # Check 4: score=0.0 but response_snippet shows a tool was mentioned
        if score == 0.0:
            snippet = p.get("response_snippet", "")
            if snippet and len(snippet) > 50 and "tool" not in snippet.lower():
                finding["flags"].append("zero_score_with_content")
                false_negatives.append(pid)

        findings.append(finding)
        flag_str = ", ".join(finding["flags"]) if finding["flags"] else "clean"
        print(f"  [{pid:8s}] score={score:.1f} ec={has_ec} flags=[{flag_str}]")

    result = {
        "score_distribution": dict(score_distribution),
        "findings": findings,
        "suspected_false_positives": false_positives,
        "suspected_false_negatives": false_negatives,
        "verdict": "CLEAN" if not false_positives and not false_negatives else "FLAGS_FOUND",
    }

    print(f"  Score distribution: {dict(score_distribution)}")
    print(f"  Suspected FP: {false_positives or 'none'}")
    print(f"  Suspected FN: {false_negatives or 'none'}")
    return result


async def section_consistency_check() -> dict:
    """Run 5 prompts 3 times each — temperature=0.0 must be deterministic."""
    print("\n[2/5] Consistency Check (temperature=0.0, 3 runs × 5 prompts)")

    proc: subprocess.Popen | None = None
    results = {}

    try:
        proc = start_server(DEFAULT_PHASE44_MODEL, SERVER_PORT)
        await asyncio.sleep(3.0)
        if proc.poll() is not None:
            print("  ERROR: Server exited immediately — port likely occupied")
            return {"error": "server_start_failed", "verdict": "SKIPPED"}
        ready = await wait_for_server(SERVER_URL, timeout=120.0)
        if not ready:
            print("  ERROR: Server did not start in 120s")
            proc.kill()
            return {"error": "server_timeout", "verdict": "SKIPPED"}

        model_id = await get_model_id(SERVER_URL, DEFAULT_PHASE44_MODEL)
        print(f"  Server ready (model_id: {model_id[:60]})")

        inconsistent = []
        all_consistent = True

        async with httpx.AsyncClient() as client:
            for prompt_id, query in BENCHMARK_PROMPTS[:5]:
                run_scores = []
                for run in range(3):
                    elapsed, resp = await run_prompt_once(client, query, 512, model_id)
                    has_ec, code_body, _ = extract_response_body(resp)
                    # Score loosely: 1.0 if execute_code, 0.5 if direct, 0.0 otherwise
                    if has_ec and code_body:
                        score = 1.0
                    elif code_body and len(code_body) > 10:
                        score = 0.5
                    else:
                        score = 0.0
                    run_scores.append(score)

                consistent = len(set(run_scores)) == 1
                if not consistent:
                    inconsistent.append(prompt_id)
                    all_consistent = False

                print(f"  [{prompt_id}] runs={run_scores} {'✓ consistent' if consistent else '✗ INCONSISTENT'}")
                results[prompt_id] = {"runs": run_scores, "consistent": consistent}

    finally:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    verdict = "PASS" if all_consistent else f"FAIL ({len(inconsistent)} inconsistent)"
    print(f"  Verdict: {verdict}")
    return {
        "results": results,
        "inconsistent_prompts": inconsistent,
        "verdict": verdict,
    }


async def section_think_mode_analysis(eval_results: dict) -> dict:
    """Analyze think-mode impact: count truncated responses, estimate fix effectiveness."""
    print("\n[3/5] Think-Mode Analysis")

    prompts = eval_results.get("prompts", [])
    think_truncated = []
    zero_with_content = []

    for p in prompts:
        if p["score"] == 0.0:
            snippet = p.get("code_snippet", "") + p.get("response_snippet", "")
            if not snippet.strip():
                think_truncated.append(p["id"])  # No content → <think> stopped everything
            elif len(snippet.strip()) < 30:
                think_truncated.append(p["id"])  # Very short → likely truncated
            else:
                zero_with_content.append(p["id"])  # Has content but still scored 0

    # Run a quick test: send one prompt WITHOUT the <think> stop sequence
    # to check if think-mode is active
    proc: subprocess.Popen | None = None
    think_test_result = {}

    try:
        proc = start_server(DEFAULT_PHASE44_MODEL, SERVER_PORT)
        await asyncio.sleep(3.0)
        if proc.poll() is not None:
            think_test_result = {"error": "server_start_failed"}
        else:
            ready = await wait_for_server(SERVER_URL, timeout=120.0)
            if ready:
                model_id = await get_model_id(SERVER_URL, DEFAULT_PHASE44_MODEL)
                # Test WITHOUT <think> stop — check if model outputs <think>
                payload = {
                    "model": model_id,
                    "messages": [
                        {"role": "system", "content": EVAL_SYSTEM_PROMPT},
                        {"role": "user", "content": "List the 5 most recent git commits."},
                    ],
                    "max_tokens": 256,
                    "temperature": 0.0,
                    "stop": ["<|im_end|>", "<|endoftext|>"],  # No <think> stop
                }
                async with httpx.AsyncClient() as client:
                    r = await client.post(
                        f"{SERVER_URL}/chat/completions",
                        json=payload,
                        timeout=60.0,
                    )
                    content = ""
                    if r.status_code == 200:
                        choices = r.json().get("choices", [])
                        if choices:
                            content = choices[0].get("message", {}).get("content", "") or ""

                think_starts = content.startswith("<think>")
                think_test_result = {
                    "content_preview": content[:200],
                    "starts_with_think": think_starts,
                    "length": len(content),
                }
                print(f"  Think-mode test (no stop): starts_with_think={think_starts}")
                print(f"  Content preview: {content[:100]!r}")
            else:
                think_test_result = {"error": "server_timeout"}
    except Exception as e:
        think_test_result = {"error": str(e)}
    finally:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    print(f"  Likely think-truncated (0.0, empty): {think_truncated}")
    print(f"  Zero score with content: {zero_with_content}")

    return {
        "think_truncated_prompts": think_truncated,
        "zero_with_content": zero_with_content,
        "think_test_without_stop": think_test_result,
        "verdict": (
            "NO_THINK" if not think_truncated else
            f"{len(think_truncated)} prompts likely think-truncated"
        ),
    }


async def section_performance_benchmark(model_path: str, label: str) -> dict:
    """Benchmark warm query time and report GPU memory."""
    print(f"\n[4/5] Performance Benchmark — {label}")

    proc: subprocess.Popen | None = None
    benchmark = {}

    try:
        proc = start_server(model_path, SERVER_PORT)
        await asyncio.sleep(3.0)
        if proc.poll() is not None:
            print("  ERROR: Server exited immediately")
            return {"error": "server_start_failed", "label": label}

        ready = await wait_for_server(SERVER_URL, timeout=120.0)
        if not ready:
            print("  ERROR: Server timeout")
            proc.kill()
            return {"error": "server_timeout", "label": label}

        model_id = await get_model_id(SERVER_URL, model_path)
        print("  Server ready. Running warm-up queries...")

        async with httpx.AsyncClient() as client:
            # Warm-up: 3 queries (not measured, triggers model load)
            for i in range(3):
                elapsed, _ = await run_prompt_once(
                    client, BENCHMARK_PROMPTS[i % len(BENCHMARK_PROMPTS)][1],
                    256, model_id
                )
                print(f"    Warm-up {i+1}: {elapsed:.1f}s")

            # Measure: 5 prompts × 5 runs each
            print("  Measuring (5 prompts × 5 runs)...")
            all_timings: dict[str, list[float]] = {}

            for prompt_id, query in BENCHMARK_PROMPTS:
                timings = []
                for run in range(5):
                    elapsed, resp = await run_prompt_once(client, query, 512, model_id)
                    if "error" not in resp:
                        timings.append(elapsed)
                    else:
                        timings.append(-1.0)  # Error sentinel

                valid = [t for t in timings if t >= 0]
                if valid:
                    p50 = sorted(valid)[len(valid) // 2]
                    p95 = sorted(valid)[min(len(valid) - 1, int(len(valid) * 0.95))]
                    min_t = min(valid)
                    max_t = max(valid)
                else:
                    p50 = p95 = min_t = max_t = -1.0

                all_timings[prompt_id] = timings
                print(f"  [{prompt_id}] p50={p50:.1f}s p95={p95:.1f}s min={min_t:.1f}s max={max_t:.1f}s")
                benchmark[prompt_id] = {
                    "timings": timings,
                    "p50": p50,
                    "p95": p95,
                    "min": min_t,
                    "max": max_t,
                    "errors": len([t for t in timings if t < 0]),
                }

        # GPU memory: read from training log or model size heuristic
        log_path = Path("logs/phase44_format_fix_training.log")
        peak_mem = "unknown"
        if log_path.exists():
            text = log_path.read_text()
            mem_matches = re.findall(r"Peak mem ([\d.]+) GB", text)
            if mem_matches:
                peak_mem = f"{max(float(m) for m in mem_matches):.3f} GB (from training log)"
        if peak_mem == "unknown":
            # Heuristic: 5.5 bits/weight × 30B params
            peak_mem = "~20 GB (estimated: 5.5 bits × 30B params)"

        model_size = "unknown"
        model_dir = Path(model_path)
        if model_dir.exists():
            total_bytes = sum(f.stat().st_size for f in model_dir.rglob("*.safetensors"))
            model_size = f"{total_bytes / 1e9:.1f} GB"

        print(f"  Peak GPU mem (training): {peak_mem}")
        print(f"  Model size on disk: {model_size}")

    finally:
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()

    return {
        "label": label,
        "model_path": model_path,
        "timings": benchmark,
        "peak_gpu_mem_training": peak_mem,
        "model_size_disk": model_size,
    }


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(
    phase44_results: dict,
    methodology: dict,
    consistency: dict,
    think_analysis: dict,
    perf_phase44: dict,
    perf_phase33b: dict | None,
) -> None:
    overall = phase44_results.get("overall_score", 0.0)
    verdict = phase44_results.get("verdict", "UNKNOWN")
    timestamp = phase44_results.get("timestamp", "unknown")

    lines = [
        "# Phase 44 Deep Dive Analysis",
        "",
        f"**Date:** {timestamp}",
        f"**Model:** `{phase44_results.get('model', DEFAULT_PHASE44_MODEL)}`",
        f"**Overall eval score:** {overall:.1%}",
        f"**Eval verdict:** {'✅ PASS' if verdict == 'PASS' else '❌ FAIL'}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
    ]

    # Executive summary
    issues = []
    if methodology["verdict"] != "CLEAN":
        issues.append(f"Methodology flags: {len(methodology['suspected_false_positives'])} FP, {len(methodology['suspected_false_negatives'])} FN")
    if consistency.get("verdict", "").startswith("FAIL"):
        issues.append(f"Consistency: {consistency['verdict']}")
    if think_analysis["verdict"] != "NO_THINK":
        issues.append(f"Think-mode: {think_analysis['verdict']}")

    if not issues and overall >= 0.80:
        lines.append("Phase 44 is a **PASS**. Eval methodology is sound. No major issues found.")
    elif not issues:
        lines.append(f"Phase 44 scored **{overall:.1%}** (below 80% target). Methodology appears sound.")
    else:
        lines.append(f"Phase 44 scored **{overall:.1%}**. Issues found:")
        for issue in issues:
            lines.append(f"- {issue}")

    lines += [
        "",
        "---",
        "",
        "## 1. Eval Results",
        "",
        "| Category | Score |",
        "|----------|-------|",
    ]

    for p in sorted(phase44_results.get("prompts", []), key=lambda x: x["category"]):
        pass  # will aggregate below

    from collections import defaultdict
    cat_scores: dict[str, list[float]] = defaultdict(list)
    for p in phase44_results.get("prompts", []):
        cat_scores[p["category"]].append(p["score"])

    for cat, scores in sorted(cat_scores.items()):
        avg = sum(scores) / len(scores)
        lines.append(f"| {cat} | {avg:.1%} ({sum(1 for s in scores if s >= 0.5)}/{len(scores)}) |")
    lines.append(f"| **Overall** | **{overall:.1%}** |")

    lines += [
        "",
        "### Per-Prompt Scores",
        "",
        "| ID | Score | EC | Time | Notes |",
        "|----|-------|-----|------|-------|",
    ]
    for p in phase44_results.get("prompts", []):
        ec = "✓" if p.get("has_execute_code") else "✗"
        elapsed = f"{p.get('elapsed', 0):.1f}s"
        snippet = (p.get("code_snippet", "") or "")[:60].replace("|", "│")
        lines.append(f"| {p['id']} | {p['score']:.2f} | {ec} | {elapsed} | `{snippet}` |")

    lines += [
        "",
        "---",
        "",
        "## 2. Methodology Audit",
        "",
        f"**Verdict:** {methodology['verdict']}",
        f"**Score distribution:** {methodology['score_distribution']}",
        "",
    ]

    if methodology["suspected_false_positives"]:
        lines.append(f"**Suspected false positives:** {', '.join(methodology['suspected_false_positives'])}")
    if methodology["suspected_false_negatives"]:
        lines.append(f"**Suspected false negatives:** {', '.join(methodology['suspected_false_negatives'])}")

    lines += [
        "",
        "### Per-Prompt Methodology Flags",
        "",
        "| ID | Score | EC | Flags |",
        "|----|-------|-----|-------|",
    ]
    for f in methodology["findings"]:
        flags = ", ".join(f["flags"]) if f["flags"] else "—"
        ec = "✓" if f.get("has_execute_code") else "✗"
        lines.append(f"| {f['id']} | {f['score']:.1f} | {ec} | {flags} |")

    lines += [
        "",
        "---",
        "",
        "## 3. Consistency Check",
        "",
        f"**Verdict:** {consistency.get('verdict', 'SKIPPED')}",
        "",
    ]

    results = consistency.get("results", {})
    if results:
        lines += ["| Prompt | Run 1 | Run 2 | Run 3 | Consistent |", "|--------|-------|-------|-------|------------|"]
        for pid, data in results.items():
            runs = data.get("runs", [])
            ok = "✓" if data.get("consistent") else "✗"
            r1 = f"{runs[0]:.1f}" if len(runs) > 0 else "?"
            r2 = f"{runs[1]:.1f}" if len(runs) > 1 else "?"
            r3 = f"{runs[2]:.1f}" if len(runs) > 2 else "?"
            lines.append(f"| {pid} | {r1} | {r2} | {r3} | {ok} |")

    lines += [
        "",
        "---",
        "",
        "## 4. Think-Mode Analysis",
        "",
        f"**Verdict:** {think_analysis.get('verdict', 'UNKNOWN')}",
        "",
    ]

    truncated = think_analysis.get("think_truncated_prompts", [])
    if truncated:
        lines.append(f"**Likely think-truncated (empty response):** {', '.join(truncated)}")
    zero_content = think_analysis.get("zero_with_content", [])
    if zero_content:
        lines.append(f"**Zero score but has content:** {', '.join(zero_content)}")

    think_test = think_analysis.get("think_test_without_stop", {})
    if think_test and "error" not in think_test:
        starts_think = think_test.get("starts_with_think", False)
        lines += [
            "",
            "**Think-mode probe** (prompt sent without `<think>` stop sequence):",
            f"- Starts with `<think>`: **{starts_think}**",
            f"- Content length: {think_test.get('length', 0)} chars",
            f"- Preview: `{(think_test.get('content_preview', '') or '')[:100]}`",
        ]

    lines += [
        "",
        "---",
        "",
        "## 5. Performance Benchmark",
        "",
        f"**Phase 44 model:** `{perf_phase44.get('model_path', DEFAULT_PHASE44_MODEL)}`",
        f"**Peak GPU mem (training):** {perf_phase44.get('peak_gpu_mem_training', 'unknown')}",
        f"**Model size on disk:** {perf_phase44.get('model_size_disk', 'unknown')}",
        "",
        "### Warm Query Timing (after model loaded)",
        "",
        "| Prompt | p50 | p95 | min | max | errors |",
        "|--------|-----|-----|-----|-----|--------|",
    ]

    phase44_timings = perf_phase44.get("timings", {})
    for pid, data in phase44_timings.items():
        p50 = f"{data['p50']:.1f}s" if data["p50"] >= 0 else "err"
        p95 = f"{data['p95']:.1f}s" if data["p95"] >= 0 else "err"
        mn = f"{data['min']:.1f}s" if data["min"] >= 0 else "err"
        mx = f"{data['max']:.1f}s" if data["max"] >= 0 else "err"
        errs = data.get("errors", 0)
        lines.append(f"| {pid} | {p50} | {p95} | {mn} | {mx} | {errs} |")

    if perf_phase33b and "timings" in perf_phase33b:
        lines += [
            "",
            f"### Comparison: Phase 33b Production (`{perf_phase33b.get('model_path', DEFAULT_PHASE33B_MODEL)}`)",
            "",
            "| Prompt | p50 (44) | p50 (33b) | Delta |",
            "|--------|----------|-----------|-------|",
        ]
        for pid, data33b in perf_phase33b.get("timings", {}).items():
            data44 = phase44_timings.get(pid, {})
            p50_44 = data44.get("p50", -1)
            p50_33b = data33b.get("p50", -1)
            if p50_44 >= 0 and p50_33b >= 0:
                delta = p50_44 - p50_33b
                delta_str = f"+{delta:.1f}s" if delta > 0 else f"{delta:.1f}s"
            else:
                delta_str = "n/a"
            p50_44_str = f"{p50_44:.1f}s" if p50_44 >= 0 else "err"
            p50_33b_str = f"{p50_33b:.1f}s" if p50_33b >= 0 else "err"
            lines.append(f"| {pid} | {p50_44_str} | {p50_33b_str} | {delta_str} |")

    lines += [
        "",
        "---",
        "",
        "## 6. Findings and Recommendations",
        "",
        f"Generated: {timestamp}",
    ]

    report_text = "\n".join(lines)
    Path(REPORT_PATH).write_text(report_text)
    print(f"\nReport written to: {REPORT_PATH}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--phase44-model", default=DEFAULT_PHASE44_MODEL)
    p.add_argument("--phase33b-model", default=DEFAULT_PHASE33B_MODEL)
    p.add_argument("--eval-json", default=EVAL_RESULTS_JSON)
    p.add_argument("--skip-consistency", action="store_true")
    p.add_argument("--skip-benchmark", action="store_true")
    args = p.parse_args()

    print("=" * 60)
    print("Phase 44 Deep Dive Analysis")
    print("=" * 60)

    # Load eval results
    eval_json_path = Path(args.eval_json)
    if not eval_json_path.exists():
        print(f"ERROR: Eval results not found: {eval_json_path}")
        print("  Run the eval first: uv run python scripts/run_phase33_direct_eval.py ...")
        return 1

    eval_results = json.loads(eval_json_path.read_text())
    print(f"Loaded eval results: {eval_results.get('overall_score', 0):.1%} from {eval_json_path}")

    # Section 1: Methodology audit (offline — uses the JSON)
    methodology = await section_methodology_audit(eval_results)

    # Section 2: Think-mode analysis (offline + one live server probe)
    think_analysis = await section_think_mode_analysis(eval_results)

    # Section 3: Consistency check (live server)
    if args.skip_consistency:
        consistency = {"verdict": "SKIPPED (--skip-consistency)"}
    else:
        consistency = await section_consistency_check()

    # Section 4: Performance benchmark — Phase 44
    if args.skip_benchmark:
        perf_phase44 = {"verdict": "SKIPPED", "timings": {}}
        perf_phase33b = None
    else:
        perf_phase44 = await section_performance_benchmark(args.phase44_model, "Phase 44")
        # Phase 33b comparison
        if Path(args.phase33b_model).exists():
            perf_phase33b = await section_performance_benchmark(args.phase33b_model, "Phase 33b")
        else:
            print(f"\n  Phase 33b model not found at {args.phase33b_model} — skipping comparison")
            perf_phase33b = None

    # Write report
    write_report(eval_results, methodology, consistency, think_analysis, perf_phase44, perf_phase33b)

    overall = eval_results.get("overall_score", 0.0)
    verdict = eval_results.get("verdict", "UNKNOWN")
    print(f"\n{'=' * 60}")
    print("Deep Dive Complete")
    print(f"  Eval overall: {overall:.1%} ({'PASS' if verdict == 'PASS' else 'FAIL'})")
    print(f"  Methodology: {methodology['verdict']}")
    print(f"  Think-mode:  {think_analysis['verdict']}")
    print(f"  Consistency: {consistency.get('verdict', 'SKIPPED')}")
    print(f"  Report: {REPORT_PATH}")
    print("=" * 60)

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
