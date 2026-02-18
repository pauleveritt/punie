# Monty Language Feature Report

*Date: 2026-02-17 | Monty version: 0.0.6 | Status: Experimental*

Monty is a minimal, sandboxed Python interpreter written in Rust by Pydantic (Samuel Colvin).
It is purpose-built for executing LLM-generated Python code safely — startup under 1μs, no filesystem/network access, host interaction only through developer-declared external functions.
Monty will power "code mode" in PydanticAI, where LLMs write Python that calls tools as functions instead of using traditional tool calling.

Repository: <https://github.com/pydantic/monty>

## Currently Supported Features (v0.0.6)

### Data Types

| Type | Notes |
|------|-------|
| `int` | Including arbitrary-precision BigInt |
| `float` | Full IEEE 754 |
| `bool` | |
| `str` | Extensive methods: split, join, replace, strip, startswith, endswith, partition, etc. |
| `bytes` | With methods: decode, endswith, startswith, etc. |
| `list` | With methods: append, insert, pop, remove, index, sort, etc. |
| `tuple` | With methods: index, count |
| `dict` | With methods: get, pop, popitem, keys, values, items, update, etc. |
| `set`, `frozenset` | Basic operations |
| `range` | Full range support |
| `slice` | Full slice syntax `[start:stop:step]` |
| `None`, `True`, `False`, `Ellipsis` | |
| `namedtuple` | |
| `dataclass` | Via `@dataclass` decorator, including `frozen=True` |

### Operators

All arithmetic (`+`, `-`, `*`, `/`, `//`, `%`, `**`), bitwise (`&`, `|`, `^`, `<<`, `>>`, `~`), comparison (`==`, `!=`, `<`, `<=`, `>`, `>=`, `is`, `is not`, `in`, `not in`), boolean (`and`, `or`, `not`), augmented assignment (`+=`, `-=`, etc.), and chained comparisons (`a < b < c`).

### Control Flow

- `if`/`elif`/`else`
- `for` loops (with `else` clause)
- `while` loops (with `else` clause)
- `break`, `continue`
- `try`/`except`/`else`/`finally` (full exception handling)
- Ternary expressions (`x if cond else y`)

### Functions

- `def` and `async def`
- `lambda` (full parameter support, closures, nested)
- Closures via cell-based variable capture
- All parameter varieties: positional-only (`/`), keyword-only (`*`), `*args`, `**kwargs`, defaults
- Nested functions, recursion (configurable depth limit)

### Expressions

- Walrus operator (`:=`) — comprehensive support including in `if`, `while`, comprehensions, f-strings
- `await` (including module-level)
- F-strings with full format specs (`f"{x:.2f}"`, `f"{x!r}"`, `f"{x:>10}"`, debug `=`)

### Comprehensions

- List, set, dict comprehensions with filters and nested `for` clauses
- Generator expressions (parsed but treated as list comprehensions — not lazy)
- Scope isolation

### Unpacking

- Tuple unpacking in assignment and `for` loops: `a, b = (1, 2)`
- Nested unpacking: `(a, b), c = ((1, 2), 3)`
- Starred unpacking: `first, *rest = [1, 2, 3, 4]`
- `*args` and `**kwargs` in function calls (single each)

### Scoping

- `global` and `nonlocal` declarations
- Proper LEGB scoping rules

### Exceptions

Full hierarchy: `BaseException`, `Exception`, `ArithmeticError`, `OverflowError`, `ZeroDivisionError`, `LookupError`, `IndexError`, `KeyError`, `RuntimeError`, `NotImplementedError`, `RecursionError`, `AttributeError`, `FrozenInstanceError`, `NameError`, `UnboundLocalError`, `ValueError`, `UnicodeDecodeError`, `ImportError`, `ModuleNotFoundError`, `OSError`, `FileNotFoundError`, `FileExistsError`, `IsADirectoryError`, `NotADirectoryError`, `AssertionError`, `MemoryError`, `StopIteration`, `SyntaxError`, `TimeoutError`, `TypeError`.

### Async/Await

- `async def` functions, `await` expressions
- `asyncio.gather()` support
- External futures (host acts as event loop)

### Built-in Functions (27 implemented)

`abs`, `all`, `any`, `bin`, `chr`, `divmod`, `enumerate`, `hash`, `hex`, `id`, `isinstance`, `len`, `map`, `max`, `min`, `next`, `oct`, `ord`, `pow`, `print`, `repr`, `reversed`, `round`, `sorted`, `sum`, `type`, `zip`

**Not yet implemented:** `aiter`, `anext`, `ascii`, `breakpoint`, `callable`, `classmethod`, `compile`, `delattr`, `dir`, `eval`, `exec`, `filter`, `format`, `getattr`, `globals`, `hasattr`, `help`, `input`, `issubclass`, `iter` (as function), `locals`, `memoryview`, `object`, `open`, `property`, `setattr`, `slice` (constructor), `staticmethod`, `super`, `vars`, `__import__`

