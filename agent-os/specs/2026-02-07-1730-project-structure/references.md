# Reference Projects

This spec draws patterns from two reference projects that follow identical conventions.

## svcs-di

**Location:** `/Users/pauleveritt/projects/t-strings/svcs-di/`

**Purpose:** Dependency injection using svcs

**Key Files:**
- `pyproject.toml` — Full dev dependencies, pytest config, build system
- `Justfile` — Complete recipe set for testing, linting, docs, CI
- `conftest.py` — Sybil setup with `_doctest_setup` for mock types
- `.github/workflows/ci.yml` — CI workflow with free-threading tests
- `.github/actions/setup-python-uv/action.yml` — Reusable setup action
- `docs/conf.py` — Sphinx + Furo + MyST configuration

**Patterns Used:**
- `uv_build` build system
- Comprehensive dev dependencies (pytest, ruff, ty, sphinx, etc.)
- Function-based tests
- Sybil for doctest integration with custom setup
- Free-threading test support via pytest-run-parallel
- Coverage threshold at 80%

## tdom-svcs

**Location:** `/Users/pauleveritt/projects/t-strings/tdom-svcs/`

**Purpose:** TDOM integration with svcs dependency injection

**Key Files:**
- `pyproject.toml` — Same dev dependencies as svcs-di
- `Justfile` — Identical recipe set
- `conftest.py` — Simpler Sybil setup without custom `_doctest_setup`
- `.github/workflows/ci.yml` — Same CI structure
- `.github/actions/setup-python-uv/action.yml` — Same setup action
- `docs/conf.py` — Same Sphinx configuration

**Patterns Used:**
- Same as svcs-di
- Simpler Sybil configuration (no mock types needed)
- Additional `[tool.ty.src]` configuration for multiple paths

## Shared Conventions

Both projects follow identical patterns for:

### Dependencies

```toml
[dependency-groups]
dev = [
    "coverage>=7.13.0",
    "furo>=2025.12.19",
    "linkify-it-py>=2.0.3",
    "myst-parser",
    "pyrefly>=0.46.1",
    "pyright>=1.1.407",
    "pytest>=8.4.2",
    "pytest-cov>=4.1.0",
    "pytest-run-parallel>=0.8.1",
    "pytest-timeout>=2.4.0",
    "pytest-xdist>=3.8.0",
    "ruff>=0.14.10",
    "sphinx>=8",
    "sphinx-autobuild>=2025.8.25",
    "sybil[pytest]>=8.4.2",
    "ty>=0.0.6",
]
```

### Pytest Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests", "src"]
addopts = "-p no:doctest -m \"not slow\""
pythonpath = ["examples"]
timeout = 60
```

### Justfile Recipes

Standard recipe set:
- `install` — `uv sync`
- `test` — `uv run pytest`
- `test-cov` — pytest with coverage
- `test-parallel` — pytest with xdist
- `lint` — ruff check
- `lint-fix` — ruff check --fix
- `format` — ruff format
- `format-check` — ruff format --check
- `typecheck` — ty check
- `quality` — lint + format-check + typecheck
- `quality-fix` — lint-fix + format
- `ci-checks` — quality + test-cov
- `ci-checks-ft` — ci-checks + test-run-parallel
- `docs-build` — sphinx-build
- `docs-serve` — sphinx-autobuild
- `clean` — Remove build artifacts

### GitHub Actions

Composite action pattern for setup:
```yaml
# .github/actions/setup-python-uv/action.yml
- Cache .venv
- Install uv
- Setup Python 3.14t
- Run uv sync --frozen
```

CI workflow pattern:
```yaml
# .github/workflows/ci.yml
- Checkout
- Setup via composite action
- Run just ci-checks-ft
- Run just coverage-report
```

### Documentation

Sphinx configuration:
- Furo theme
- MyST parser for Markdown
- linkify-it-py for URL auto-linking
- Minimal index.md with toctree

## Differences

The only notable difference is:

**svcs-di** has a `_doctest_setup()` function in `conftest.py` to provide mock types (Greeting, Database, etc.) for docstring examples.

**tdom-svcs** does not need this because its examples don't require mock types.

For Punie, we'll follow the tdom-svcs simpler pattern since we don't have complex docstring examples yet.
