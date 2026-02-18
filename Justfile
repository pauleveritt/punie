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

# Start MLX server with production model (Phase 27, 5-bit quantized)
mlx-start:
    #!/usr/bin/env bash
    set -euo pipefail
    MODEL_PATH="fused_model_qwen3_phase27_cleaned_5bit"

    if [ ! -d "$MODEL_PATH" ]; then
        echo "❌ Production model not found at $MODEL_PATH"
        echo "Expected: fused_model_qwen3_phase27_cleaned_5bit/"
        exit 1
    fi

    echo "🚀 Starting MLX server with Phase 27 production model..."
    echo "   Model: $MODEL_PATH (20 GB, 5-bit quantized)"
    echo "   Endpoint: http://localhost:5001"
    echo ""
    echo "Press Ctrl+C to stop"
    echo ""

    uv run mlx_lm.server \
        --model "$MODEL_PATH" \
        --port 5001 \
        --trust-remote-code

# Stop MLX server (handles multiple orphaned processes)
mlx-stop:
    #!/usr/bin/env bash
    set -euo pipefail

    PIDS=$(lsof -ti:5001 || true)
    if [ -z "$PIDS" ]; then
        echo "✓ No MLX servers running on port 5001"
    else
        # Count processes
        COUNT=$(echo "$PIDS" | wc -l | tr -d ' ')
        if [ "$COUNT" -eq 1 ]; then
            echo "🛑 Stopping MLX server (PID $PIDS)..."
        else
            echo "🛑 Stopping $COUNT MLX servers (PIDs: $(echo $PIDS | tr '\n' ' '))..."
        fi

        # Kill all processes
        echo "$PIDS" | xargs kill 2>/dev/null || true
        sleep 1
        echo "✓ MLX server(s) stopped"
    fi

# Start both MLX and Punie servers with Phase 27 model (foreground)
# This is an alias for dev-servers with better naming
serve:
    @just dev-servers

# Start Punie HTTP/WebSocket server (Phase 28 with reconnection support)
# Legacy recipe that requires MLX server - prefer 'just serve' instead
server-start:
    #!/usr/bin/env bash
    set -euo pipefail

    # Check if MLX server is running
    if ! lsof -ti:5001 > /dev/null 2>&1; then
        echo "⚠️  MLX server is not running on port 5001"
        echo "   Start it with: just mlx-start"
        echo ""
        echo "   Or use 'just serve' to load model directly (recommended)"
        echo ""
        exit 1
    fi

    echo "🚀 Starting Punie HTTP/WebSocket server..."
    echo "   HTTP endpoint: http://localhost:8000"
    echo "   WebSocket endpoint: ws://localhost:8000/ws"
    echo "   Model: Phase 27 via MLX server (port 5001)"
    echo ""
    echo "Features enabled:"
    echo "  ✓ Multi-client WebSocket support"
    echo "  ✓ Session persistence (5-minute grace period)"
    echo "  ✓ Automatic reconnection"
    echo "  ✓ Secure resume tokens"
    echo ""
    echo "Press Ctrl+C to stop"
    echo ""

    # Use "local:" prefix (not "openai:") for custom MLX server
    # Format: local:http://host:port/v1/model-name
    uv run punie serve --model "local:http://localhost:5001/v1/fused_model_qwen3_phase27_cleaned_5bit"

# Stop Punie server
server-stop:
    #!/usr/bin/env bash
    set -euo pipefail

    PID=$(lsof -ti:8000 || true)
    if [ -z "$PID" ]; then
        echo "✓ Punie server is not running on port 8000"
    else
        echo "🛑 Stopping Punie server (PID $PID)..."
        kill $PID
        sleep 1
        echo "✓ Punie server stopped"
    fi