### Built-in Modules (5, all partial)

| Module | What works |
|--------|-----------|
| `sys` | `version_info`, `platform`, `monty_version` |
| `typing` | `TYPE_CHECKING`, `Any`, `Optional`, `Union`, `NoReturn`, `Callable`, `ClassVar`, `Final`, `Literal`, `TypeAlias` as markers |
| `asyncio` | `gather()` only |
| `pathlib` | `Path` with `read_text`, `write_text`, etc. (via OS calls) |
| `os` | `getenv()`, `environ` (via OS calls) |

### Imports

- `import sys` (single-module only)
- `from typing import TYPE_CHECKING`
- `if TYPE_CHECKING:` guard (imports silently ignored at runtime)

### Other

- `assert` with optional message
- Serialization: snapshot/resume of interpreter state mid-execution
- Resource limits: memory, allocations, stack depth, execution time
- stdout/stderr capture
- REPL support (suspendable as of v0.0.6)

## Not Supported (Explicitly Blocked)

| Feature | Error | README status |
|---------|-------|---------------|
| **Class definitions** (`class Foo:`) | `NotImplementedError: class definitions` | "should come soon" |
| **Match/case** (pattern matching) | `NotImplementedError: pattern matching` | "should come soon" |
| **Context managers** (`with`) | `NotImplementedError: context managers` | — |
| **`del` statement** | `NotImplementedError: the 'del' statement` | — |
| **`yield` / `yield from`** (generators) | `NotImplementedError: yield expressions` | — |
| **`raise ... from ...`** (exception chaining) | Opcode removed from VM | — |
| **`async for`** | `NotImplementedError: async for loops` | — |
| **`async with`** | `NotImplementedError: async context managers` | — |
| **Exception groups** (`try*/except*`) | `NotImplementedError: exception groups` | — |
| **Type aliases** (`type X = ...`) | `NotImplementedError: type aliases` | — |
| **Template strings** (t-strings) | `NotImplementedError: template strings` | — |
| **Complex numbers** (`3+4j`) | `NotImplementedError: complex constants` | — |
| **`@` matrix multiply** | Opcode exists, raises error | — |
| **Dict unpacking in literals** (`{**d}`) | `NotImplementedError` | — |
| **Wildcard imports** (`from x import *`) | `NotImplementedError` | — |
| **Multi-module imports** (`import a, b`) | Only single-module supported | — |
| **Relative imports** | `ImportError` | — |
| **Decorators** (beyond `@dataclass`) | Not implemented | — |
| **Standard library** (beyond 5 partial modules) | Not available | — |
| **Third-party libraries** | Not available | — |

## Known Behavioral Differences from CPython

From test xfail markers:

- Generator expressions return `list` type, not `generator` (not lazy)
- Dict `.keys()`, `.values()`, `.items()` return lists, not dict views
- `id()` semantics differ (bytes literals, non-overlapping lifetimes)
- F-string spec checking is stricter than CPython
- Star imports blocked entirely
- `list += int` has a known bug

## LLM Compatibility Gaps

