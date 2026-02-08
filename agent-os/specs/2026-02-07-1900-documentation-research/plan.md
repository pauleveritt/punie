# Plan: Documentation with Deep Research (Roadmap 1.3)

## Context

Punie needs research documentation that the agent can refer to during later roadmap phases — Phase 3 (Pydantic AI Migration) and Phase 4 (ACP Integration). This creates three focused docs pages in `docs/research/`: an ACP SDK reference, a Pydantic AI reference, and an architecture overview showing how they bridge together for Punie.

## Spec Folder

`agent-os/specs/2026-02-07-1900-documentation-research/`

## Standards Applied

- **agent-verification** — Verify using Astral skills, not justfile recipes

## References

- ACP Python SDK: `~/PycharmProjects/python-acp-sdk/` (v0.7.1, `agent-client-protocol` on PyPI)
- Pydantic AI: `~/PycharmProjects/pydantic-ai/`

## Key Design Decisions

1. **Multi-page in `docs/research/`** — Keeps research docs separate from future user-facing docs (API docs, tutorials)
2. **Three pages** — `acp-sdk.md` (ACP reference), `pydantic-ai.md` (Pydantic AI reference), `architecture.md` (how they fit together)
3. **No runnable code blocks** — Use ` ```text ` or bare ` ``` ` for code snippets, since `docs/conftest.py` Sybil collects ` ```python ` blocks via `PythonCodeBlockParser`
4. **Agent-oriented** — Optimized for agent recall during later phases, not tutorials

## Tasks

### Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-07-1900-documentation-research/` with:
- `plan.md` — This plan
- `shape.md` — Scope, decisions, context
- `standards.md` — Full content of agent-verification standard
- `references.md` — Pointers to local checkouts with key files listed

### Task 2: Create `docs/research/acp-sdk.md`

ACP Python SDK reference with deep dive on Tool Implementation.

### Task 3: Create `docs/research/pydantic-ai.md`

Pydantic AI reference covering agent patterns and tooling.

### Task 4: Create `docs/research/architecture.md`

Architecture overview showing how Pydantic AI and ACP bridge together in Punie.

### Task 5: Update `docs/index.md`

Add toctree for research documentation.

### Task 6: Verify

1. `uv run sphinx-build -W -b html docs docs/_build/html` — docs build without warnings
2. `uv run pytest` — full suite passes
3. Use `astral:ruff` skill to check linting
4. Use `astral:ty` skill to check types

## Files Summary

**7 files to create:**
- `agent-os/specs/2026-02-07-1900-documentation-research/plan.md`
- `agent-os/specs/2026-02-07-1900-documentation-research/shape.md`
- `agent-os/specs/2026-02-07-1900-documentation-research/standards.md`
- `agent-os/specs/2026-02-07-1900-documentation-research/references.md`
- `docs/research/acp-sdk.md`
- `docs/research/pydantic-ai.md`
- `docs/research/architecture.md`

**1 file to modify:**
- `docs/index.md` — update toctree and replace placeholder
