# Justfile for punie project

# Default recipe - show available commands
default:
    @just --list

# Install dependencies
install:
    uv sync

# Run all tests
test:
    uv run pytest

# Run tests with coverage
test-cov:
    uv run pytest tests src --cov=punie --cov-report=term-missing --cov-report=html

# Check coverage meets 80% threshold
test-cov-check:
    uv run pytest tests src --cov=punie --cov-report=term-missing --cov-fail-under=80

# Run tests in parallel
test-parallel:
    uv run pytest -n auto

# Run specific test file
test-file FILE:
    uv run pytest {{FILE}}

# Run tests matching a pattern
test-match PATTERN:
    uv run pytest -k {{PATTERN}}

# Run linting with ruff
lint:
    uv run ruff check src tests

# Fix linting issues automatically
lint-fix:
    uv run ruff check --fix src tests

# Format code with ruff
format:
    uv run ruff format src tests

# Check formatting without making changes
format-check:
    uv run ruff format --check src tests

# Run type checking
typecheck *ARGS:
    uv run ty check {{ ARGS }}

# Run all quality checks (lint, format-check, typecheck)
quality: lint format-check typecheck

# Run all quality checks and fix what can be fixed
quality-fix: lint-fix format

# Build documentation
docs-build:
    uv run sphinx-build -W -b html docs docs/_build/html

# Serve documentation with auto-reload
docs-serve:
    uv run sphinx-autobuild docs docs/_build/html --open-browser

# Clean build artifacts
clean:
    rm -rf dist/ build/ *.egg-info .pytest_cache .ruff_cache htmlcov/ .coverage
    find . -type d -name __pycache__ -exec rm -rf {} +
    find . -type f -name "*.pyc" -delete

# Run the full CI suite (quality + tests with coverage)
ci-checks: quality test-cov-check

# Run doctests specifically (via Sybil)
doctest:
    uv run pytest src/ -v

# Show coverage report and check 80% threshold
coverage-report:
    #!/usr/bin/env bash
    set -euo pipefail
    uv run coverage report
    uv run coverage html
    echo "HTML coverage report generated in htmlcov/index.html"
    COVERAGE=$(uv run coverage report | grep TOTAL | awk '{print $4}' | sed 's/%//')
    if (( $(echo "$COVERAGE < 80" | bc -l) )); then
        echo "::warning::Coverage is ${COVERAGE}% which is below the 80% threshold"
        exit 1
    else
        echo "Coverage is ${COVERAGE}% which meets the 80% threshold"
    fi


# Enable pre-push hook to run ci-checks before pushing - installs git hook
# Automatically runs full quality checks before every git push
# Blocks push if any check fails, preventing broken code from being pushed
enable-pre-push:
    @echo "Installing pre-push hook..."
    @echo '#!/bin/sh' > .git/hooks/pre-push
    @echo '' >> .git/hooks/pre-push
    @echo '# Run quality checks before push' >> .git/hooks/pre-push
    @echo 'echo "Running quality checks before push..."' >> .git/hooks/pre-push
    @echo 'if ! just ci-checks; then' >> .git/hooks/pre-push
    @echo '    echo "Pre-push check failed! Push aborted."' >> .git/hooks/pre-push
    @echo '    exit 1' >> .git/hooks/pre-push
    @echo 'fi' >> .git/hooks/pre-push
    @chmod +x .git/hooks/pre-push
    @echo "Pre-push hook installed! Use 'just disable-pre-push' to disable."

# Disable pre-push hook - removes executable permissions from git hook
# Push will work normally without running checks
disable-pre-push:
    @chmod -x .git/hooks/pre-push 2>/dev/null || true
    @echo "Pre-push hook disabled. Use 'just enable-pre-push' to re-enable."

# Prepare model releases - compress adapters for distribution
release-prepare:
    #!/usr/bin/env bash
    set -euo pipefail
    echo "Compressing Phase 7 adapter (Python + HTML)..."
    tar -czf punie-phase7-adapter.tar.gz adapters_phase7/
    echo "✓ Created punie-phase7-adapter.tar.gz ($(du -h punie-phase7-adapter.tar.gz | cut -f1))"

    echo "Compressing Phase 6 adapter (Python only)..."
    tar -czf punie-phase6-adapter.tar.gz adapters_phase6/
    echo "✓ Created punie-phase6-adapter.tar.gz ($(du -h punie-phase6-adapter.tar.gz | cut -f1))"

    echo ""
    echo "Ready for release! Run: just release-create <version>"

