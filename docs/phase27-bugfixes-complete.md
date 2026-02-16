# Phase 27 Data Bugfixes Complete

**Date:** 2026-02-16
**Status:** ✅ ALL FIXES VERIFIED

## Summary

Fixed 4 bugs introduced by the original `fix_phase27_data_issues.py` script while maintaining all 6 original fixes.

## Bugs Fixed

### 1. Quote Regex Corrupted Raw-Text Tool Responses ✅

**Problem:** `fix_quote_style()` ran on ALL `<tool_response>` content, corrupting HTML and code snippets.
- Example: `class="card"` → `class='card'` (invalid HTML)
- Impact: 3 confirmed corruptions at lines 98, 551, 638

**Solution:** Scoped quote conversion to structured Result objects only.

```python
RESULT_TYPES = {
    "GotoDefinitionResult", "FindReferencesResult", "TypeCheckResult",
    "RuffResult", "TestResult", "HoverResult", "DocumentSymbolsResult",
    "WorkspaceSymbolsResult", "GitLogResult", "GitStatusResult", "GitDiffResult",
}

# Only apply to structured objects, not raw text
if any(inner.startswith(rt + "(") for rt in RESULT_TYPES):
    content = fix_quote_style(content)
```

**Verification:** ✅ 0 corrupted raw-text responses found

---

### 2. Git Log Restoration Created Duplicates ✅

**Problem:** Matched by `assistant["content"]` (tool_call code). 3 pairs shared identical code → first match always won.
- Example: Two examples both call `git_log(".", 5)` but have different commit hashes
- Impact: 10 responses but only 7 unique (3 duplicates)

**Solution:** Match by user query instead (always unique).

```python
# Match by user query, not assistant code
orig_user = next((m for m in orig["messages"] if m["role"] == "user" and "<tool_response>" not in m.get("content", "")), None)
our_user = next((m for m in messages if m["role"] == "user" and "<tool_response>" not in m.get("content", "")), None)

if orig_user and our_user and orig_user["content"] == our_user["content"]:
    # Restore from original
```

**Verification:** ✅ All 10 git_log responses are unique

---

### 3. Author/Date Enrichment Had Zero Cross-Example Diversity ✅

**Problem:** `commit_index` always started at 0 → all examples began with "Alex Johnson"

**Solution:** Seed enrichment based on user query hash for diversity.

```python
def enrich_git_commits(content: str, seed: int = 0) -> str:
    commit_index = seed  # Start at different position per example
    ...

# In fix_example():
seed = hash(our_user["content"]) % 5 if our_user else 0
content = enrich_git_commits(content, seed=seed)
```

**Verification:** ✅ Found 5 different first authors:
- Emma Davis: 4 examples
- David Wilson: 2 examples
- Sarah Chen: 2 examples
- Alex Johnson: 1 example
- Michael Brown: 1 example

---

### 4. JSON-Format Tool Calls Conflicted with XML Training ✅

**Problem:** 4 examples used old `"name": "run_command"` JSON format instead of XML `<tool_call>`
- Conflicts with Code Mode training format
- Found at lines 168, 263, 296 + 1 more

**Solution:** Filter out JSON-format examples after deduplication.

```python
def has_json_format_tool_call(example: dict[str, Any]) -> bool:
    """Check if example uses old JSON-format tool calls."""
    for msg in example.get("messages", []):
        content = msg.get("content", "")
        if msg.get("role") == "assistant" and '"name":' in content and '"arguments":' in content:
            return True
    return False

# In process_file():
filtered = [ex for ex in deduplicated if not has_json_format_tool_call(ex)]
```

**Verification:** ✅ 0 JSON-format tool calls remain

---

## Original Fixes Still Intact ✅

All 6 original fixes verified:
1. ✅ 0 duplicates in train.jsonl
2. ✅ 0 duplicates in valid.jsonl
3. ✅ 0 train/valid leakage
4. ✅ 0 `role: "tool"` messages
5. ✅ Git log tool responses restored from original
6. ✅ Quote style fixed in structured Result objects

## Final Dataset Metrics

| Metric | Before Fix | After Fix | Change |
|--------|-----------|-----------|--------|
| train.jsonl lines | 1053 | 938 | -115 (111 dupes + 4 JSON) |
| valid.jsonl lines | 111 | 98 | -13 (4 dupes + 9 leakage) |
| **Total examples** | 1164 | **1036** | -128 |
| Unique git_log responses | 7 of 10 | **10 of 10** | Fixed ✅ |
| Raw-text corruptions | 3 | **0** | Fixed ✅ |
| Author diversity | 1 name | **5 names** | Fixed ✅ |
| JSON-format tool calls | 4 | **0** | Fixed ✅ |

## Verification Results

```
🔍 Verifying Phase 27 data fixes...

Git log uniqueness: ✅ All 10 git_log responses are unique
Quote corruption: ✅ No quote corruption in raw-text tool responses
Author diversity: ✅ Found 5 different first authors across git_log examples
JSON-format removal: ✅ No JSON-format tool calls found
Original fixes intact: ✅ All 6 original fixes still in place

✅ All checks passed!
```

## Files Modified

1. **scripts/fix_phase27_data_issues.py** - Fixed 4 bugs
   - Added `RESULT_TYPES` set for quote scoping
   - Added `has_json_format_tool_call()` detector
   - Changed git_log matching to use user query
   - Added `seed` parameter to `enrich_git_commits()`
   - Added JSON-format filtering step

2. **data/phase27_cleaned/train.jsonl** - Restored and re-processed
3. **data/phase27_cleaned/valid.jsonl** - Restored and re-processed

## New Verification Tools

- **scripts/verify_phase27_fixes.py** - Comprehensive verification suite
  - Checks git_log uniqueness
  - Detects quote corruption
  - Verifies author diversity
  - Confirms JSON-format removal
  - Validates original fixes

## Next Steps

1. ✅ All tests passing (718 tests)
2. ✅ Data verified clean
3. ✅ Ready for Phase 27 training

The dataset is now production-ready with all bugs fixed and verified.
