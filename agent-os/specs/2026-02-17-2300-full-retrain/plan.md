# Phase 33: Full Retrain on Complete Dataset

## Context

Phase 32 (Domain Tools + LibCST) is complete — Punie now has 26 tools across 4 categories. Phase 33 is a one-time retrain consolidating ALL tool categories into a single ~1200-example dataset, giving the model mastery over text, validation, LSP, and domain tools together.

**Key discovery:** `data/phase28_merged/` (1126 examples, `{"messages": [...]}` format) already subsumes Phase 22-27 data. We build on it rather than rebuilding from scratch. We need ~150 new domain tool examples for Phase 32 tools + data validation + training with new knobs.

## Tool Categories (26 total)

| Category | Tools | Count |
|----------|-------|-------|
| Text | read_file, write_file, run_command | 3 |
| Validation | typecheck, ruff_check, pytest_run | 3 |
| LSP | goto_definition, find_references, hover, document_symbols, workspace_symbols | 5 |
| Git | git_status, git_diff, git_log | 3 |
| CST Code | cst_find_pattern, cst_rename, cst_add_import | 3 |
| Domain (tdom) | validate_component, check_render_tree, validate_escape_context | 3 |
| Domain (svcs) | validate_service_registration, check_dependency_graph, validate_injection_site | 3 |
| Domain (tdom-svcs) | validate_middleware_chain, check_di_template_binding, validate_route_pattern | 3 |

## Dataset Plan

| Source | Train | Valid | Total |
|--------|-------|-------|-------|
| phase28_merged (foundation) | 1019 | 107 | 1126 |
| phase32_domain_tools (new) | ~135 | ~15 | ~150 |
| **phase33_merged (output)** | **~1154** | **~122** | **~1276** |

## Training Knobs

- `--iters 800` (more iterations for larger dataset)
- `--grad-accumulation-steps 4` (effective batch = 4)
- `--mask-prompt` (train only on completions)
- `--lora-scale 20.0` (default, explicit)
- LR: 1e-4 with cosine decay (via YAML config)

## Success Criteria

- ≥80% accuracy on 26-query eval suite
- All tool categories represented in successful responses
- Multi-tool workflow succeeds
- Average response time <5s

## Status

Implemented 2026-02-17. Data generation, merge, and training configuration complete.