# Create GitHub Release with model artifacts
# Usage: just release-create v1.0.0
release-create VERSION:
    #!/usr/bin/env bash
    set -euo pipefail

    # Check if compressed files exist
    if [ ! -f punie-phase7-adapter.tar.gz ] || [ ! -f punie-phase6-adapter.tar.gz ]; then
        echo "Error: Compressed model files not found. Run 'just release-prepare' first."
        exit 1
    fi

    # Check if gh CLI is installed
    if ! command -v gh &> /dev/null; then
        echo "Error: GitHub CLI (gh) is not installed."
        echo "Install: brew install gh"
        exit 1
    fi

    # Get GitHub username
    GH_USER=$(gh api user --jq .login)

    # Create release with notes
    echo "Creating GitHub Release {{VERSION}}..."
    gh release create {{VERSION}} \
        --title "Punie {{VERSION}} - Multi-domain Local Model Training" \
        --notes "# Punie {{VERSION}} - Trained Models

This release includes trained LoRA adapters for Punie's local coding agent.

## 🏆 Phase 7 Adapter (Recommended)
**Full-stack web development: Python + HTML**

- **Accuracy:** 100% discrimination (tool vs direct-answer queries)
- **Speed:** 11.96s avg inference, 0.68s load time
- **Size:** 130 MB adapter
- **Domains:** Python (FastAPI, pytest, Flask, typer, click, httpx, starlette, pydantic, attrs, structlog) + HTML (semantic, forms, tables, accessibility)
- **Training:** 824 examples (741 train, 83 valid)

**Download:** \`punie-phase7-adapter.tar.gz\`

## Phase 6 Adapter
**Python-focused development**

- **Accuracy:** 100% discrimination
- **Speed:** 11.97s avg inference, 1.25s load time
- **Size:** 130 MB adapter
- **Domains:** Python only (10 popular frameworks)
- **Training:** 794 examples (714 train, 80 valid)

**Download:** \`punie-phase6-adapter.tar.gz\`

## Installation

1. **Download the model:**
   \`\`\`bash
   wget https://github.com/$GH_USER/punie/releases/download/{{VERSION}}/punie-phase7-adapter.tar.gz
   tar -xzf punie-phase7-adapter.tar.gz
   \`\`\`

2. **Start MLX server with adapter:**
   \`\`\`bash
   uv run python -m mlx_lm.server \\
     --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \\
     --adapter-path adapters_phase7 \\
     --port 8080
   \`\`\`

3. **Run Punie:**
   \`\`\`bash
   uv run punie serve --model local
   \`\`\`

## Base Model

Both adapters require the base model:
- **Base:** \`mlx-community/Qwen2.5-Coder-7B-Instruct-4bit\`
- **Size:** ~4 GB (downloaded automatically by MLX)

## Performance Comparison

| Model | Load Time | Inference | Accuracy | Domains |
|-------|-----------|-----------|----------|---------|
| Phase 7 | 0.68s | 11.96s | 100% | Python + HTML |
| Phase 6 | 1.25s | 11.97s | 100% | Python only |

## Documentation

- [Model Performance Tracker](https://github.com/$GH_USER/punie/blob/main/MODEL_PERFORMANCE_TRACKER.md)
- [Training Methodology](https://github.com/$GH_USER/punie/tree/main/agent-os/specs)
- [Development Diary](https://github.com/$GH_USER/punie/tree/main/docs/diary)

For questions or issues, please visit the [GitHub repository](https://github.com/$GH_USER/punie)." \
        punie-phase7-adapter.tar.gz \
        punie-phase6-adapter.tar.gz

    echo ""
    echo "✓ Release {{VERSION}} created successfully!"
    echo "View at: https://github.com/$GH_USER/punie/releases/tag/{{VERSION}}"

# Clean up compressed model files after release
release-clean:
    @rm -f punie-phase7-adapter.tar.gz punie-phase6-adapter.tar.gz
    @echo "✓ Cleaned up compressed model files"

# Full release workflow: prepare, create, and clean
# Usage: just release v1.0.0
release VERSION: release-prepare (release-create VERSION) release-clean
    @echo ""
    @echo "🎉 Release {{VERSION}} complete!"
    @echo "Models are now available for download on GitHub."
