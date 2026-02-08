# Phase 6.2: Model Download CLI — Shape

## API Changes

### New CLI Command

```bash
# Download default model
punie download-model

# Download specific model
punie download-model mlx-community/Qwen2.5-Coder-3B-Instruct-4bit

# List recommended models
punie download-model --list

# Custom models directory
punie download-model --models-dir ~/.cache/punie-models
```

### Error Messages

```python
# When model not downloaded
RuntimeError: Model 'mlx-community/Qwen2.5-Coder-7B-Instruct-4bit' is not downloaded.
Download it with: punie download-model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit

# When mlx-lm not installed
ImportError: Local model support requires mlx-lm.
Install with: uv pip install 'punie[local]'
```

## Implementation Files

### Modified Files

| File | Changes |
|------|---------|
| `.python-version` | `3.14.2t` → `3.14.2` |
| `CLAUDE.md` | Remove free-threaded reference |
| `pyproject.toml` | Remove `pytest-run-parallel`, remove `freethreaded` marker |
| `tests/test_concurrency.py` | Update docstring (not free-threading specific) |
| `.github/workflows/ci.yml` | Update job name, remove parallel test step |
| `.github/actions/setup-python-uv/action.yml` | Update comments |
| `Justfile` | Remove `test-run-parallel` recipe |
| `src/punie/cli.py` | Add `download_model()` command |
| `src/punie/models/mlx.py` | Add model validation in `from_pretrained()` |
| `README.md` | Add download-model usage, remove free-threaded reference |
| `agent-os/product/roadmap.md` | Mark 6.2 complete, note 9.3 deferral |
| `agent-os/product/tech-stack.md` | Update language line |

### Deleted Files

| File | Reason |
|------|--------|
| `tests/test_freethreaded.py` | Free-threading tests no longer applicable |

### New Files

| File | Purpose |
|------|---------|
| `tests/test_cli_download.py` | Test download command and model validation |
| `agent-os/specs/2026-02-08-model-download/` | Spec documentation |

## Architecture

```
┌─────────────────────────────────────────┐
│ User runs: punie serve --model local    │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ CLI: resolve_model() → "local"          │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ Factory: create_pydantic_agent()        │
│   - Detects "local" model               │
│   - Creates MLXModel                    │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ MLXModel.from_pretrained()              │
│   - Try: mlx_lm.utils.load(model_name)  │
│   - Catch: "not found" → RuntimeError   │
│            with download instructions   │
└───────────────┬─────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────┐
│ CLI main/serve: Catch RuntimeError      │
│   - Show red error message              │
│   - Exit with code 1                    │
└─────────────────────────────────────────┘
```

## User Experience

### Happy Path

```bash
# 1. Install with local support
$ uv pip install 'punie[local]'

# 2. Download model (one-time)
$ punie download-model
Downloading mlx-community/Qwen2.5-Coder-7B-Instruct-4bit...
Model downloaded successfully to ~/.cache/punie/models/

# 3. Use local model
$ punie serve --model local
🚀 Punie agent started on http://127.0.0.1:8000
```

### Error Path (Missing Model)

```bash
# User forgets to download model
$ punie serve --model local
Error: Model 'mlx-community/Qwen2.5-Coder-7B-Instruct-4bit' is not downloaded.
Download it with: punie download-model
$ echo $?
1
```

### List Models

```bash
$ punie download-model --list
Available models:

Name                                            Size    Description
──────────────────────────────────────────────────────────────────────
mlx-community/Qwen2.5-Coder-7B-Instruct-4bit   ~4GB    Default (best balance)
mlx-community/Qwen2.5-Coder-3B-Instruct-4bit   ~2GB    Faster, simpler tasks
mlx-community/Qwen2.5-Coder-14B-Instruct-4bit  ~8GB    Highest quality

Download with: punie download-model <model-name>
```
