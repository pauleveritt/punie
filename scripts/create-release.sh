#!/usr/bin/env bash
set -euo pipefail

VERSION="$1"

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

# Write release notes to temporary file
cat > /tmp/punie-release-notes.md << 'EOF'
# Punie VERSIONPLACEHOLDER - Trained Models

This release includes trained LoRA adapters for Punie local coding agent.

## Phase 7 Adapter (Recommended)
**Full-stack web development: Python + HTML**

- **Accuracy:** 100% discrimination (tool vs direct-answer queries)
- **Speed:** 11.96s avg inference, 0.68s load time
- **Size:** 130 MB adapter
- **Domains:** Python (FastAPI, pytest, Flask, typer, click, httpx, starlette, pydantic, attrs, structlog) + HTML
- **Training:** 824 examples (741 train, 83 valid)

**Download:** punie-phase7-adapter.tar.gz

## Phase 6 Adapter
**Python-focused development**

- **Accuracy:** 100% discrimination
- **Speed:** 11.97s avg inference, 1.25s load time
- **Size:** 130 MB adapter
- **Domains:** Python only (10 popular frameworks)
- **Training:** 794 examples (714 train, 80 valid)

**Download:** punie-phase6-adapter.tar.gz

## Installation

1. **Download the model:**
   ```bash
   wget https://github.com/USERPLACEHOLDER/punie/releases/download/VERSIONPLACEHOLDER/punie-phase7-adapter.tar.gz
   tar -xzf punie-phase7-adapter.tar.gz
   ```

2. **Start MLX server with adapter:**
   ```bash
   uv run python -m mlx_lm.server \
     --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
     --adapter-path adapters_phase7 \
     --port 8080
   ```

3. **Run Punie:**
   ```bash
   uv run punie serve --model local
   ```

## Base Model

Both adapters require the base model:
- **Base:** mlx-community/Qwen2.5-Coder-7B-Instruct-4bit
- **Size:** ~4 GB (downloaded automatically by MLX)

## Performance Comparison

| Model | Load Time | Inference | Accuracy | Domains |
|-------|-----------|-----------|----------|---------|
| Phase 7 | 0.68s | 11.96s | 100% | Python + HTML |
| Phase 6 | 1.25s | 11.97s | 100% | Python only |

## Documentation

- [Model Performance Tracker](https://github.com/USERPLACEHOLDER/punie/blob/main/MODEL_PERFORMANCE_TRACKER.md)
- [Training Methodology](https://github.com/USERPLACEHOLDER/punie/tree/main/agent-os/specs)
- [Development Diary](https://github.com/USERPLACEHOLDER/punie/tree/main/docs/diary)

For questions or issues, please visit the [GitHub repository](https://github.com/USERPLACEHOLDER/punie).
EOF

# Replace placeholders
sed -i '' "s/VERSIONPLACEHOLDER/$VERSION/g" /tmp/punie-release-notes.md
sed -i '' "s/USERPLACEHOLDER/$GH_USER/g" /tmp/punie-release-notes.md

# Create release
echo "Creating GitHub Release $VERSION..."
gh release create "$VERSION" \
    --title "Punie $VERSION - Multi-domain Local Model Training" \
    --notes-file /tmp/punie-release-notes.md \
    punie-phase7-adapter.tar.gz \
    punie-phase6-adapter.tar.gz

# Clean up temp file
rm /tmp/punie-release-notes.md

echo ""
echo "✓ Release $VERSION created successfully!"
echo "View at: https://github.com/$GH_USER/punie/releases/tag/$VERSION"
