# Record: Restore Tool Call Parsing to Eval Pipeline

## What We Did (Feb 12, 2026)

### The Problem

On Feb 8, we proved that `Qwen3-Coder-30B-A3B-Instruct-4bit` can call tools using XML format. We wrote `parse_tool_calls()` in `src/punie/models/mlx.py` to extract these from raw text.

On Feb 11, we deleted the entire MLX model layer (commit `a227ae9`) when shifting to `mlx_lm.server` as a subprocess. The tool call parser went with it. The overnight evaluation then found zero tool calls -- not because models can't call tools, but because nothing was parsing the text anymore.

### Step 1: Recover the parser into a standalone module

Recovered three functions from git history:

```bash
git show 80bb3df:src/punie/models/mlx.py
```

Created `src/punie/training/tool_call_parser.py` containing:
- `parse_tool_calls(text) -> tuple[str, list[dict]]` -- main entry point
- `_parse_xml_tool_call(xml_content)` -- parses `<function=name><parameter=key>value</parameter></function>`
- `_parse_xml_function_block(func_name, params_block)` -- handles broken XML missing opening `<tool_call>` tag

Key changes from original:
- Removed `ToolCallDict` TypedDict -- uses plain `dict[str, Any]`
- Removed all PydanticAI imports (no `ToolCallPart`, no `ModelResponse`)
- Pure function: text in, `(clean_text, list[dict])` out

### Step 2: Write tests

Created `tests/test_training_tool_call_parser.py` with 14 tests covering:
- JSON format: `<tool_call>{"name": "read_file", "arguments": {"path": "..."}}</tool_call>`
- XML format: `<tool_call><function=list_files><parameter=path>.</parameter></function></tool_call>`
- Broken XML (missing opening `<tool_call>` tag)
- Mixed text + tool calls
- No tool calls (returns empty list)
- Invalid JSON, missing name, missing function tag, empty string, nested JSON, multiline params

Tests ported from the deleted `tests/test_mlx_model.py` (also recovered via `git show 80bb3df`).

### Step 3: Integrate into eval_runner.py

Modified `src/punie/training/eval_runner.py`:
- Added import: `from punie.training.tool_call_parser import parse_tool_calls`
- After the existing structured-parts loop (lines 88-93), added a fallback:
  ```python
  if not tool_calls_list:
      _, parsed_calls = parse_tool_calls(result.output)
      tool_calls_list = [call["name"] for call in parsed_calls if "name" in call]
  ```
- Structured parts checked first (for cloud models), text parsing as fallback (for mlx_lm.server)

### Step 4: Update CLI defaults

Modified `src/punie/cli.py`:
- `punie train` default `--model`: changed from `Qwen2.5-Coder-1.5B-Instruct-4bit` to `Qwen3-Coder-30B-A3B-Instruct-4bit`
- `punie eval` default `--model`: same change

`server_config.py` has no hardcoded default -- it accepts `model_path` as required arg. No change needed.

### Step 5: Update documentation

- Added Phase 17 entry to `docs/research/training-journal.md`
- Marked cumulative results table as invalid (measurements were without parser)
- Deleted `OVERNIGHT_RESULTS.md` from project root (conclusions were wrong)

### Step 6: Verification

```bash
uv run pytest tests/test_training*.py -v      # 168 passed
uv run ruff check src/punie/training/          # All checks passed
uv run ty check src/punie/training/            # All checks passed
```

## Files Created/Modified

| File | Action |
|------|--------|
| `src/punie/training/tool_call_parser.py` | **Created** -- standalone parser module (145 lines) |
| `tests/test_training_tool_call_parser.py` | **Created** -- 14 tests (200 lines) |
| `src/punie/training/eval_runner.py` | **Modified** -- added import + fallback parsing (lines 18, 94-97) |
| `src/punie/cli.py` | **Modified** -- default model on lines 780 and 844 |
| `docs/research/training-journal.md` | **Modified** -- Phase 17 entry added |
| `OVERNIGHT_RESULTS.md` | **Deleted** |

**Git status:** All changes are unstaged and uncommitted.

## Where Models Live

Models are cached by HuggingFace at `~/.cache/huggingface/hub/`:

