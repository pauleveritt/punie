# Shape: Comprehensive Examples

## Problem Statement

Punie's `examples/` directory contains only `hello_world.py`, making it difficult for developers to understand:
- How to use ACP SDK primitives (schema models, content blocks, tool calls)
- How to leverage contrib utilities (SessionAccumulator, ToolCallTracker)
- How to establish and manage ACP connections
- What future integration patterns (Pydantic AI, dynamic discovery) will look like

## Scope Decisions

### In Scope

1. **Progressive learning path** — 9 numbered examples building from basic schema to full connection lifecycle
2. **Self-contained execution** — Each example runs standalone with `python examples/NN_*.py`
3. **Tiered approach:**
   - Tier 1: Sync, schema-only (no network)
   - Tier 2: Async, self-contained TCP loopback
   - Tier 3: Aspirational (schema works, future patterns documented)
4. **Auto-testing integration** — Existing `tests/test_examples.py` discovers all examples automatically

### Out of Scope

1. **External PyCharm dependency** — Examples use in-process fakes, not real PyCharm connections
2. **Test infrastructure changes** — No modifications to `test_examples.py` needed
3. **Breaking changes** — All new files, no modifications to existing SDK or test helpers
4. **Jupyter notebooks or interactive demos** — Pure Python files only

## Key Constraints

1. **Self-contained convention** — Each example must have module docstring, `main()` with assertions, and `__main__` guard
2. **No pytest fixtures in examples** — Examples can't depend on test harness
3. **Import discipline** — Example 07 imports from `tests.acp_helpers`, which requires either running via pytest or adding project root to sys.path
4. **Python 3.14.2t** — Free-threaded Python, async/await support

## Success Criteria

1. All 9 examples run successfully: `uv run python examples/NN_*.py`
2. Full test suite passes: `uv run pytest -v`
3. Examples demonstrate progressive complexity
4. Aspirational examples (08, 09) clearly mark future functionality in docstrings
5. Roadmap 1.2 marked complete

## References

- **Shaping conversation** — Transcript at `~/.claude/projects/-Users-pauleveritt-projects-pauleveritt-punie/e0102304-39c4-4902-86d0-5f118bf35b81.jsonl`
- **Existing convention** — `examples/hello_world.py`
- **Test infrastructure** — `tests/test_examples.py`
- **ACP helpers** — `tests/acp_helpers.py` (_Server, FakeAgent, FakeClient)
- **SDK patterns** — `tests/test_acp_sdk.py`
