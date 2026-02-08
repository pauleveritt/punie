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
