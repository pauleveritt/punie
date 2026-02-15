# Standards Applied

## agent-verification

**Standard:** `agent-os/standards/agent-verification.md`

**Application:** This audit verifies completed work without re-running it.

**Verification method:**
1. **Artifact existence** — Check for files, directories, models
2. **Memory cross-reference** — Match `MEMORY.md` claims against codebase
3. **Test evidence** — Confirm validation scripts exist and were run
4. **Documentation audit** — Verify diary entries, specs, and roadmap entries

**Decision criteria:**
- If artifacts exist AND memory documents completion AND tests pass → Mark complete
- If any element missing → Investigate further or mark incomplete

**Outcome:** All 8 Phase 23 tasks passed verification.

## roadmap-format

**Standard:** Roadmap uses checkbox format for tracking task completion.

**Format conventions:**
- `[ ]` — Task not started or in progress
- `[x]` — Task complete with evidence

**Status indicators:**
- `🚧 In Progress` — Active development
- `✅ Complete` — All tasks checked off
- `📋 Planned` — Not yet started

**Evidence requirements:**
Each checked task should include:
- Brief description of what was done
- File references (paths to code, tests, docs)
- Metrics or results (if applicable)

**Phase 23 application:**
- Updated all 8 checkboxes from `[ ]` to `[x]`
- Changed status from `🚧 In Progress` to `✅ Complete`
- Added evidence notes inline (file paths, model metrics)
- Added completion summary referencing Phase 26

## Documentation Standards

**Spec structure:** Each spec directory contains:
- `plan.md` — The implementation plan
- `shape.md` — Problem analysis and decisions
- `standards.md` — Standards applied (this file)
- `references.md` — Pointers to evidence

**Memory updates:** When completing phases:
1. Update `MEMORY.md` with phase summary
2. Update roadmap checkboxes
3. Create spec documentation if needed
4. Write diary entry for significant findings

**Audit trail:** Link from roadmap → spec → memory → code.

Example for Phase 23:
- Roadmap: `agent-os/product/roadmap.md` lines 1362-1449
- Spec: `agent-os/specs/2026-02-15-phase23-completion-audit/`
- Memory: `MEMORY.md` "Phase 23" section
- Code: `src/punie/agent/typed_tools.py`, `fused_model_qwen3_phase23_ty_5bit/`
- Diary: `docs/diary/2026-02-15-phase23-task11-validation.md`
