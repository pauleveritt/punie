# References

## Internal

### Existing Patterns

- **`resolve_model()` in `src/punie/cli.py:106`**
  - Pattern: CLI flag > env var > default
  - `resolve_mode()` follows this exact pattern
  - Ensures consistent configuration precedence across Punie

- **`create_pydantic_agent()` in `src/punie/agent/factory.py`**
  - Current hardcoded instructions moved to `PUNIE_INSTRUCTIONS` constant
  - Factory updated to accept optional `AgentConfig` parameter
  - Backward compatible: no config = same as before

- **`LocalClient` in `src/punie/local/client.py`**
  - `_resolve_path()` method updated to use `resolve_workspace_path()`
  - Terminal `cwd` also goes through `_resolve_path()`
  - Ensures all file and directory operations are workspace-constrained

- **`MLXModel` in `src/punie/models/mlx.py`**
  - `from_pretrained()` updated with memory check before `mlx_load()`
  - Logs warning if insufficient memory, but doesn't block
  - Logs actual memory usage after successful load

### Related Phases

- **Phase 6.1: Local MLX Model** (agent-os/specs/2026-02-05-local-model-mlx/)
  - Added `MLXModel` with `mlx_lm.load()` integration
  - Established `KnownModelName` pattern with "local" alias
  - This spec adds memory monitoring to Phase 6.1's model loading

- **Phase 6.2: Model Download CLI** (agent-os/specs/2026-02-06-model-download-cli/)
  - Added `punie download` command with interactive model selection
  - Recommended 3B-4bit, 7B-4bit, 14B-4bit models
  - This spec adds memory size estimates for those three models

- **Phase 6.3: Standalone Local Tools** (agent-os/specs/2026-02-07-standalone-local-tools/)
  - Added `LocalClient` with `read_file`, `write_file`, `run_terminal_cmd`
  - Added `create_local_agent()` factory
  - This spec adds workspace safety to Phase 6.3's LocalClient

## External

### Python Standard Library

- **`dataclasses.dataclass`** — https://docs.python.org/3/library/dataclasses.html
  - Used for `AgentConfig` and `MemorySnapshot`
  - `frozen=True` for immutability

- **`pathlib.Path`** — https://docs.python.org/3/library/pathlib.html
  - `Path.resolve()` — canonicalize paths (resolve symlinks, `..`)
  - `Path.is_relative_to()` — check if path is within workspace

- **`resource.getrusage()`** — https://docs.python.org/3/library/resource.html
  - Used in `get_memory_snapshot()` for memory monitoring
  - Portable across macOS and Linux (Unix-only)
  - Returns RSS (Resident Set Size) and peak RSS

- **`os.sysconf()`** — https://docs.python.org/3/library/os.html#os.sysconf
  - Used in `check_memory_available()` to get total system RAM
  - `os.sysconf('SC_PHYS_PAGES') * os.sysconf('SC_PAGE_SIZE')`
  - Unix-only, adequate for Punie's target platforms

- **`ast.parse()`** — https://docs.python.org/3/library/ast.html#ast.parse
  - Used for Python syntax validation in `validate_python_syntax`
  - Catches malformed code from small local models
  - Only applied to fenced Python code blocks, not prose

### Security

- **Path Traversal Attacks**
  - OWASP: https://owasp.org/www-community/attacks/Path_Traversal
  - Mitigated by `resolve_workspace_path()` using `Path.resolve()` + `is_relative_to()`
  - Handles `..`, absolute paths, symlinks

- **Sandbox Escape via Symlinks**
  - Attack vector: symlink inside workspace pointing outside
  - Mitigation: `Path.resolve()` canonicalizes symlinks before `is_relative_to()` check
  - Example: `workspace/malicious_link -> /etc/passwd` would resolve to `/etc/passwd` and fail check

### Dependencies

- **Pydantic AI** — https://ai.pydantic.dev/
  - `PydanticAgent` and `Agent` classes
  - `create_pydantic_agent()` wraps Pydantic AI agent creation

- **MLX LM** — https://github.com/ml-explore/mlx-examples/tree/main/llms
  - `mlx_lm.load()` used in `MLXModel.from_pretrained()`
  - This spec adds memory check before calling `mlx_lm.load()`

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PUNIE_MODE` | `"acp"` | Execution mode: `"acp"` (PyCharm/RPC) or `"local"` (standalone) |
| `PUNIE_MODEL` | (varies) | Model to use, resolved by `resolve_model()` |
| `PUNIE_LOCAL_INSTRUCTIONS` | — | Not an env var, but a constant in `config.py` for local mode instructions |
| `PUNIE_INSTRUCTIONS` | — | Not an env var, but a constant in `config.py` for ACP mode instructions |

## Mode Switching Logic

```
punie serve
  → resolve_mode() → "acp" (default)
  → PunieAgent() with ACP client
  → PUNIE_INSTRUCTIONS (PyCharm-centric)
  → validate_python_syntax=False
  → No workspace safety (PyCharm handles paths)
  → No memory monitoring (PyCharm environment)

PUNIE_MODE=local punie serve
  → resolve_mode() → "local"
  → create_local_agent() with LocalClient
  → PUNIE_LOCAL_INSTRUCTIONS (standalone-centric)
  → validate_python_syntax=True
  → resolve_workspace_path() enforced on all paths
  → Memory check before MLX model load

punie serve --mode local
  → resolve_mode() → "local" (CLI flag takes priority)
  → Same as PUNIE_MODE=local above
```

## Testing Approaches

### Path Traversal Tests

- Relative traversal: `../../etc/passwd`
- Absolute paths outside: `/etc/passwd`
- Symlink escape: `workspace/link -> /outside`
- Dot components: `./foo/../bar`
- Absolute paths inside: `/full/path/to/workspace/file.txt` (allowed)

### Memory Monitoring Tests

- `MemorySnapshot` frozen dataclass check
- Positive RSS values
- MB conversion accuracy (bytes / 1024^2)
- `check_memory_available()` with large model size
- Model size estimation for known patterns (3B, 7B, 14B)
- Unknown model defaults to 4096MB

### Agent Configuration Tests

- Frozen dataclass check
- Default config uses `PUNIE_INSTRUCTIONS`
- Custom config construction
- Factory uses config instructions and model settings
- Syntax validation catches invalid Python
- Syntax validation skips prose
- `create_local_agent()` defaults to local instructions
- `resolve_mode()` default is "acp"
