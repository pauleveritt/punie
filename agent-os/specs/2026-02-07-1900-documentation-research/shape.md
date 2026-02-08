# Shape: Documentation with Deep Research

## Scope

Create comprehensive research documentation for Punie's future phases (Pydantic AI Migration and ACP Integration). This documentation serves as a reference for the agent during implementation, not as user-facing tutorials.

## What's Included

1. **ACP SDK Reference** (`docs/research/acp-sdk.md`)
   - Complete protocol overview (Agent and Client interfaces)
   - Deep dive on Tool Implementation (the critical integration point)
   - Complete type hierarchy for tool calls
   - Tool call lifecycle with examples
   - Helper functions and contrib utilities
   - Package structure

2. **Pydantic AI Reference** (`docs/research/pydantic-ai.md`)
   - Agent class and run modes
   - Tools and Toolsets (AbstractToolset is the ACP bridge)
   - Dependencies and type-safe DI
   - Structured output
   - Multi-agent patterns
   - Protocol support

3. **Architecture Overview** (`docs/research/architecture.md`)
   - How Pydantic AI and ACP bridge together in Punie
   - Data flow: PyCharm -> ACP -> Punie -> Pydantic AI -> LLM -> tools -> ACP -> PyCharm
   - The Tool Bridge pattern (critical integration)
   - Tool mapping table
   - Roadmap phase mapping

4. **Spec Documentation** (`agent-os/specs/2026-02-07-1900-documentation-research/`)
   - Plan, shape, standards, references
   - Documents the research process and decisions

## What's Not Included

- User-facing tutorials (future work)
- API documentation (generated from docstrings, future work)
- Runnable code examples (would be collected by Sybil)
- Installation guides (covered in README.md)

## Key Decisions

### Decision 1: Research Docs in Separate Directory

**Choice:** Create `docs/research/` subdirectory

**Rationale:**
- Keeps research docs separate from future user-facing docs
- Clear signal that these are reference materials, not tutorials
- Allows for future expansion (API docs, tutorials) without mixing concerns

**Alternatives Considered:**
- Single-page reference — Would be too long, hard to navigate
- Mix with user docs — Would confuse audience (agent vs. user)

### Decision 2: Deep Dive on Tool Implementation

**Choice:** Make "Tool Implementation" section the largest in `acp-sdk.md`

**Rationale:**
- Tool calls are the critical integration point between Pydantic AI and ACP
- Understanding the ephemeral, notification-based model is essential
- The lifecycle (ToolCallStart -> request_permission -> ToolCallProgress) is non-obvious
- Helpers and contrib utilities need full documentation

**Alternatives Considered:**
- Equal weight to all sections — Would miss the criticality of tools
- Separate tool implementation page — Would fragment the reference

### Decision 3: No Runnable Code Blocks

**Choice:** Use ` ```text ` or bare ` ``` ` for code snippets

**Rationale:**
- `docs/conftest.py` configures Sybil to collect ` ```python ` blocks via `PythonCodeBlockParser`
- Research docs contain snippets from external codebases (ACP SDK, Pydantic AI)
- These snippets are not meant to run in Punie's context
- Avoids test failures from non-executable reference code

**Alternatives Considered:**
- Use `# doctest: +SKIP` — Too noisy, still implies intent to run
- Configure Sybil to skip research docs — Loses consistency with main docs

### Decision 4: Architecture Page First in TOC

**Choice:** Order as architecture -> ACP SDK -> Pydantic AI

**Rationale:**
- Architecture page provides context for the two reference pages
- Shows how the pieces fit together before diving into details
- Follows "big picture first" documentation pattern

**Alternatives Considered:**
- Alphabetical order — Less pedagogically sound
- SDK first — Misses the "why" before the "what"

## Context

### Why Now?

Roadmap 1.3 focuses on documentation. Before implementing Pydantic AI migration (Phase 3) and ACP integration (Phase 4), we need deep research on both technologies.

### Why This Approach?

Research docs serve as:
1. **Agent memory** — Reference during future implementation phases
2. **Design validation** — Ensures we understand the integration points
3. **Knowledge capture** — Documents insights from exploring ACP SDK and Pydantic AI codebases

### Integration Points

- **ACP SDK v0.7.1** — Local checkout at `~/PycharmProjects/python-acp-sdk/`
- **Pydantic AI** — Local checkout at `~/PycharmProjects/pydantic-ai/`
- **Sphinx + MyST** — Existing docs infrastructure with Furo theme
- **Sybil** — Configured to collect Python code blocks (hence our "no runnable code" decision)

## Success Criteria

1. Documentation builds without warnings (`uv run sphinx-build -W`)
2. Tests pass (no runnable code blocks collected)
3. Ruff and ty verification pass
4. Architecture page clearly explains the Pydantic AI ↔ ACP bridge
5. ACP SDK tool implementation section provides complete reference for future work
6. Pydantic AI page covers AbstractToolset (the bridge point)
