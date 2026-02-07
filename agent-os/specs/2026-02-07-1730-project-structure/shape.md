# Shape: Project Structure Setup

## Scope

Bootstrap Punie from a minimal skeleton into a fully-featured Python project with:

- Complete package structure (`src/punie/`)
- Test infrastructure (pytest + Sybil)
- Quality tools (ruff, ty, pyright, pyrefly)
- Documentation (Sphinx + Furo + MyST)
- CI/CD (GitHub Actions)
- Developer convenience (Justfile recipes)

## Decisions

### Build System

**Choice:** `uv_build`

**Rationale:** Matches reference projects (svcs-di, tdom-svcs) and provides fast, reliable builds with uv integration.

### Test Framework

**Choice:** pytest with Sybil integration

**Rationale:**
- Function-based tests (standard `testing/function-based-tests`)
- Sybil for doctest integration (standard `testing/sybil-doctest`)
- Matches reference project patterns

### Documentation

**Choice:** Sphinx + Furo theme + MyST parser

**Rationale:**
- Clean, modern theme (Furo)
- Markdown support via MyST
- Matches reference projects
- GitHub Pages deployment ready

### Quality Tools

**Choices:**
- **ruff** — Linting and formatting
- **ty** — Fast type checking
- **pyright** — Additional type checking
- **pyrefly** — Code quality analysis

**Rationale:** Astral toolchain (ruff, ty) for speed; pyright/pyrefly for comprehensive analysis. Matches reference projects and `agent-verification` standard.

### CI/CD

**Choice:** GitHub Actions with custom composite action

**Rationale:**
- Reusable setup-python-uv action for consistency
- Free-threading test support
- Coverage reporting
- GitHub Pages deployment

### Python Version

**Choice:** Python 3.14.2t (free-threaded)

**Rationale:**
- Cutting edge Python version
- Free-threading support for future concurrency
- Matches svcs-di/tdom-svcs experimental approach

## Context

### Reference Projects

Both svcs-di and tdom-svcs follow identical conventions:

- Same dev dependencies
- Same pytest configuration
- Same Justfile recipes
- Same CI workflow structure
- Sybil for doctest integration

The only difference is tdom-svcs has a simpler Sybil setup without custom `_doctest_setup` since it doesn't need mock types for examples.

### Agent OS Integration

Punie already has:
- `agent-os/` directory with standards, skills, commands
- Roadmap at `agent-os/product/roadmap.md`
- Agent verification standard

This setup task is roadmap item 1.1 and enables all future development work.

### No Runtime Dependencies Yet

Punie starts with `dependencies = []` because:
- Core functionality not yet defined
- Dependencies will be added incrementally as features are built
- Focus is on project infrastructure first

## Out of Scope

- Actual Punie implementation code
- ACP protocol implementation
- PyCharm integration
- Runtime dependencies

## Success Criteria

1. `uv sync` completes successfully
2. `uv run pytest tests/` passes (minimal test)
3. `uv run pytest` passes (including Sybil doctests)
4. `astral:ruff` reports no issues
5. `astral:ty` reports no type errors
6. `uv run sphinx-build -W -b html docs docs/_build/html` succeeds
7. All 22 new files created, pyproject.toml rewritten
