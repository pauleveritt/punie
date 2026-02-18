# Phase 33 Shaping Notes

## Scope Decision

**In scope:**
- Generate ~150 domain tool examples (Phase 32's 12 new tools)
- Merge with phase28_merged foundation (1126 examples)
- Update LoRAConfig + train_runner for new training knobs
- Create cosine LR YAML config
- Expand eval suite to 26 tools

**Out of scope:**
- Rebuilding Phase 22-27 data (phase28_merged already subsumes it)
- Cross-tool workflows for domain tools (Phase 34)
- Flywheel data capture (separate Phase 35+ effort)
- Multi-project support (Phase 31)

## Key Design Decisions

### Why phase28_merged as foundation?

phase28_merged (1126 examples) is the highest-quality dataset we have. It already covers:
- Text tools (read/write/run_command) with diverse queries
- Validation tools (typecheck, ruff, pytest) with multi-step workflows
- LSP navigation (goto_def, find_refs, hover, symbols)
- Git tools (git_status, git_diff, git_log)
- Cross-tool workflows

Adding 150 domain examples gives ~12% new content while keeping existing knowledge.

### Why 12-13 examples per tool?

At 150 total across 12 tools: 150/12 ≈ 12.5 examples/tool. This is enough to teach the model the tool signature and typical response format without overfitting. Compare to Phase 27 where 10-15 examples/tool achieved 100% accuracy.

### Why mask_prompt?

Training on completions-only (not the system+user turns) focuses the loss signal on what the model needs to learn — the tool call syntax and response format. At 1276 total examples, this makes each update more signal-rich.

### Why grad_accumulation_steps=4?

With batch_size=1 and gradient accumulation of 4, effective batch = 4. This improves training stability compared to raw batch_size=4 (which exceeds memory on M-series Macs with 30B model).

### CST tool naming convention

Training examples use `_direct` suffix for CST tools (matching PUNIE_DIRECT_INSTRUCTIONS):
- `cst_find_pattern_direct(file, pattern)`
- `cst_rename_direct(file, old_name, new_name)`
- `cst_add_import_direct(file, import_stmt)`

Domain validator examples also use `_direct` suffix.

## Data Quality Standards

Each example must:
1. Have a realistic user query (not "run tool X")
2. Show the model calling the tool with proper arguments
3. Parse and present the structured result meaningfully
4. Be self-contained (no dependencies on previous turns)