# Stop all servers (MLX + Punie)
stop-all: server-stop mlx-stop
    @echo ""
    @echo "✓ All servers stopped"

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

    # Check if Punie server is already running
    if lsof -ti:8000 > /dev/null 2>&1; then
        echo "   ✓ Punie server already running on port 8000"
        echo "   ℹ️  Connecting Toad to existing server"
        echo ""
    else
        # Check if MLX server is running
        if ! lsof -ti:5001 > /dev/null 2>&1; then
            echo "   🚀 Starting Punie server (includes MLX server)..."
            echo "   ⏳ This takes ~15 seconds for model loading..."
            echo ""
        else
            echo "   ✓ MLX server already running on port 5001"
            echo "   🚀 Starting Punie server..."
            echo ""
        fi

        # Start Punie server in background
        just serve > punie-server.log 2>&1 &
        PUNIE_PID=$!
        echo "   Punie server starting (PID $PUNIE_PID, log: punie-server.log)"

        # Wait for Punie to be ready
        echo "   Waiting for Punie server to start..."
        for i in {1..30}; do
            if lsof -ti:8000 > /dev/null 2>&1; then
                echo "   ✓ Punie server ready on port 8000"
                break
            fi
            sleep 1
            if [ $i -eq 30 ]; then
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

    # Note: Servers keep running after Toad exits
    # Use 'just stop-all' to stop them
    echo ""
    echo "✓ Toad closed"
    echo "ℹ️  Punie server still running (use 'just stop-all' to stop)"

# Start both MLX and Punie servers (for development)
dev-servers:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "🚀 Starting development servers..."
    echo ""

    # Start MLX in background
    just mlx-start > mlx-server.log 2>&1 &
    MLX_PID=$!
    echo "   MLX server starting (PID $MLX_PID, log: mlx-server.log)..."

    # Wait for MLX to be ready
    echo "   Waiting for MLX server to start..."
    for i in {1..30}; do
        if lsof -ti:5001 > /dev/null 2>&1; then
            echo "   ✓ MLX server ready"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then
            echo "   ❌ MLX server failed to start (timeout)"
            exit 1
        fi
    done

    echo ""
    echo "   Now starting Punie server..."
    echo ""

    # Start Punie server (foreground)
    just server-start

    # Cleanup on Ctrl+C
    trap "just stop-all" EXIT

# Start both servers in background (for CI or when you need terminal free)
dev-servers-bg:
    #!/usr/bin/env bash
    set -euo pipefail

    echo "🚀 Starting development servers in background..."
    echo ""

    # Start MLX in background
    just mlx-start > mlx-server.log 2>&1 &
    MLX_PID=$!
    echo "   MLX server starting (PID $MLX_PID)..."

    # Wait for MLX to be ready
    echo "   Waiting for MLX server to start..."
    for i in {1..30}; do
        if lsof -ti:5001 > /dev/null 2>&1; then
            echo "   ✓ MLX server ready on port 5001"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then
            echo "   ❌ MLX server failed to start (timeout)"
            exit 1
        fi
    done

    # Start Punie server in background
    just server-start > punie-server.log 2>&1 &
    PUNIE_PID=$!
    echo ""
    echo "   Punie server starting (PID $PUNIE_PID)..."

    # Wait for Punie to be ready
    echo "   Waiting for Punie server to start..."
    for i in {1..30}; do
        if lsof -ti:8000 > /dev/null 2>&1; then
            echo "   ✓ Punie server ready on port 8000"
            break
        fi
        sleep 1
        if [ $i -eq 30 ]; then
            echo "   ❌ Punie server failed to start (timeout)"
            kill $MLX_PID 2>/dev/null || true
            exit 1
        fi
    done

    echo ""
    echo "✅ Both servers running in background!"
    echo ""
    echo "📊 Server Info:"
    echo "   MLX:   PID $MLX_PID, port 5001, log: mlx-server.log"
    echo "   Punie: PID $PUNIE_PID, port 8000, log: punie-server.log"
    echo ""
    echo "📝 Commands:"
    echo "   View logs:  tail -f mlx-server.log punie-server.log"
    echo "   Stop all:   just stop-all"
    echo "   Check status: lsof -ti:5001 -ti:8000"
    echo ""
