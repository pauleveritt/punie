# Phase 6.2: Model Download CLI — Standards

## Code Standards

### Error Messages

- Clear actionable error messages with exact command to fix
- Use `RuntimeError` for user-facing errors (not `ValueError` or `TypeError`)
- Include model name in error messages for clarity
- Exit with code 1 for user errors (not code 0)

### CLI Design

- Use Typer for consistent CLI patterns
- Default to sensible values (default model, ~/.cache/punie/models)
- Support --help for all commands
- Use typer.echo() for user-facing messages (not print())
- Use typer.secho() with fg=typer.colors.RED for errors

### Testing

- Function-based tests (no classes)
- Test pure functions separately from CLI integration
- Use fakes/mocks for external dependencies (no actual downloads in tests)
- Cover both happy paths and error paths
- Test with and without mlx-lm installed (ImportError handling)

### Dependencies

- Use lazy imports for optional dependencies (mlx-lm)
- Use TYPE_CHECKING guards for type imports
- Fail gracefully with clear error messages when deps missing
- Don't add new required dependencies for optional features

## Python Version Strategy

### Decision: Python 3.14 (Regular)

**Rationale:**
- mlx-lm has no cp314t (free-threaded) wheels as of 2026-02-08
- Free-threaded ecosystem not mature for ML libraries
- Local model support is core feature, not optional
- Can revisit free-threading in future (Phase 9.3)

**Impact:**
- Remove all free-threading tests and infrastructure
- Update documentation to remove free-threading claims
- Mark Phase 9.3 as deferred with explanation
- Keep async concurrency tests (not free-threading specific)

## Model Storage

### Location

- Default: `~/.cache/punie/models/`
- User can override with `--models-dir`
- Create directory if it doesn't exist
- Use Hugging Face's default cache as fallback

### Download Strategy

- Use `huggingface_hub.snapshot_download()` (transitive dep of mlx-lm)
- Show progress messages (before/after, not streaming)
- Store full model name as subdirectory (e.g., `~/.cache/punie/models/mlx-community/Qwen2.5-Coder-7B-Instruct-4bit/`)
- Don't implement model versioning or updates in this phase

## Error Handling

### Missing Model Error

```python
try:
    model_data, tokenizer = mlx_load(model_name)
except Exception as e:
    if "not found" in str(e).lower() or "does not exist" in str(e).lower():
        msg = (
            f"Model '{model_name}' is not downloaded.\n"
            f"Download it with: punie download-model {model_name}"
        )
        raise RuntimeError(msg) from e
    raise
```

### Missing mlx-lm Error

```python
try:
    from mlx_lm import generate, load as mlx_load
except ImportError as e:
    msg = (
        "Local model support requires mlx-lm.\n"
        "Install with: uv pip install 'punie[local]'"
    )
    raise ImportError(msg) from e
```

## Documentation

- Update README.md with download-model examples
- Add to Phase 6.2 in roadmap.md
- Update docs/research/evolution.md with narrative
- Keep examples/15_mlx_local_model.py accurate
