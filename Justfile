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
    ./scripts/create-release.sh {{VERSION}}

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

# Start Punie server with auto-managed MLX server (one command does everything)
serve:
    uv run punie serve --model local

# Start Toad UI with WebSocket connection (requires Punie server running)
toad-start:
    #!/usr/bin/env bash
    set -euo pipefail

    # Check if Punie server is running
    if ! lsof -ti:8000 > /dev/null 2>&1; then
        echo "⚠️  Punie server is not running on port 8000"
        echo "   Start it with: just serve"
        echo ""
        echo "   Or use 'just toad-dev' to start both together"
        echo ""
        exit 1
    fi

    echo "🐸 Starting Toad UI with WebSocket connection..."
    echo "   Punie server: http://localhost:8000"
    echo "   WebSocket: ws://localhost:8000/ws"
    echo ""
    echo "✨ Using WebSocket transport (no subprocess!)"
    echo ""
    echo "Press Ctrl+D or 'quit' to exit Toad"
    echo ""

    # Run Toad with WebSocket agent subclass
    uv run python scripts/run_toad_websocket.py

# Start Punie server and Toad together (recommended for development)
toad-dev:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "🚀 Starting Toad UI with Punie server..."
    echo ""

    # Start Punie server in background if not already running
    if lsof -ti:8000 > /dev/null 2>&1; then
        echo "   ✓ Punie server already running on port 8000"
        echo "   ℹ️  Connecting Toad to existing server"
        echo ""
    else
        echo "   🚀 Starting Punie server (auto-detecting model)..."
        echo "   ⏳ This takes ~15 seconds for model loading..."
        echo ""

        uv run punie serve --model local > punie-server.log 2>&1 &
        PUNIE_PID=$!
        echo "   Punie server starting (PID $PUNIE_PID, log: punie-server.log)"

        # Wait for Punie to be ready
        echo "   Waiting for Punie server to start..."
        for i in {1..60}; do
            if lsof -ti:8000 > /dev/null 2>&1; then
                echo "   ✓ Punie server ready on port 8000"
                break
            fi
            sleep 1
            if [ $i -eq 60 ]; then
                echo "   ❌ Punie server failed to start (timeout)"
                echo "   Check punie-server.log for details"
                exit 1
            fi
        done
    fi

    echo ""
    echo "   Now starting Toad UI with WebSocket..."
    echo ""

    # Start Toad with WebSocket (foreground)
    uv run python scripts/run_toad_websocket.py

    echo ""
    echo "✓ Toad closed"
    echo "ℹ️  Punie server still running (use 'punie stop-all' to stop)"