Issues [#163](https://github.com/pydantic/monty/issues/163) and [#172](https://github.com/pydantic/monty/issues/172) document patterns real LLMs generate that Monty cannot yet handle:

1. `sorted([3,1,2], key=lambda x: -x)` — keyword args to `sorted()` not supported
2. `sorted([3,1,2], reverse=True)` — same
3. `sorted([(2,'b'),(1,'a')])` — tuple comparison inside `sorted()` fails
4. `{1,2} | {3,4}` / `&` / `-` — set operators not supported
5. `d["a"]["b"] = 2` — chained subscript assignment fails
6. GPT 5.2 frequently returns futures instead of awaiting them (issue #172)

## What's Coming: Active PRs and Issues (Next ~6 Months)

### High Confidence (Active PRs, likely weeks)

| Feature | PR/Issue | Status | Impact |
|---------|----------|--------|--------|
| **Dataclass methods** | [PR #175](https://github.com/pydantic/monty/pull/175) (+806 lines, by samuelcolvin) | Open, in review | Fills out dataclass support |
| **User-defined function calling improvements** | [PR #180](https://github.com/pydantic/monty/pull/180) (+233/-206, by davidhewitt) | Open, in review | Better function call semantics |
| **`datetime` module** (fixed-offset) | [PR #171](https://github.com/pydantic/monty/pull/171) (+4568 lines, by mwildehahn) | Open, community PR | `datetime`, `date`, `time`, `timedelta`, `timezone` |
| **`re` module** (regex) | [PR #157](https://github.com/pydantic/monty/pull/157) (+1748 lines, by Embers-of-the-Fire) | Open, community PR | `re.match`, `re.search`, `re.findall`, etc. |
| **Filesystem mount** | [Issue #176](https://github.com/pydantic/monty/issues/176) (assigned to davidhewitt) | Design phase | Read/write/overlay directory mounting with strict security |
| **REPL exception handling** | [PR #178](https://github.com/pydantic/monty/pull/178) | Open, community PR | Keep REPL alive after exceptions |
| **HeapGuard refactoring** | PRs #179, #170, #166, #143 (by davidhewitt) | Ongoing, many merged | Internal safety improvement |

### Medium Confidence (Open Issues, likely 1-3 months)

| Feature | Issue | Notes |
|---------|-------|-------|
| **Class definitions** | README "coming soon" | Highest-impact missing feature. Needed for many LLM patterns. No PR yet. |
| **Match/case** (pattern matching) | README "coming soon" | Listed as coming soon but no active work visible. |
| **`collections` module** (`Counter`, `defaultdict`, `deque`) | [Issue #181](https://github.com/pydantic/monty/issues/181) (filed by dmontagu/Pydantic team) | Claude Code uses `Counter` frequently |
| **LLM compatibility fixes** (sorted kwargs, set operators, chained subscript assignment) | [Issue #163](https://github.com/pydantic/monty/issues/163) | Pragmatic fixes for common LLM patterns |
| **Auto-await trailing futures** | [Issue #172](https://github.com/pydantic/monty/issues/172) (filed by samuelcolvin) | GPT 5.2 frequently forgets to await |
| **`json` module** | README "coming soon" | Listed alongside dataclasses |

### Lower Confidence (Discussed but no timeline)

| Feature | Issue | Notes |
|---------|-------|-------|
| **Runtime type annotation enforcement** | [Issue #134](https://github.com/pydantic/monty/issues/134) | Samuel Colvin "thumbs-up but not until more stable release" |
| **crates.io publishing** | [Issue #148](https://github.com/pydantic/monty/issues/148) | Blocked on Astral publishing ruff crates |
| **Context managers** (`with`) | Not discussed | No issue or PR |
| **Generators** (`yield`) | Not discussed | No issue or PR |
| **`del` statement** | Not discussed | No issue or PR |
| **Exception chaining** (`raise from`) | TODO in parse.rs | No issue or PR |

## Assessment for Punie

### What works well today

Monty v0.0.6 already covers the core patterns Punie needs for Code Mode:
- Function calls with all parameter varieties
- All data types used in tool results (dict, list, str, int, bool)
- F-strings for formatting output
- Try/except for error handling
- Async/await for concurrent tool calls
- Comprehensions for data transformation
- Walrus operator for inline assignment

### What's missing that matters

For Punie's domain-tool / holy-grail vision:

1. **Class definitions** — needed if Monty-generated code should define Pydantic models or custom types. Currently Punie works around this by passing structured results as dicts. Critical for Milestone 2+ of the holy grail architecture.

2. **Context managers** — would be needed for resource management patterns in generated code. Lower priority since external functions handle cleanup.

3. **`json` module** — frequently needed for parsing API responses and formatting structured data. Listed as "coming soon."

4. **Standard library gaps** — `collections.Counter`, `re`, `datetime` are all in active PRs, which is encouraging.

### Recommendation

Monty is iterating extremely fast (6 releases in 3 weeks, 15+ merged PRs in February alone).
The project is less than a month old.
For Punie's purposes:

- **Today**: Monty v0.0.6 is sufficient for Code Mode with the current 14 external functions
- **1 month**: Expect dataclass methods, datetime, re, and possibly class definitions
- **3 months**: Expect class definitions, match/case, collections, json, and major LLM compatibility fixes
- **6 months**: Expect a substantially complete Python subset suitable for most LLM-generated code patterns

The main risk is that class definitions have no PR yet despite being listed as "coming soon" — this is the single most impactful missing feature for both general LLM code and Punie's holy grail architecture.

## Key People

| Person | Role |
|--------|------|
| **Samuel Colvin** (samuelcolvin) | Pydantic founder, primary architect |
| **David Hewitt** (davidhewitt) | Core Rust dev (PyO3 maintainer), HeapGuard architecture |
| **David Montague** (dmontagu) | Pydantic team, filed collections issue |
| **Petyo** (petyosi) | Handles releases/versioning |

## References

- [Monty README](https://github.com/pydantic/monty/blob/main/README.md)
- [Issue #117 — Why not RustPython?](https://github.com/pydantic/monty/issues/117) — Samuel explains design philosophy, mentions meeting with Guido van Rossum
- [Issue #163 — LLM compatibility gaps](https://github.com/pydantic/monty/issues/163)
- [Issue #172 — Unawaited futures](https://github.com/pydantic/monty/issues/172)
- [Issue #134 — Runtime type enforcement proposal](https://github.com/pydantic/monty/issues/134)
- [Issue #176 — Filesystem mount design](https://github.com/pydantic/monty/issues/176)
- Local source: `/Users/pauleveritt/PycharmProjects/monty/crates/monty/src/parse.rs` (supported/unsupported features)
- Local source: `/Users/pauleveritt/PycharmProjects/monty/crates/monty/src/builtins/mod.rs` (builtin functions)
