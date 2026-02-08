# Phase 6.2: Model Download CLI — Plan

## Context

Phase 6.1 added local MLX model support to Punie, but two issues remain:

1. **No model download command** — Users must manually download models via huggingface_hub. When `punie serve --model local` is run without a downloaded model, `mlx_lm.utils.load()` fails with an opaque error.

2. **Python 3.14t blocks mlx-lm** — mlx-lm has no cp314t (free-threaded) wheels. The project currently uses Python 3.14.2t.

**Decision:** Switch to regular Python 3.14.2 to unblock local model installation.

## Objectives

1. Switch from Python 3.14.2t (free-threaded) to Python 3.14.2 (regular)
2. Add `punie download-model` CLI command with progress reporting
3. Add model validation that shows clear error messages with download instructions
4. Ensure `uv pip install 'punie[local]'` works without errors

## Success Criteria

- Python version is 3.14.2 (not 3.14.2t)
- `uv pip install 'punie[local]'` successfully installs mlx-lm
- `punie download-model` downloads models with progress messages
- `punie download-model --list` shows recommended models
- `punie serve --model local` without downloaded model shows clear error with download instructions
- All existing tests pass (minus deleted free-threading tests)
- Coverage remains >80%

## Non-Goals

- Automatic model download on first use (require explicit download)
- Model versioning or update checking
- Multiple model management UI
