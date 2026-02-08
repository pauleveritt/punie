# Phases 6.4–6.6: Agent Configuration, Safety Constraints, Memory Optimization

## Context

Phases 6.1–6.3 gave Punie a local MLX model, a download CLI, and a `LocalClient` for standalone operation. But the agent still has a generic PyCharm-centric system prompt, zero workspace safety checks, and no memory monitoring. This spec completes Local Model Integration by making the agent coding-aware (6.4), workspace-safe (6.5), and memory-efficient (6.6).

**Product alignment:** The mission targets "Python developers on modest hardware" — all three phases serve that goal directly.

**Key design principle:** PyCharm/ACP is the default mode. Set `PUNIE_MODE=local` to switch to standalone local mode. This follows the same pattern as `PUNIE_MODEL` env var (see `resolve_model()` in `src/punie/cli.py:106`).

```
Default (ACP mode):           PUNIE_MODE=local:
  PUNIE_INSTRUCTIONS            PUNIE_LOCAL_INSTRUCTIONS
  ACP Client (PyCharm RPC)      LocalClient (real filesystem)
  No workspace safety needed    resolve_workspace_path() enforced
  No memory monitoring needed   Memory check before MLX model load
```

## Phase 6.4: Agent Configuration

**Goal:** Make agent instructions and behavior configurable for different execution modes.

### Implementation

1. **Create `AgentConfig` dataclass** (`src/punie/agent/config.py`)
   - Frozen dataclass with instructions, temperature, max_tokens, retries, output_retries, validate_python_syntax
   - Two instruction constants: `PUNIE_INSTRUCTIONS` (PyCharm/ACP default) and `PUNIE_LOCAL_INSTRUCTIONS` (standalone local)
   - Default to `PUNIE_INSTRUCTIONS` for backward compatibility

2. **Update `create_pydantic_agent()`** (`src/punie/agent/factory.py`)
   - Accept optional `AgentConfig` parameter
   - Use config values instead of hardcoded constants
   - Add Python syntax validation when `config.validate_python_syntax` is True
   - Validation uses `ast.parse()` on fenced Python code blocks

3. **Add `resolve_mode()`** (`src/punie/cli.py`)
   - Follow `resolve_model()` pattern
   - Priority: CLI flag > `PUNIE_MODE` env var > "acp" default
   - Wire into serve command to switch between ACP and local modes

### Key Decisions

- **Default is ACP/PyCharm** — `AgentConfig()` uses `PUNIE_INSTRUCTIONS` and `validate_python_syntax=False`
- **`PUNIE_MODE=local`** switches to `PUNIE_LOCAL_INSTRUCTIONS` + `validate_python_syntax=True`
- Frozen dataclass per standard — config is immutable once created
- `ast.parse()` validation only on fenced Python code blocks, not prose
- Factory remains backward-compatible: no config param = same as before

## Phase 6.5: Workspace Safety

**Goal:** Prevent LocalClient from accessing files outside the workspace directory.

### Implementation

1. **Create safety utilities** (`src/punie/local/safety.py`)
   - `WorkspaceBoundaryError` exception with path and workspace info
   - `resolve_workspace_path()` function that:
     - Joins workspace + path
     - Calls `.resolve()` to canonicalize (handles symlinks, `..`, etc.)
     - Checks `resolved.is_relative_to(workspace.resolve())`
     - Raises `WorkspaceBoundaryError` if outside

2. **Update `LocalClient`** (`src/punie/local/client.py`)
   - Replace `_resolve_path()` implementation to call `resolve_workspace_path()`
   - Terminal `cwd` also goes through `_resolve_path` — commands can't escape

3. **Export safety types** (`src/punie/local/__init__.py`)
   - Export `WorkspaceBoundaryError` and `resolve_workspace_path`

### Key Decisions

- Pure function `resolve_workspace_path()` — easy to test independently
- Custom exception `WorkspaceBoundaryError` — clear error for path violations
- Always `resolve()` to canonicalize paths (handles `..`, symlinks)
- `is_relative_to()` check after resolution — robust against all traversal attacks
- Absolute paths are checked too — `/etc/passwd` would fail `is_relative_to(workspace)`

## Phase 6.6: Memory Monitoring

**Goal:** Warn users before loading models that may exceed available memory.

### Implementation

1. **Create memory utilities** (`src/punie/models/memory.py`)
   - `MemorySnapshot` frozen dataclass with RSS and peak RSS measurements
   - `get_memory_snapshot()` using `resource.getrusage()` (stdlib, no extra dependency)
   - `check_memory_available()` with simple heuristic: current RSS + model_size + safety_margin < total RAM
   - `MODEL_SIZES_MB` dict with estimates for 3B-4bit, 7B-4bit, 14B-4bit
   - `estimate_model_size()` function to map model names to sizes

2. **Update `MLXModel`** (`src/punie/models/mlx.py`)
   - Add memory check in `from_pretrained()` before calling `mlx_load()`
   - Log warning if insufficient memory (don't block — user may know their system)
   - Log actual memory usage after loading via `get_memory_snapshot()`

### Key Decisions

- `resource.getrusage()` — stdlib, no extra dependency, works on macOS/Linux
- Frozen `MemorySnapshot` dataclass per standard
- Warning, not error — don't block users who know their system can handle it
- Simple heuristic — not a sophisticated memory profiler, just a safety check
- Model size estimates baked in — covers the 3 recommended models from CLI

## Success Criteria

1. `AgentConfig` is frozen and used by factory
2. `PUNIE_MODE=local` switches to local instructions and safety checks
3. `WorkspaceBoundaryError` raised for path traversal attempts
4. Memory snapshot logged before and after model loading
5. All tests pass with `astral:ruff` and `astral:ty` clean