| Model | Path | Size |
|-------|------|------|
| Qwen2.5-Coder-1.5B-Instruct-4bit | `~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit/` | 839 MB |
| Qwen3-Coder-30B-A3B-Instruct-4bit | `~/.cache/huggingface/hub/models--mlx-community--Qwen3-Coder-30B-A3B-Instruct-4bit/` | 16 GB |

Trained adapters live in the project at `adapters/` (~220 MB total, 8 adapters). All trained against the 1.5B model, not the 30B.

No `~/.cache/mlx/` directory exists. MLX uses HuggingFace cache exclusively.

## To Reproduce From Scratch

Starting from commit `3acccd3` (before our changes), on the `local-model-training` branch:

```bash
# 1. Recover parser from git history
git show 80bb3df:src/punie/models/mlx.py > /tmp/old_mlx.py
# Extract parse_tool_calls(), _parse_xml_tool_call(), _parse_xml_function_block()
# Place in src/punie/training/tool_call_parser.py
# Remove ToolCallDict TypedDict, use dict[str, Any]
# Remove pydantic_ai imports, keep only json, re, typing

# 2. Write tests in tests/test_training_tool_call_parser.py
# Port from: git show 80bb3df:tests/test_mlx_model.py

# 3. Add fallback parsing to eval_runner.py
# Import parse_tool_calls at top
# After structured parts loop, add: if not tool_calls_list: parse from result.output

# 4. Update CLI defaults in src/punie/cli.py
# Change two occurrences of Qwen2.5-Coder-1.5B-Instruct-4bit
# to Qwen3-Coder-30B-A3B-Instruct-4bit (train and eval commands)

# 5. Delete OVERNIGHT_RESULTS.md

# 6. Verify
uv run pytest tests/test_training*.py -v
uv run ruff check src/punie/training/
uv run ty check src/punie/training/
```

## Problems Found During Review

### Problem 1 (CRITICAL): Training template format doesn't match parser

`src/punie/training/tool_calling_templates.py` line 43 produces:
```
I'll use the read_file tool.

```json
{
  "tool": "read_file",
  "arguments": {"path": "foo.py"}
}
```
```

The parser expects `<tool_call>{"name": ...}</tool_call>` or XML `<function=...>` tags.

**Two mismatches:**
1. **Format**: Code fences (` ```json ``` `) vs `<tool_call>` tags
2. **Key name**: `"tool"` vs `"name"`

A model fine-tuned on these templates will output tool calls the parser cannot recognize. All tool-calling eval prompts would score 0.0.

**Impact:** This doesn't affect today's work (we're using the base 30B model, which outputs `<tool_call>` natively). But it will matter when we resume LoRA training.

### Problem 2 (MODERATE): `test-tools` CLI command misses text-based tool calls

`src/punie/cli.py` lines 472-481 (the `punie test-tools` command) only checks structured message parts for `tool_name`. It does NOT fall back to `parse_tool_calls()` like the eval runner does. When testing a local model, it will incorrectly report "No tool calls detected" even when the model outputs `<tool_call>` blocks in text.

**Impact:** Misleading diagnostic output. Users running `punie test-tools` against a local model will think tool calling is broken when it's actually working.

### Problem 3 (LOW): Changes are uncommitted

All six file changes are unstaged. Need to commit before they can be evaluated with real models.

## Fixes Applied (Feb 12, 2026)

### Fix 1: Align training templates with parser format

**Modified:** `src/punie/training/tool_calling_templates.py`
- Line 43: Changed from ` ```json ``` ` format with `"tool"` key to `<tool_call>` XML format with `"name"` key
- Line 164: Same change in `create_multi_tool_example` function

**Modified:** `tests/test_training_tool_calling_templates.py`
- Updated assertions to check for `<tool_call>` tags and `"name":` key instead of ` ```json ``` ` and `"tool":`

### Fix 2: Add text parsing fallback to test-tools command

**Modified:** `src/punie/cli.py`
- Added import: `from punie.training.tool_call_parser import parse_tool_calls`
- After structured parts loop (line 481), added fallback parsing to detect tool calls in raw text output

Now `punie test-tools` correctly detects tool calls from both cloud models (structured parts) and local models (XML text).

### Verification

```bash
uv run pytest tests/test_training*.py -v      # All tests pass
uv run ruff check src/punie/training/ src/punie/cli.py
uv run ty check src/punie/training/ src/punie/cli.py
```
