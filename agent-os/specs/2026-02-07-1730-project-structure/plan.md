# Plan: Set Up Project Structure (Roadmap 1.1)

## Context

Punie is a bare project with only a minimal `pyproject.toml`, `README.md`, Agent OS infrastructure, and PyCharm config. Task 1.1 from the roadmap is to set up the full project structure matching the conventions of svcs-di and tdom-svcs. Success means a working `uv run pytest` with ruff/ty configured and all scaffolding in place.

## Spec Folder

`agent-os/specs/2026-02-07-1730-project-structure/`

## Standards Applied

- **agent-verification** — Verify using Astral skills, not justfile recipes
- **testing/function-based-tests** — Tests as functions, not classes
- **testing/sybil-doctest** — Sybil for README and docstring testing

## Reference Projects

- `/Users/pauleveritt/projects/t-strings/svcs-di/` — pyproject.toml, Justfile, conftest.py, CI workflows
- `/Users/pauleveritt/projects/t-strings/tdom-svcs/` — same conventions, simpler Sybil pattern

## Tasks

### Task 1: Save Spec Documentation

Create `agent-os/specs/2026-02-07-1730-project-structure/` with:
- `plan.md` — This plan
- `shape.md` — Scope, decisions, context
- `standards.md` — Full content of 3 applied standards
- `references.md` — Pointers to svcs-di and tdom-svcs

### Task 2: Create Root Configuration Files

| File | Content |
|------|---------|
| `.python-version` | `3.14.2t` |
| `.gitignore` | Standard Python ignores (matching reference projects) |
| `CLAUDE.md` | Experimental project, Astral tools, no auto-commit |
| `LICENSE` | MIT, Copyright 2026 Paul Everitt |

### Task 3: Rewrite pyproject.toml

Full rewrite of the minimal skeleton to match reference conventions:
- Description: "AI coding agent that delegates tool execution to PyCharm via ACP"
- `dependencies = []` (no runtime deps yet)
- Build system: `uv_build`
- Classifiers: Alpha, Python 3.14, Typed
- Dev deps: pytest, pytest-cov, pytest-xdist, pytest-timeout, pytest-run-parallel, sybil[pytest], ruff, ty, pyright, pyrefly, coverage, furo, myst-parser, sphinx, sphinx-autobuild, linkify-it-py
- `[tool.pytest.ini_options]`: testpaths=["tests", "src"], addopts="-p no:doctest -m \"not slow\"", timeout=60
- `[tool.coverage.report]`: fail_under=80

### Task 4: Create Source Package

| File | Content |
|------|---------|
| `src/punie/__init__.py` | Package docstring only |
| `src/punie/py.typed` | Empty (PEP 561 marker) |

### Task 5: Create Test Infrastructure

| File | Content |
|------|---------|
| `tests/__init__.py` | Empty |
| `tests/test_punie.py` | Minimal function-based test: import punie, assert `__name__` |

### Task 6: Create Root conftest.py (Sybil)

Following tdom-svcs pattern:
- `DocTestParser` for `src/**/*.py`
- `PythonCodeBlockParser` for `README.md`
- `pytest_collect_file` hook with `examples/` exclusion

### Task 7: Create Justfile

All standard recipes matching both reference projects:
- install, test, test-cov, test-cov-check, test-parallel, test-file, test-match
- lint, lint-fix, format, format-check, typecheck
- quality, quality-fix, ci-checks, ci-checks-ft
- docs-build, docs-serve, clean, doctest, coverage-report
- test-run-parallel, enable-pre-push, disable-pre-push

### Task 8: Create Documentation Structure

| File | Content |
|------|---------|
| `docs/conf.py` | Sphinx + Furo + MyST, matching reference projects |
| `docs/conftest.py` | Sybil for `docs/**/*.md` |
| `docs/index.md` | Minimal index with empty toctree |
| `docs/_static/favicon.svg` | Simple "pu" favicon |
| `docs/_templates/.gitkeep` | Empty dir for template overrides |

### Task 9: Create GitHub Actions and Workflows

| File | Content |
|------|---------|
| `.github/actions/setup-python-uv/action.yml` | Composite action: cache .venv, install uv, Python 3.14t, `uv sync --frozen` |
| `.github/workflows/ci.yml` | Push/PR: setup + `just ci-checks-ft` + `just coverage-report` |
| `.github/workflows/pages.yml` | Push to main: build Sphinx docs, deploy to GitHub Pages |

### Task 10: Create Examples Directory

| File | Content |
|------|---------|
| `examples/.gitkeep` | Empty placeholder (referenced in pythonpath) |

### Task 11: Install Dependencies and Verify

1. Run `uv sync` to install deps and generate `uv.lock`
2. Run `uv run pytest tests/` — minimal test passes
3. Use `astral:ruff` skill to check linting
4. Use `astral:ty` skill to check types
5. Run `uv run pytest` (full suite including Sybil) — no collection errors
6. Run `uv run sphinx-build -W -b html docs docs/_build/html` — docs build

## Files Summary

**22 files to create**, **1 file to modify** (pyproject.toml), **1 file generated** (uv.lock)
