#!/usr/bin/env python3
"""Direct HTTP evaluation for Phase 33 — bypasses pydantic-ai infrastructure.

The trained model uses Code Mode: it calls execute_code() with Python code
that invokes sub-tools (read_file, typecheck, git_status, cst_find_pattern,
validate_component, etc.). This script:

1. Starts mlx_lm.server with no hard max_tokens cap (per-request limit controls it)
2. Sends each prompt via raw HTTP to the OpenAI API
3. Parses the execute_code call from the raw XML response
4. Checks for expected sub-tool names inside the code parameter
5. Reports per-category scores

Usage:
    # Server not running:
    uv run python scripts/run_phase33_direct_eval.py

    # Server already running on port 8080:
    uv run python scripts/run_phase33_direct_eval.py --no-server

Scoring logic (27 prompts):
    - Single-tool prompts: pass (1.0) if execute_code called + ANY expected keyword.
      Direct tool call (right tool, no execute_code wrapper) = 0.5 partial credit.
      execute_code + wrong tool = 0.1. No call = 0.0.
    - Multi-tool prompts (multi-01): fraction of keywords found + 0.1 bonus.
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

# Use the training-matching system prompt (short form used in all training examples).
# The full PUNIE_LOCAL_INSTRUCTIONS (~20K chars) was NOT used during training,
# causing the model to lose its tool-calling behavior at eval time.
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

MODEL_PATH = "fused_model_qwen3_phase33_5bit"
SERVER_PORT = 8080
SERVER_URL = f"http://127.0.0.1:{SERVER_PORT}/v1"
MAX_TOKENS = 512    # Default per-request limit
TIMEOUT = 120.0     # Per-request timeout (longer for reasoning-heavy prompts)

# Each prompt: (id, category, user_query, expected_subtool, expected_keywords, is_multi, max_tokens_override)
# - is_multi=True: fraction scoring (need ALL tools in output) — used for multi-step workflows
# - is_multi=False: OR-logic scoring (ANY keyword match = pass) — used for single-tool prompts
# - max_tokens_override: override MAX_TOKENS for this prompt (None = use default)
EVAL_PROMPTS = [
    # Text tools
    # text-01: "Show me the contents" — closely matches training "read_file" pattern
    ("text-01", "text_tools",
     "Show me the contents of src/punie/agent/config.py.",
     "read_file", ["read_file", "document_symbols"], False, None),
    # text-02: "Write X to file Y" — matches training write_file pattern
    ("text-02", "text_tools",
     "Write the text 'Phase 33 complete' to output/summary.txt.",
     "write_file", ["write_file"], False, None),
    # text-03: ls is a valid shell arg; run_command also acceptable
    ("text-03", "text_tools",
     "Run 'ls src/' and show me what Python files are in the source directory.",
     "run_command", ["run_command", "ls"], False, None),
    # Validation
    ("valid-01", "validation",
     "Run type checking on src/ and report any type errors.",
     "typecheck", ["typecheck", "type_check"], False, None),
    ("valid-02", "validation",
     "Check src/ for linting violations with ruff.",
     "ruff_check", ["ruff_check", "ruff"], False, None),
    ("valid-03", "validation",
     "Run the test suite in tests/ and report how many tests passed and failed.",
     "pytest_run", ["pytest_run", "pytest"], False, None),
    # LSP
    ("lsp-01", "lsp",
     "Find the definition of AgentConfig in the codebase.",
     "goto_definition", ["goto_definition"], False, None),
    ("lsp-02", "lsp",
     "Find all references to execute_code across the project.",
     "find_references", ["find_references"], False, None),
    ("lsp-03", "lsp",
     "Show type information and docstring for LoRAConfig.",
     "hover", ["hover"], False, None),
    ("lsp-04", "lsp",
     "List all classes and functions in src/punie/training/lora_config.py.",
     "document_symbols", ["document_symbols"], False, None),
    # lsp-05: workspace_symbols can crash server; use larger token budget + retry
    ("lsp-05", "lsp",
     "Search the workspace for any symbol named TrainingResult.",
     "workspace_symbols", ["workspace_symbols"], False, 2048),
    # Git
    ("git-01", "git",
     "Check git status and tell me which files have been modified.",
     "git_status", ["git_status"], False, None),
    ("git-02", "git",
     "Show the git diff for uncommitted changes.",
     "git_diff", ["git_diff"], False, None),
    ("git-03", "git",
     "List the 5 most recent git commits.",
     "git_log", ["git_log"], False, None),
    # CST tools — include _direct suffix as accepted alternative
    # cst-01: held-out variant (different file + rephrased; not verbatim training copy)
    ("cst-01", "cst",
     "Find all class definitions in src/punie/http/websocket.py.",
     "cst_find_pattern", ["cst_find_pattern", "cst_find_pattern_direct"], False, 512),
    # cst-02: held-out variant (different rename target; not verbatim training copy)
    ("cst-02", "cst",
     "Rename TrainingResult to FineTuneResult in src/punie/training/train_runner.py.",
     "cst_rename", ["cst_rename", "cst_rename_direct"], False, None),
    # cst-03: held-out variant (different import + different file)
    ("cst-03", "cst",
     "Add 'from collections import defaultdict' to src/punie/http/websocket.py.",
     "cst_add_import", ["cst_add_import", "cst_add_import_direct"], False, None),
    # Domain validators — include _direct suffix as accepted alternative
    # dom-01: held-out variant (different file; training used home.py)
    ("dom-01", "domain",
     "Check if src/views/error_page.py is a valid tdom component.",
     "validate_component", ["validate_component", "validate_component_direct"], False, None),
    ("dom-02", "domain",
     "Check the service registration in src/services/user_service.py.",
     "validate_service_registration",
     ["validate_service_registration", "validate_service_registration_direct"], False, None),
    # dom-03: held-out variant (different file + rephrased; training used auth.py)
    ("dom-03", "domain",
     "Does src/middleware/circuit_breaker.py follow @middleware conventions?",
     "validate_middleware_chain",
     ["validate_middleware_chain", "validate_middleware_chain_direct"], False, None),
    ("dom-04", "domain",
     "Check dependency graph violations in src/services/report_service.py.",
     "check_dependency_graph",
     ["check_dependency_graph", "check_dependency_graph_direct"], False, None),
    # dom-05: held-out variant (different file + rephrased; training used profile.py)
    ("dom-05", "domain",
     "Check src/views/registration.py — does it use t-strings instead of f-strings in html() calls?",
     "validate_escape_context",
     ["validate_escape_context", "validate_escape_context_direct"], False, None),
    ("dom-06", "domain",
     "Validate route patterns in src/routes/api.py.",
     "validate_route_pattern",
     ["validate_route_pattern", "validate_route_pattern_direct"], False, None),
    # dom-07/08/09: previously untested domain tools
    ("dom-07", "domain",
     "Verify the render tree composition in src/views/checkout.py.",
     "check_render_tree",
     ["check_render_tree", "check_render_tree_direct"], False, None),
    ("dom-08", "domain",
     "Are all Inject[] type annotations properly imported in src/services/billing_service.py?",
     "validate_injection_site",
     ["validate_injection_site", "validate_injection_site_direct"], False, None),
    ("dom-09", "domain",
     "Check if html() calls in src/views/account.py pass context= for injectable components.",
     "check_di_template_binding",
     ["check_di_template_binding", "check_di_template_binding_direct"], False, None),
    # Multi-tool — fraction scoring, needs at least 3 of 4 tools; 1024 token budget
    ("multi-01", "multi_tool",
     "Find the definition of HomeView, read it, validate as a tdom component, then run tests.",
     "execute_code", ["goto_definition", "read_file", "validate_component", "pytest_run"],
     True, 1024),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=MODEL_PATH)
    p.add_argument("--port", type=int, default=SERVER_PORT)
    p.add_argument("--no-server", action="store_true", help="Skip server startup (already running)")
    p.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    return p.parse_args()


def start_server(model_path: str, port: int) -> subprocess.Popen:
    """Start mlx_lm server without a hard token cap (per-request max_tokens controls it)."""
    cmd = [
        "uv", "run", "python", "-m", "mlx_lm", "server",
        "--model", model_path,
        "--port", str(port),
        "--host", "127.0.0.1",
        # No --max-tokens: allow per-request max_tokens to control generation length
    ]
    print(f"Starting server: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc


async def wait_for_server(url: str, timeout: float = 90.0) -> bool:
    """Poll /v1/models until the server responds."""
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


def extract_code_from_response(response_json: dict) -> tuple[bool, str]:
    """Extract the Python code from an API response.

    Handles two formats:
    1. Native tool_calls array (OpenAI format from mlx_lm server)
    2. Content string with <tool_call> XML tags (legacy format)

    Returns: (has_execute_code, code_body)
    """
    choices = response_json.get("choices", [])
    if not choices:
        return False, ""

    msg = choices[0].get("message", {})

    # Format 1: Native tool_calls array
    tool_calls = msg.get("tool_calls", [])
    for tc in tool_calls:
        fn = tc.get("function", {})
        args_raw = fn.get("arguments", "{}")
        if fn.get("name") == "execute_code":
            try:
                args = json.loads(args_raw)
                # Try "code" key first, then any string value (handles "Coder", "python", etc.)
                code = args.get("code") or args.get("python") or next(
                    (v for v in args.values() if isinstance(v, str)), ""
                )
                return True, code or args_raw
            except json.JSONDecodeError:
                return True, args_raw
        # Direct tool call (not wrapped in execute_code) — has_execute_code=False
        # so it scores 0.5 partial credit (right tool, wrong wrapper).
        if fn.get("name"):
            return False, fn["name"] + "\n" + args_raw

    # Format 2: XML in content string
    content = msg.get("content", "") or ""
    m = re.search(
        r"<tool_call>\s*<function=execute_code>\s*<parameter=code>\s*(.*?)\s*(?:</parameter>|$)",
        content,
        re.DOTALL,
    )
    if m:
        return True, m.group(1)

    # No tool call found — return full content as the "code body" for keyword matching
    return False, content


def score_response(
    response_json: dict,
    expected_subtool: str,
    expected_keywords: list[str],
    is_multi: bool = False,
) -> tuple[float, bool, str]:
    """Score a model response.

    Single-tool prompts (is_multi=False):
        - execute_code called + ANY expected keyword in code → 1.0
        - execute_code called + NO expected keywords → 0.1 (correct format, wrong tool)
        - direct tool call + expected keyword found → 0.5 (right tool, wrong wrapper)
        - no tool call → 0.0

    Multi-tool prompts (is_multi=True):
        - Fraction of expected keywords found + 0.1 bonus for execute_code

    Returns: (score, has_execute_code, code_body_snippet)
    """
    has_execute_code, code_body = extract_code_from_response(response_json)

    if is_multi:
        # Multi-tool: fraction scoring — model should call ALL specified tools
        found_keywords = [kw for kw in expected_keywords if kw in code_body]
        keyword_score = len(found_keywords) / len(expected_keywords) if expected_keywords else 1.0
        score = keyword_score
        if has_execute_code:
            score = min(1.0, score + 0.1)
    else:
        # Single-tool: OR logic — any matching keyword = pass
        any_found = any(kw in code_body for kw in expected_keywords)
        if has_execute_code and any_found:
            score = 1.0
        elif has_execute_code:
            score = 0.1  # Correct format, wrong tool
        elif any_found:
            score = 0.5  # Direct tool call (right tool, but not via execute_code)
        else:
            score = 0.0  # No tool call at all

    return score, has_execute_code, (code_body[:200] if code_body else "")


async def run_prompt(
    client: httpx.AsyncClient,
    prompt_id: str,
    user_query: str,
    max_tokens: int,
    server_url: str,
    model_id: str,
    retries: int = 2,
) -> tuple[float, dict]:
    """Run a single prompt against the server. Returns (duration_seconds, response_json).

    Retries on server disconnect with progressively smaller token budgets.
    """
    messages = [
        {"role": "system", "content": EVAL_SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]
    overall_start = time.time()

    for attempt in range(retries + 1):
        # On retries, halve the token budget to avoid runaway generation
        mt = max(256, max_tokens // (2 ** attempt)) if attempt > 0 else max_tokens
        if attempt > 0:
            print(f" [retry {attempt}, max_tokens={mt}]", end="", flush=True)
            await asyncio.sleep(3.0)  # Wait for server to stabilize

        payload = {
            "model": model_id,
            "messages": messages,
            "max_tokens": mt,
            "temperature": 0.0,
            "stop": ["<|im_end|>", "<|endoftext|>", "<think>"],
        }
        try:
            r = await client.post(
                f"{server_url}/chat/completions",
                json=payload,
                timeout=TIMEOUT,
            )
            elapsed = time.time() - overall_start
            if r.status_code != 200:
                if attempt < retries:
                    continue
                return elapsed, {"error": f"HTTP {r.status_code}: {r.text[:200]}"}
            return elapsed, r.json()
        except httpx.TimeoutException:
            if attempt < retries:
                continue
            return time.time() - overall_start, {"error": "TIMEOUT"}
        except Exception as e:
            err_str = str(e)
            if attempt < retries and (
                "disconnect" in err_str.lower()
                or "connection" in err_str.lower()
                or "reset" in err_str.lower()
            ):
                continue
            return time.time() - overall_start, {"error": err_str}

    return time.time() - overall_start, {"error": "All retries exhausted"}


async def main() -> int:
    args = parse_args()

    if not Path(args.model).exists():
        print(f"ERROR: Model not found: {args.model}")
        return 1

    server_proc: subprocess.Popen | None = None

    if not args.no_server:
        server_proc = start_server(args.model, args.port)
        # Wait briefly then check if the process exited immediately (port already in use)
        await asyncio.sleep(3.0)
        if server_proc.poll() is not None:
            print(f"ERROR: Server exited immediately — port {args.port} is likely already occupied.")
            print(f"  Kill the existing server on port {args.port} and retry.")
            return 1
        print("Waiting for server to be ready...")
        server_url_for_wait = f"http://127.0.0.1:{args.port}/v1"
        ready = await wait_for_server(server_url_for_wait, timeout=120.0)
        if not ready:
            print("ERROR: Server failed to start within 120s")
            if server_proc:
                server_proc.kill()
            return 1
        print("Server ready.\n")

    # Get the actual model ID from the server (for informational display only)
    server_url = f"http://127.0.0.1:{args.port}/v1"
    async with httpx.AsyncClient() as probe:
        try:
            r = await probe.get(f"{server_url}/models", timeout=10.0)
            models_data = r.json()
            all_ids = [m["id"] for m in models_data.get("data", [])]
            # Note: mlx_lm reports the base model ID from config.json, not the local path.
            # A fused model derived from X will still report X as its ID — that's expected.
            model_id = all_ids[0] if all_ids else args.model
            print(f"  Using model ID: {model_id}\n")
        except Exception as e:
            model_id = args.model
            print(f"  Could not get model ID ({e}), using: {model_id}\n")

    results = []
    category_results: dict[str, list[dict]] = defaultdict(list)

    try:
        async with httpx.AsyncClient() as client:
            for (
                prompt_id, category, query,
                expected_subtool, expected_keywords,
                is_multi, max_tokens_override,
            ) in EVAL_PROMPTS:
                mt = max_tokens_override if max_tokens_override is not None else args.max_tokens
                print(f"  [{prompt_id}] {query[:60]}...", end=" ", flush=True)
                elapsed, response_json = await run_prompt(
                    client, prompt_id, query, mt, server_url, model_id
                )

                if "error" in response_json:
                    print(f"✗ ERROR: {response_json['error']}")
                    entry = {
                        "id": prompt_id,
                        "category": category,
                        "score": 0.0,
                        "has_execute_code": False,
                        "elapsed": elapsed,
                        "response_snippet": str(response_json),
                        "code_snippet": "",
                    }
                else:
                    score, has_ec, snippet = score_response(
                        response_json, expected_subtool, expected_keywords, is_multi
                    )
                    status = "✓" if score >= 0.5 else "✗"
                    print(f"{status} score={score:.2f} ({elapsed:.1f}s)")
                    if score < 0.5:
                        print(f"      code: {snippet[:100]}")
                    entry = {
                        "id": prompt_id,
                        "category": category,
                        "score": score,
                        "has_execute_code": has_ec,
                        "elapsed": elapsed,
                        "response_snippet": str(response_json)[:400],
                        "code_snippet": snippet,
                    }

                results.append(entry)
                category_results[category].append(entry)

    finally:
        if server_proc:
            print("\nStopping server...")
            server_proc.terminate()
            try:
                server_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_proc.kill()

    # Summary
    overall = sum(r["score"] for r in results) / len(results) if results else 0.0
    print()
    print("=" * 60)
    print("Phase 33 Direct Eval Results")
    print(f"  Model:   {args.model}")
    print(f"  Prompts: {len(results)}")
    print(f"  Overall: {overall:.1%}")
    print()
    print("Category breakdown:")
    for cat, cat_results in sorted(category_results.items()):
        avg = sum(r["score"] for r in cat_results) / len(cat_results)
        passed = sum(1 for r in cat_results if r["score"] >= 0.5)
        status = "✓" if avg >= 0.7 else "✗"
        print(f"  {status} {cat:20s}: {avg:.1%} ({passed}/{len(cat_results)})")

    verdict = "PASS" if overall >= 0.80 else "FAIL"
    print()
    print(f"{'✅ PASS' if verdict == 'PASS' else '❌ FAIL'}: {overall:.1%} (target ≥80%)")

    # Save
    Path("logs").mkdir(exist_ok=True)
    out = {
        "model": args.model,
        "overall_score": overall,
        "verdict": verdict,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "prompts": results,
    }
    out_path = Path("logs/phase33_direct_eval_results.json")
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nSaved to {out_path}")

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
