# Phase 6.2: Model Download CLI — References

## External References

### Hugging Face Hub

- [huggingface_hub documentation](https://huggingface.co/docs/huggingface_hub/index)
- [snapshot_download API](https://huggingface.co/docs/huggingface_hub/package_reference/file_download#huggingface_hub.snapshot_download)
- [Model cards](https://huggingface.co/docs/hub/model-cards)

### MLX Models

- [MLX Community on Hugging Face](https://huggingface.co/mlx-community)
- [Qwen2.5-Coder-7B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen2.5-Coder-7B-Instruct-4bit)
- [Qwen2.5-Coder-3B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen2.5-Coder-3B-Instruct-4bit)
- [Qwen2.5-Coder-14B-Instruct-4bit](https://huggingface.co/mlx-community/Qwen2.5-Coder-14B-Instruct-4bit)

### Python Packaging

- [PEP 703: Making the GIL Optional](https://peps.python.org/pep-0703/)
- [uv documentation](https://docs.astral.sh/uv/)
- [Python 3.14 release notes](https://docs.python.org/3.14/whatsnew/3.14.html)

### Related Work

- [dorukgezici/pydantic-ai-mlx](https://github.com/dorukgezici/pydantic-ai-mlx) - Original MLX integration
- [Phase 6.1 spec](../2026-02-08-mlx-model/) - Local model integration

## Internal References

### Related Files

- `src/punie/cli.py` - CLI entry point
- `src/punie/models/mlx.py` - MLX model implementation
- `src/punie/agent/factory.py` - Agent factory with model resolution
- `examples/15_mlx_local_model.py` - Local model example
- `tests/test_mlx_model.py` - Existing MLX tests

### Related Phases

- **Phase 5.1** - Typer CLI implementation
- **Phase 5.2** - Init command patterns
- **Phase 6.1** - MLX model integration (completed)
- **Phase 6.3** - Local tools (next)

## Decision Log

### 2026-02-08: Switch to Python 3.14 (Regular)

**Problem:** mlx-lm requires binary wheels, no cp314t wheels available.

**Options Considered:**
1. Stay on 3.14t, make mlx-lm optional, skip local models
2. Switch to 3.13 (mlx-lm has wheels)
3. Switch to 3.14 (regular)

**Decision:** Option 3 (Python 3.14 regular)

**Rationale:**
- Local models are core feature (offline dev, zero API cost, privacy)
- Free-threading ecosystem not mature for ML libraries
- Python 3.14 has modern features we want
- Can revisit free-threading when ecosystem catches up
- Async concurrency still works fine

**Trade-offs:**
- ✅ Unblocks local model installation
- ✅ Keeps modern Python 3.14 features
- ✅ Maintains async concurrency
- ❌ Defers free-threading (Phase 9.3)
- ❌ Loses experimental parallel test benefits

### 2026-02-08: Explicit Download Required

**Problem:** How to handle models not being downloaded?

**Options Considered:**
1. Auto-download on first use (like ollama)
2. Fail with error, require explicit download
3. Prompt user to download interactively

**Decision:** Option 2 (explicit download)

**Rationale:**
- Clear user intent (downloads are multi-GB)
- No surprises (user knows download is happening)
- Works in non-interactive contexts (CI, scripts)
- Simple implementation (no progress streaming needed)
- Follows UV pattern (explicit `uv pip install`)

**Trade-offs:**
- ✅ Predictable behavior
- ✅ Works in all contexts
- ✅ Simple to implement
- ❌ Extra step for users
- ❌ Less "magic" than auto-download
