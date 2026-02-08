# Shape: Agent Configuration, Safety, and Memory

## File Changes

| Action | File | LOC | Description |
|--------|------|-----|-------------|
| Create | `src/punie/agent/config.py` | ~60 | `AgentConfig` dataclass + two instruction sets |
| Create | `src/punie/local/safety.py` | ~40 | `resolve_workspace_path()` and `WorkspaceBoundaryError` |
| Create | `src/punie/models/memory.py` | ~80 | Memory snapshot and checking utilities |
| Modify | `src/punie/agent/factory.py` | +30 | Accept `AgentConfig`, add output validation |
| Modify | `src/punie/local/client.py` | +5 | Use `resolve_workspace_path()` in `_resolve_path` |
| Modify | `src/punie/local/__init__.py` | +2 | Export safety types |
| Modify | `src/punie/models/mlx.py` | +15 | Add memory check before model loading |
| Modify | `src/punie/cli.py` | +20 | Add `resolve_mode()` function, wire into serve/main |
| Create | `tests/test_agent_config.py` | ~200 | ~10 tests for AgentConfig + factory + mode switching |
| Create | `tests/test_workspace_safety.py` | ~250 | ~10 tests for path safety |
| Create | `tests/test_memory.py` | ~150 | ~8 tests for memory utilities |
| Modify | `agent-os/product/roadmap.md` | +30 | Mark 6.4–6.6 complete |
| Modify | `docs/research/evolution.md` | +100 | Add 6.4–6.6 entries |

**Total:** ~982 LOC

## Package Structure

```
src/punie/
├── agent/
│   ├── config.py          # NEW: AgentConfig + instruction sets
│   └── factory.py         # MODIFIED: Accept AgentConfig, validation
├── local/
│   ├── safety.py          # NEW: Workspace boundary enforcement
│   ├── client.py          # MODIFIED: Use resolve_workspace_path()
│   └── __init__.py        # MODIFIED: Export safety types
├── models/
│   ├── memory.py          # NEW: Memory monitoring utilities
│   └── mlx.py             # MODIFIED: Memory check before load
└── cli.py                 # MODIFIED: resolve_mode() + mode switching

tests/
├── test_agent_config.py   # NEW: ~10 tests
├── test_workspace_safety.py  # NEW: ~10 tests
└── test_memory.py         # NEW: ~8 tests

agent-os/specs/2026-02-08-local-model-integration/
├── plan.md
├── shape.md
├── standards.md
└── references.md
```

## Data Structures

### AgentConfig (Phase 6.4)

```python
@dataclass(frozen=True)
class AgentConfig:
    """Configuration for Punie agent behavior."""
    instructions: str = PUNIE_INSTRUCTIONS  # PyCharm/ACP default
    temperature: float = 0.0
    max_tokens: int = 4096
    retries: int = 3
    output_retries: int = 2
    validate_python_syntax: bool = False  # off by default (ACP mode)
```

### WorkspaceBoundaryError (Phase 6.5)

```python
class WorkspaceBoundaryError(Exception):
    """Raised when a path resolves outside the workspace directory."""
    def __init__(self, path: Path, workspace: Path):
        self.path = path
        self.workspace = workspace
        super().__init__(f"Path {path} is outside workspace {workspace}")
```

### MemorySnapshot (Phase 6.6)

```python
@dataclass(frozen=True)
class MemorySnapshot:
    """Point-in-time memory usage measurement."""
    rss_bytes: int          # Resident Set Size (actual RAM used)
    rss_mb: float           # RSS in megabytes
    peak_rss_bytes: int     # Peak RSS (max RSS since process start)
    peak_rss_mb: float      # Peak RSS in megabytes
```

## Function Signatures

### Phase 6.4: Agent Configuration

```python
def resolve_mode(mode_flag: str | None) -> str:
    """Resolve mode from CLI flag, env var, or default.

    Priority: CLI flag > PUNIE_MODE env var > "acp" default.
    """

def create_pydantic_agent(
    model: KnownModelName | Model = "openai:gpt-4o",
    config: AgentConfig | None = None,
) -> PydanticAgent:
    """Create Pydantic AI agent with optional configuration."""
```

### Phase 6.5: Workspace Safety

```python
def resolve_workspace_path(workspace: Path, path: str) -> Path:
    """Resolve path ensuring it stays within workspace boundary.

    Raises:
        WorkspaceBoundaryError: If resolved path is outside workspace
    """
```

### Phase 6.6: Memory Monitoring

```python
def get_memory_snapshot() -> MemorySnapshot:
    """Get current process memory usage via resource.getrusage()."""

def check_memory_available(
    model_size_mb: float,
    safety_margin_mb: float = 1024.0,
) -> tuple[bool, MemorySnapshot]:
    """Check if enough memory is available before model loading.

    Returns:
        (available: bool, current_snapshot: MemorySnapshot)
    """

def estimate_model_size(model_name: str) -> float:
    """Estimate model size from name. Falls back to 4096MB (7B default)."""
```

## Configuration Flow

```
User invocation:
  punie serve                    → resolve_mode() → "acp"  → PUNIE_INSTRUCTIONS
  PUNIE_MODE=local punie serve   → resolve_mode() → "local" → PUNIE_LOCAL_INSTRUCTIONS
  punie serve --mode local       → resolve_mode() → "local" → PUNIE_LOCAL_INSTRUCTIONS

Mode switching:
  "acp" mode:
    - Use PunieAgent() with ACP client
    - PyCharm/RPC integration
    - No workspace safety (PyCharm handles paths)
    - No memory monitoring (PyCharm environment)

  "local" mode:
    - Use create_local_agent() with LocalClient
    - Direct filesystem access
    - resolve_workspace_path() enforced on all paths
    - Memory check before MLX model load
    - Python syntax validation enabled
```

## Test Coverage

| Module | Tests | Coverage |
|--------|-------|----------|
| `test_agent_config.py` | 10 | Config dataclass, factory integration, mode switching, syntax validation |
| `test_workspace_safety.py` | 10 | Path resolution, traversal blocking, symlink handling, end-to-end LocalClient |
| `test_memory.py` | 8 | Memory snapshot, availability checks, model size estimation |

**Total new tests:** 28
