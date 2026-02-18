# LibCST Architecture Report

*Date: 2026-02-17 | LibCST version: 1.8.6 | Status: Research*

LibCST is Meta's Concrete Syntax Tree library for Python — a lossless parser that preserves
every byte of whitespace, comment, and formatting while enabling safe, programmatic code
transformation.

Local source: `~/PycharmProjects/LibCST`

---

## 1. Executive Summary

LibCST provides a **lossless, round-trippable Python parser** with a rich transformation
framework. Unlike the standard `ast` module, LibCST preserves whitespace and comments,
enabling automated refactoring tools that produce diffs humans can review.

**Size:** ~101K lines Python, ~18K lines Rust — a substantial but well-organized codebase.

**Dependencies:** Minimal at runtime — only PyYAML (version varies by Python). No other
runtime dependencies. This is remarkably lean for a 100K+ line project.

**Two motivations for this report:**

### Agent-Driven Usage: Strong Case

LibCST fills a gap in Punie's current tool coverage. The 14 existing tools are all
**read-only** navigation (LSP: goto_definition, find_references, hover) or **execution**
(ruff, pytest, typecheck, git). LibCST enables **write operations**: rename a symbol,
add an import, restructure code. The external-function pattern used for all existing tools
applies directly — LibCST runs outside Monty and returns Pydantic result models.

**Verdict: High value, low implementation risk.** Three proposed tools:
`cst_find_pattern`, `cst_rename`, `cst_add_import`.

### Monty Feasibility: Two Paths

**Path A — External tool (works today):** LibCST runs as an external function; Monty
code inspects the result. Same pattern as `typecheck()`, `ruff_check()`, `pytest_run()`.
Zero Monty compatibility issues.

**Path B — Monty-native mini-CST (interesting, feasible for subset):** A recursive-descent
parser written using only Monty primitives (strings, dicts, lists, functions, recursion)
could parse Python source into a dict-based tree. The key insight: *a parser treats
Python syntax as data — it doesn't need to run the code it parses*. A Monty-native
tokenizer + parser can handle `class`, `yield`, `with`, `match/case`, and all other
syntax blocked by Monty, because those constructs become dict nodes, not running code.
Estimated effort: ~1,500 lines for a useful subset (~30% of LibCST's features).

---

## 2. Architecture Overview

### Package Structure

```
libcst/
├── _nodes/              # Core node definitions (~10,222 lines, 9 files)
│   ├── base.py          # CSTNode base class (499 lines)
│   ├── expression.py    # Expression nodes (4,067 lines)
│   ├── statement.py     # Statement nodes (3,871 lines)
│   ├── module.py        # Module root node (165 lines)
│   └── op.py            # Operator nodes (1,031 lines)
├── _parser/             # Parser infrastructure
│   ├── entrypoints.py   # parse_module(), parse_statement(), parse_expression()
│   ├── conversions/     # CST conversion (expression: 1,630, statement: 1,381 lines)
│   └── parso/           # Tokenizer (tokenize.py: 1,155 lines)
├── metadata/            # Metadata providers (~7,701 lines)
│   ├── wrapper.py       # MetadataWrapper (222 lines)
│   ├── base_provider.py # BaseMetadataProvider (171 lines)
│   └── scope_provider.py # ScopeProvider (1,254 lines)
├── matchers/            # Pattern matching system
│   ├── __init__.py      # Public API (16,680 lines, auto-generated)
│   └── _matcher_base.py # Combinator logic (1,943 lines)
├── codemod/             # Codemod framework
│   ├── _command.py      # CodemodCommand base
│   └── visitors/        # AddImportsVisitor, RemoveImportsVisitor, etc.
├── _visitors.py         # CSTVisitor + CSTTransformer
└── _typed_visitor.py    # Auto-generated type stubs (7,669 lines)

native/                  # Rust PEG parser
├── libcst/              # Main Rust crate
│   ├── src/
│   │   ├── lib.rs       # Library entry point
│   │   ├── py.rs        # PyO3 Python bindings
│   │   ├── nodes/       # Node definitions (15 subdirectories)
│   │   ├── parser/      # Parser implementation (6 subdirectories)
│   │   └── tokenizer/   # Tokenizer (9 subdirectories)
│   └── Grammar          # Python grammar specification (32 KB)
└── libcst_derive/       # Procedural macros for node derivation
```

### Data Flow

```
source code (str or bytes)
    │
    ▼ parse_module() / parse_expression() / parse_statement()
    │
    ▼ native.parse_module() [Rust, via PyO3]
    │
    ▼ peg crate PEG parser → tokenize → parse → deflated CST
    │
    ▼ whitespace inflation (attach comments, blank lines to adjacent nodes)
    │
    ▼ frozen dataclass tree rooted at Module
    │
    ├──▶ CSTVisitor.visit()      → read-only traversal, collect info
    │
    ├──▶ CSTTransformer.visit()  → new tree with substitutions
    │         │
    │         ▼ MetadataWrapper.resolve() (optional: ScopeProvider, etc.)
    │
    ▼ module.code  [CodegenState token accumulation]
    │
    ▼ source code (round-tripped, byte-for-byte identical if unmodified)
```

### Size Breakdown by Component

| Component | Lines | Notes |
|-----------|-------|-------|
| Matchers (generated) | 16,680 | Auto-generated from node types |
| Visitor type stubs (generated) | 7,669 | Auto-generated visit/leave methods |
| Node definitions | ~10,222 | expression, statement, op, module, base |
| Metadata system | ~7,701 | scope, types, positions, dependencies |
| Parser (Python) | ~6,000 | Conversion, tokenizer bridge |
| Codemod framework | ~5,000 | Commands, visitors, parallel execution |
| Rust parser | ~18,000 | PEG grammar + PyO3 bindings + tokenizer |
| **Total Python** | **~101,443** | Across all `.py` files |

---

## 3. Core Data Model

### CSTNode Base Class (`_nodes/base.py`, 499 lines)

All tree nodes inherit from `CSTNode`, which is declared as an abstract frozen dataclass:

```python
@dataclass(frozen=True)
class CSTNode(ABC):
    __slots__: ClassVar[Sequence[str]] = ()

    def __post_init__(self) -> None:
        self._validate()
```

The frozen dataclass pattern provides:
- **Immutability** after construction — prevents accidental tree corruption
- **Identity equality** — `node1 == node2` is `True` only if `node1 is node2`
- **Structural equality** via `deep_equals()` — compares field values recursively
- **Hashability** for use as dict keys in metadata lookups

**Key methods:**

| Method | Purpose |
|--------|---------|
| `with_changes(**changes)` | Create new node with updated fields via `dataclasses.replace()` |
| `_codegen_impl(state: CodegenState)` | Abstract; each subclass emits tokens |
| `_visit_and_replace_children(visitor)` | Abstract; each subclass handles child traversal |
| `visit(visitor)` | Main entry point: calls `on_visit`, recurse, `on_leave` |
| `deep_clone()` | Recursively clone entire subtree (new object identities) |
| `deep_equals(other)` | Structural equality, not identity |
| `deep_replace(old, new)` | Replace node by identity throughout subtree |
| `deep_remove(old)` | Remove node by identity throughout subtree |
| `validate_types_shallow()` | Check field types at this node |
| `validate_types_deep()` | Recursively validate entire subtree |

### Module Root Node (`_nodes/module.py`, 165 lines)

`Module` is the root of every parsed tree:

```python
@add_slots
@dataclass(frozen=True)
class Module(CSTNode):
    body: Sequence[Union[SimpleStatementLine, BaseCompoundStatement]]
    header: Sequence[EmptyLine] = ()      # Comments before first statement
    footer: Sequence[EmptyLine] = ()      # Trailing whitespace/comments
    encoding: str = "utf-8"
    default_indent: str = "    "
    default_newline: str = "\n"
    has_trailing_newline: bool = True

    @property
    def code(self) -> str: ...            # Reconstruct source string
    @property
    def bytes(self) -> bytes: ...         # Encode with self.encoding
    def code_for_node(self, node: CSTNode) -> str: ...  # Codegen for subtree
    def get_docstring(self, clean: bool = True) -> Optional[str]: ...
```

### Node Hierarchy

- **~100 expression types** in `expression.py` (4,067 lines): `Name`, `Integer`, `Float`,
  `SimpleString`, `FormattedString`, `ConcatenatedString`, `BinaryOperation`,
  `UnaryOperation`, `BooleanOperation`, `Comparison`, `Call`, `Attribute`, `Subscript`,
  `Index`, `Slice`, `IfExp`, `Lambda`, `Yield`, `Await`, `GeneratorExp`, `ListComp`,
  `SetComp`, `DictComp`, `List`, `Tuple`, `Set`, `Dict`, `Param`, `Parameters`, `Arg`, etc.

- **~60 statement types** in `statement.py` (3,871 lines): `FunctionDef`, `ClassDef`,
  `If`, `For`, `While`, `Try`, `With`, `Return`, `Import`, `ImportFrom`, `Assign`,
  `AugAssign`, `AnnAssign`, `Raise`, `Del`, `Pass`, `Break`, `Continue`, `Global`,
  `Nonlocal`, `Assert`, etc.

- **6 whitespace types**: `SimpleWhitespace`, `ParenthesizedWhitespace`, `EmptyLine`,
  `TrailingWhitespace`, `MaybeSentinel`, `MaybeWhitespace`

- **~30 operator types** in `op.py` (1,031 lines): `Add`, `Subtract`, `Multiply`,
  `Divide`, `Modulo`, `And`, `Or`, `Not`, `BitAnd`, `BitOr`, `BitXor`, etc.

### Whitespace Preservation

Each node **owns its surrounding whitespace**. For example, a `Name` node carries its
`lpar` (left parentheses with whitespace) and `rpar` fields. A `BinaryOperation` node
carries `whitespace_before` and `whitespace_after` on its operator. This is why LibCST
can reconstruct source byte-for-byte: nothing is thrown away during parsing.

---

## 4. Parser

### Rust PEG Parser Architecture

The parser lives in `native/libcst/` — a Rust crate that compiles to a Python
extension module (`libcst_native`) via PyO3 and maturin.

**Key Rust dependencies:**
- `peg = "0.8.5"` — Parser Expression Grammar library (generates recursive-descent code from grammar rules)
- `pyo3 = "0.26"` — Rust-Python FFI bindings
- `thiserror = "2.0.12"` — Error handling
- `regex = "1.11.2"`, `memchr = "2.7.4"` — Tokenizer support
- `libcst_derive` — Procedural macros for node type derivation

The grammar specification lives in `native/libcst/Grammar` (32 KB), describing the full
Python grammar as PEG rules.

### Two-Phase Parse

1. **Tokenize + deflated parse:** The PEG parser processes tokens and builds a "deflated"
   CST where whitespace tokens are attached as raw strings, not yet associated with
   specific nodes.

2. **Whitespace inflation:** A second pass walks the deflated CST and assigns each
   whitespace token to the appropriate adjacent node — either as `leading_lines`,
   `trailing_whitespace`, or inline spacing fields on operator nodes.

This two-phase approach is why LibCST can guarantee lossless round-trips: the inflation
step is deterministic and reversible.

### Entry Points (`_parser/entrypoints.py`)

```python
def parse_module(source: Union[str, bytes],
                 config: PartialParserConfig = ...) -> Module: ...

def parse_statement(source: str,
                    config: PartialParserConfig = ...) -> Union[
                        SimpleStatementLine, BaseCompoundStatement]: ...

def parse_expression(source: str,
                     config: PartialParserConfig = ...) -> BaseExpression: ...
```

The Python entry points delegate immediately to `native.parse_module()`,
`native.parse_statement()`, or `native.parse_expression()` (the Rust extension).

*Note:* LibCST once had a pure-Python fallback parser (`_parser/parso/`); the Rust
parser is now the sole implementation.

---

## 5. Code Generation

### CodegenState Token Accumulator

Every `CSTNode` subclass implements `_codegen_impl(state: CodegenState)`, which appends
string tokens to a `CodegenState` accumulator:

```python
# From Module._codegen_impl:
def _codegen_impl(self, state: CodegenState) -> None:
    for h in self.header:
        h._codegen(state)
    for stmt in self.body:
        stmt._codegen(state)
    for f in self.footer:
        f._codegen(state)
    if self.has_trailing_newline:
        if len(state.tokens) == 0:
            state.add_token(state.default_newline)
    else:
        state.pop_trailing_newline()
```

`CodegenState` carries `default_indent`, `default_newline`, and a `tokens: list[str]`
accumulator. The final source string is `"".join(state.tokens)`.

### Round-Trip Guarantee

Because whitespace is preserved in the tree (see Section 3) and every node faithfully
emits it during codegen, `parse_module(source).code == source` is guaranteed for any
valid Python source. This is LibCST's defining feature — transformers only change the
nodes they explicitly modify.

---

## 6. Visitor/Transformer

### CSTVisitor (read-only)

```python
class CSTVisitor(CSTTypedVisitorFunctions, MetadataDependent):
    def on_visit(self, node: CSTNode) -> bool:
        visit_func = getattr(self, f"visit_{type(node).__name__}", None)
        retval = visit_func(node) if visit_func else True
        return False if retval is False else True

    def on_leave(self, original_node: CSTNode) -> None:
        leave_func = getattr(self, f"leave_{type(original_node).__name__}", None)
        if leave_func:
            leave_func(original_node)
```

### CSTTransformer (produces new tree)

```python
class CSTTransformer(CSTTypedTransformerFunctions, MetadataDependent):
    def on_visit(self, node: CSTNode) -> bool:
        visit_func = getattr(self, f"visit_{type(node).__name__}", None)
        retval = visit_func(node) if visit_func else True
        return False if retval is False else True

    def on_leave(self, original_node: CSTNodeT,
                 updated_node: CSTNodeT) -> Union[
                     CSTNodeT, RemovalSentinel, FlattenSentinel[CSTNodeT]]:
        leave_func = getattr(self, f"leave_{type(original_node).__name__}", None)
        if leave_func:
            updated_node = leave_func(original_node, updated_node)
        return updated_node
```

### Dispatch Mechanism

Method lookup is **dynamic string concatenation**:
- `visit_FunctionDef(node)` — called on entering a `FunctionDef` node
- `leave_FunctionDef(original, updated)` — called on leaving, with the potentially-modified node

The typed visitor base classes (`CSTTypedVisitorFunctions`, `CSTTypedTransformerFunctions`)
are auto-generated (7,669 lines in `_typed_visitor.py`) to provide type-annotated no-op
stubs for every node type. This enables IDE autocomplete while keeping dispatch runtime-dynamic.

### Per-Attribute Hooks

Beyond node-level dispatch, both `CSTVisitor` and `CSTTransformer` support attribute-level hooks:
- `visit_FunctionDef_body(node)` — called before visiting the `body` attribute
- `leave_FunctionDef_body(node)` — called after visiting the `body` attribute

### Special Return Values (CSTTransformer only)

| Return value | Effect |
|---|---|
| `updated_node` | Replace original with this node |
| `RemovalSentinel.REMOVE` | Remove node from its parent sequence |
| `FlattenSentinel([...])` | Replace node with zero or more nodes in parent sequence |

### Bottom-Up Tree Reconstruction

Transformers use a **bottom-up** strategy: children are visited and potentially replaced
before the parent's `leave_` method fires. The `updated_node` argument to `leave_X`
already has transformed children. This means you can safely inspect children in `leave_`
hooks.

### BatchableCSTVisitor

For performance when multiple passes are needed, `BatchableCSTVisitor` lets several
read-only visitors share a single tree traversal. `MetadataWrapper.visit_batched()`
orchestrates this.

---

## 7. Metadata System

### MetadataWrapper

`MetadataWrapper` is the gateway to all computed metadata:

```python
class MetadataWrapper:
    def __init__(self, module: Module, unsafe_skip_copy: bool = False,
                 cache: Mapping[ProviderT, object] = {}) -> None:
        if not unsafe_skip_copy:
            module = module.deep_clone()   # Creates new object identities!
        self.__module = module
        self._metadata = {}
        self._cache = cache
```

The deep clone is essential: metadata is keyed by **node identity** (`id(node)`), not
structural equality. Two syntactically identical `Name("foo")` nodes in different
positions in the tree must have different metadata. The clone ensures every node in
`MetadataWrapper.module` is a unique object.

### Provider Dependency Resolution

Providers declare their dependencies, and the wrapper resolves them in topological order:

```python
def _resolve_impl(wrapper, providers):
    completed = set(wrapper._metadata.keys())
    remaining = _gather_providers(set(providers), set()) - completed

    while remaining:
        batchable = set()
        for P in remaining:
            if set(P.METADATA_DEPENDENCIES).issubset(completed):
                if issubclass(P, BatchableMetadataProvider):
                    batchable.add(P)
                else:
                    wrapper._metadata[P] = P()._gen(wrapper)
                    completed.add(P)
        # Run batchable providers together in single traversal
        metadata_batch = _gen_batchable(wrapper, [p() for p in batchable])
        wrapper._metadata.update(metadata_batch)
        completed |= batchable
        remaining -= completed
```

### Key Metadata Providers

| Provider | Lines | What it computes |
|----------|-------|-----------------|
| `ScopeProvider` | 1,254 | Variable bindings, assignments, accesses across scope hierarchy |
| `QualifiedNameProvider` | ~200 | Fully-qualified dotted names (e.g. `os.path.join`) |
| `PositionProvider` | ~150 | Line/column position for every node |
| `ExpressionContextProvider` | ~100 | Whether a `Name` is LOAD, STORE, or DEL context |
| `ParentNodeProvider` | ~80 | Parent node for every node |
| `TypeInferenceProvider` | ~300 | Type information (requires Pyre/external type checker) |

### Scope Hierarchy

`ScopeProvider` builds a scope tree reflecting Python's LEGB rules:
- `BuiltinScope` → `GlobalScope` → `FunctionScope` → `ClassScope` → `ComprehensionScope`

Each scope tracks `assignments` (all `BaseAssignment` objects created in that scope)
and `accesses` (all `Access` objects that refer to names in that scope). Cross-scope
references are resolved at the `Access` level via `__assignments` back-links.

---

## 8. Matchers

The matchers system provides **declarative pattern matching** against CST nodes.

### Basic Usage

```python
import libcst as cst
import libcst.matchers as m

tree = cst.parse_module("print('hello')\nx = foo(1, 2)")

# Find all calls to 'print'
calls = m.findall(tree, m.Call(func=m.Name("print")))

# Check if a node matches a pattern
m.matches(node, m.FunctionDef(name=m.Name("my_func")))

# Extract values from matches
result = m.extract(node, m.Call(
    func=m.Name(value=m.SaveMatchedNode(m.DoNotCare(), "func_name"))
))
# result = {"func_name": "print"}

# Replace matching nodes
new_tree = m.replace(tree, m.Name("old_name"),
                     lambda node, _: node.with_changes(value="new_name"))
```

### Core Functions

| Function | Purpose |
|----------|---------|
| `matches(node, pattern)` | Returns `True` if node matches pattern |
| `findall(node, pattern)` | Returns list of all matching nodes in subtree |
| `extract(node, pattern)` | Returns dict of `SaveMatchedNode` captures, or `None` |
| `extractall(node, pattern)` | Returns list of all capture dicts |
| `replace(node, pattern, visitor)` | Transform all matching nodes |

### Combinators

| Combinator | Meaning |
|------------|---------|
| `DoNotCare()` | Match any value (wildcard) |
| `OneOf(a, b, c)` | Match any of the given patterns |
| `AllOf(a, b)` | Match all patterns simultaneously |
| `DoesNotMatch(p)` | Inverse of `matches(p)` |
| `MatchIfTrue(fn)` | Match if `fn(node)` returns `True` |
| `MatchRegex(pattern)` | Match string value against regex |
| `SaveMatchedNode(p, name)` | Match `p` and capture result under `name` |
| `ZeroOrMore()` | Match zero or more items in a sequence |
| `ZeroOrOne()` | Match zero or one item in a sequence |
| `AtLeastN(p, n)` | Match at least N items matching `p` |
| `AtMostN(p, n)` | Match at most N items matching `p` |
| `TypeOf(T1, T2)` | Match nodes of the given types |

### Decorator Integration

Visitor methods can be gated on matchers using decorators:

```python
from libcst.matchers import visit, call_if_inside, call_if_not_inside

class MyTransformer(MatcherDecoratableTransformer):
    @visit(m.FunctionDef(name=m.Name("old_name")))
    def on_function_def(self, node):
        # Only called for FunctionDefs named "old_name"
        ...

    @call_if_inside(m.ClassDef())
    def visit_FunctionDef(self, node):
        # Only called for methods, not top-level functions
        ...
```

The `matchers/__init__.py` is auto-generated (16,680 lines) from the node type hierarchy,
producing a mirror class for every CST node type that accepts `None`/`DoNotCare` for
any field.

---

## 9. Codemod Framework

### Primary Base Class: ContextAwareTransformer

```python
class ContextAwareTransformer(Codemod, MatcherDecoratableTransformer):
    """Primary base class for codemods. Subclass this for most use cases."""

    def __init__(self, context: CodemodContext) -> None:
        Codemod.__init__(self, context)
        MatcherDecoratableTransformer.__init__(self)

    def transform_module_impl(self, tree: cst.Module) -> cst.Module:
        return tree.visit(self)
```

### CodemodCommand

High-level base for CLI-invocable commands:

```python
class CodemodCommand(Codemod, ABC):
    DESCRIPTION: str = "No description."

    @staticmethod
    def add_args(arg_parser: argparse.ArgumentParser) -> None: ...

    @abstractmethod
    def transform_module_impl(self, tree: Module) -> Module: ...
```

After `transform_module_impl` returns, `CodemodCommand` automatically runs
`AddImportsVisitor` and `RemoveImportsVisitor` to handle import hygiene.

### Import Management

Two built-in visitors make import management declarative:

```python
# Add an import (batched, deduped automatically)
AddImportsVisitor.add_needed_import(context, "typing", "Optional")

# Remove an import when no longer needed
RemoveImportsVisitor.remove_unused_import(context, "typing", "Optional")
```

These are scheduled visitors — they run as a post-processing step, not inline.

### 17 Built-in Commands

LibCST ships with 17 codemod commands (`libcst.codemod.commands`):

- `rename_module` — Rename a module and update all imports
- `convert_type_comments` — Convert `# type: ignore` to annotations
- `add_trailing_comma` — Add trailing commas to multi-line function calls
- `remove_unused_imports` — Remove imports that are never used
- `replace_union_syntax` — Convert `Union[X, Y]` to `X | Y`
- `order_default_params` — Reorder params so non-default come before default
- ...and 11 more

### CLI and Parallel Execution

```bash
python -m libcst.tool codemod rename_module --path src/ OldName NewName
```

The codemod runner supports parallel execution across multiple files using Python's
`multiprocessing` module.

---

## 10. Assessment — Agent-Driven Usage

### 10.1 High-Value Operations for an Agent

| Operation | LibCST API | Complexity |
|-----------|-----------|------------|
| Find all calls to X | `m.findall(tree, m.Call(func=m.Name("X")))` | Simple |
| Find all function signatures | `m.findall(tree, m.FunctionDef())` | Simple |
| Rename symbol | `QualifiedNameProvider` + transformer | Complex |
| Add import | `AddImportsVisitor.add_needed_import()` | Low |
| Remove unused import | `RemoveImportsVisitor` + scope analysis | Moderate |
| Find usages of name | `ScopeProvider` + `findall` | Moderate |
| List all class/function names | `m.findall()` + field access | Simple |
| Refactor: extract function | Parse + transformer + codegen | Complex |

### 10.2 Comparison with Existing LSP Tools

The 14 existing Punie tools fall into two categories:

| Category | Tools | Capability |
|----------|-------|-----------|
| **Read-only navigation** | `goto_definition`, `find_references`, `hover`, `document_symbols`, `workspace_symbols` | Find where things are |
| **Execution** | `typecheck`, `ruff_check`, `pytest_run`, `git_status`, `git_diff`, `git_log` | Run and report |

LibCST adds a third category:

| Category | Proposed Tools | Capability |
|----------|-------|-----------|
| **Transformation** | `cst_find_pattern`, `cst_rename`, `cst_add_import` | Change code |

LSP and LibCST are **complementary**: LSP finds the location of a symbol
(line/column), LibCST transforms it. A rename workflow would naturally chain both.

### 10.3 Proposed Punie Tools (3 high-value, low-risk)

**Tool 1: `cst_find_pattern`**
```python
result = cst_find_pattern("src/services/user.py",
                           pattern={"type": "Call", "func": "validate_email"})
# Returns: CSTFindResult(matches=[{line: 42, col: 8, source: "validate_email(email)"}, ...])
```

**Tool 2: `cst_rename`**
```python
result = cst_rename("src/services/user.py",
                     old_name="validate_email", new_name="check_email")
# Returns: CSTRenameResult(changed=True, replacements=3, new_source="...")
```

**Tool 3: `cst_add_import`**
```python
result = cst_add_import("src/services/user.py",
                         module="typing", name="Optional")
# Returns: CSTImportResult(added=True, new_source="...")
```

### 10.4 Implementation Path

Follow the established 7-file pattern:

| File | Change |
|------|--------|
| `src/punie/agent/typed_tools.py` | Add `CSTFindResult`, `CSTRenameResult`, `CSTImportResult` Pydantic models |
| `src/punie/agent/toolset.py` | Add 3 sync bridge functions (LibCST is sync — no async bridge needed) |
| `src/punie/agent/stubs.py` | Add 3 stubs with signatures + docstrings + examples |
| `src/punie/agent/config.py` | Add 3 guideline lines to `PUNIE_INSTRUCTIONS` |
| `src/punie/agent/monty_runner.py` | Add 3 `Callable` fields to `ExternalFunctions` |
| `tests/test_typed_tools.py` | Add parse function tests |
| `tests/test_sandbox_typed_tools.py` | Add sandbox execution tests |

**LibCST-specific implementation note:** Unlike LSP tools (which use
`asyncio.run_coroutine_threadsafe`), LibCST tools are fully synchronous — they just
call `cst.parse_module()` and run transformations. No async bridging needed. Example:

```python
def sync_cst_rename(file_path: str, old_name: str, new_name: str) -> CSTRenameResult:
    """Bridge from sync sandbox to LibCST rename operation."""
    import libcst as cst
    from punie.agent.typed_tools import CSTRenameResult, parse_cst_rename

    source = Path(file_path).read_text()
    try:
        module = cst.parse_module(source)
        # Apply rename transformer...
        new_source = new_module.code
        return CSTRenameResult(changed=True, new_source=new_source, ...)
    except Exception as e:
        return CSTRenameResult(changed=False, error=str(e), ...)
```

---

## 11. Assessment — Monty Feasibility (External Tool)

### 11.1 Feature Compatibility Matrix

Running LibCST itself *inside* Monty is not feasible. LibCST makes heavy use of features
Monty v0.0.6 does not support:

| LibCST Feature | Monty Status | Blocker Level |
|----------------|-------------|--------------|
| Class definitions | `NotImplementedError` | **Critical** — LibCST is class-heavy |
| `getattr()` builtin | Not implemented | **Critical** — visitor dispatch uses `getattr` |
| Decorators (beyond `@dataclass`) | Not implemented | **Critical** — `@add_slots`, `@dataclass` everywhere |
| `with` / context managers | `NotImplementedError` | High — used in metadata resolution |
| `yield` / generators | `NotImplementedError` | Moderate — used in some traversals |
| Standard library (`collections`, `abc`, etc.) | Not available | High — used throughout |
| `typing` module (beyond markers) | Partial | Moderate — `ClassVar`, `Sequence`, etc. |

### 11.2 External-Function Approach (Works Today)

The practical path requires zero Monty compatibility work:

```
[Monty sandbox]               [Python host]
result = cst_rename(          →  LibCST.parse_module()
    "src/foo.py",                LibCST transformer
    "old", "new"             ←   CSTRenameResult Pydantic model
)
if result.changed:
    print(result.new_source)
```

Monty code calls the external function and inspects a Pydantic model result. This is
identical to how `typecheck()`, `ruff_check()`, and `pytest_run()` already work.

---

## 12. Assessment — Mini-CST in Monty

This is the more interesting feasibility question.

### 12.1 The Key Insight

A CST parser treats Python source as *data*, not as *executable code*. A Monty-native
parser can handle `class Foo:`, `yield x`, `with open(...):`, `match x:`, and every
other construct Monty cannot *execute* — because parsing just builds a dict tree. The
parser needs to recognize syntax tokens, not run the semantics.

**Analogy:** A JSON parser doesn't need to understand what the JSON *means*. Similarly,
a Python CST parser doesn't need to *run* the Python — it just needs to recognize tokens
and build a tree.

### 12.2 Available Monty Primitives for a Mini-CST

| Primitive | Available? | Use for CST |
|-----------|-----------|-------------|
| Strings + methods (`split`, `strip`, `startswith`, `endswith`, `partition`) | ✅ Yes | Tokenizer |
| Recursion (configurable depth) | ✅ Yes | Recursive descent parser |
| Dicts | ✅ Yes | Node representation |
| Lists | ✅ Yes | Child sequences, token streams |
| Tuples | ✅ Yes | Immutable node alternatives |
| Functions + closures | ✅ Yes | Visitor dispatch, parser combinators |
| `frozen=True` dataclasses | ✅ Yes | Structured nodes (optional; dicts work too) |
| F-strings | ✅ Yes | Code generation |
| Try/except | ✅ Yes | Parser error handling |
| Comprehensions | ✅ Yes | Node filtering, tree queries |
| `isinstance()` | ✅ Yes | Node type checking |
| `enumerate`, `zip`, `map` | ✅ Yes | Traversal helpers |
| Class definitions | ❌ No | Use dicts instead |
| `getattr()` | ❌ No | Use `node["type"]` dict lookup instead |
| Standard library | ❌ No | Re-implement needed pieces |
| `re` module | ❌ No (PR open) | Use `str.find()` / `str.startswith()` |

### 12.3 Architecture of a Monty-Native Mini-CST

**Node representation (tagged dicts, not classes):**

```python
# Instead of LibCST's frozen dataclass:  Name(value="foo", lpar=[], rpar=[])
# Use tagged dicts:
{"type": "Name", "value": "foo"}
{"type": "FunctionDef", "name": "foo", "params": [...], "body": [...]}
{"type": "BinaryOp", "left": {...}, "op": "+", "right": {...}}
```

**Tokenizer (~200 lines):**

```python
def tokenize(source):
    """Returns list of {"type": T, "value": V, "line": L, "col": C} dicts."""
    tokens = []
    pos = 0
    line = 1
    col = 0
    while pos < len(source):
        # Match keywords, identifiers, numbers, strings, operators...
        if source[pos:pos+3] == "def":
            tokens.append({"type": "KEYWORD", "value": "def", "line": line, "col": col})
            pos += 3
        # ... etc.
    return tokens
```

**Recursive descent parser (~800 lines):**

```python
def parse_funcdef(tokens, pos):
    """Parse 'def name(params): body' — even though Monty can't call class-based methods"""
    assert tokens[pos]["value"] == "def"
    pos += 1
    name = tokens[pos]["value"]
    pos += 1
    params, pos = parse_params(tokens, pos)
    assert tokens[pos]["value"] == ":"
    pos += 1
    body, pos = parse_body(tokens, pos)
    return {"type": "FunctionDef", "name": name, "params": params, "body": body}, pos

def parse_classdef(tokens, pos):
    """Parse 'class Foo(Base): ...' — Monty can't run classes but CAN parse them"""
    assert tokens[pos]["value"] == "class"
    pos += 1
    name = tokens[pos]["value"]
    pos += 1
    bases, pos = parse_bases(tokens, pos) if tokens[pos]["value"] == "(" else ([], pos)
    assert tokens[pos]["value"] == ":"
    pos += 1
    body, pos = parse_body(tokens, pos)
    return {"type": "ClassDef", "name": name, "bases": bases, "body": body}, pos
```

**Visitor pattern (~50 lines, function dispatch via dict):**

```python
def visit(node, handlers):
    """Walk tree, calling handlers[node["type"]](node) for each matching node."""
    node_type = node["type"]
    handler = handlers.get(node_type) or handlers.get("_all")
    if handler:
        handler(node)
    for key, value in node.items():
        if isinstance(value, dict) and "type" in value:
            visit(value, handlers)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict) and "type" in item:
                    visit(item, handlers)
```

**Transformer pattern (~60 lines, bottom-up):**

```python
def transform(node, handlers):
    """Walk tree bottom-up, replacing nodes where handlers return a new node."""
    new_node = {}
    for key, value in node.items():
        if isinstance(value, dict) and "type" in value:
            new_node[key] = transform(value, handlers)
        elif isinstance(value, list):
            new_node[key] = [
                transform(item, handlers) if isinstance(item, dict) and "type" in item
                else item
                for item in value
            ]
        else:
            new_node[key] = value
    handler = handlers.get(new_node.get("type"))
    return handler(new_node) if handler else new_node
```

**Code generation (~300 lines, one function per node type):**

```python
def codegen(node):
    """Convert a CST dict back to source code."""
    t = node["type"]
    if t == "Name":     return node["value"]
    if t == "Integer":  return node["value"]
    if t == "BinaryOp": return f"{codegen(node['left'])} {node['op']} {codegen(node['right'])}"
    if t == "Assign":   return f"{codegen(node['target'])} = {codegen(node['value'])}"
    if t == "FunctionDef":
        params = ", ".join(codegen(p) for p in node["params"])
        body = "\n    ".join(codegen(s) for s in node["body"])
        return f"def {node['name']}({params}):\n    {body}"
    # ... one branch per node type
    raise ValueError(f"Unknown node type: {t}")
```

**Pattern matching (~100 lines, dict comparison):**

```python
def matches(node, pattern):
    """Check if node matches pattern dict. None values = wildcard."""
    if not isinstance(node, dict) or "type" not in node:
        return False
    for key, expected in pattern.items():
        if expected is None:
            continue
        if key not in node:
            return False
        if isinstance(expected, dict):
            if not matches(node[key], expected):
                return False
        elif node[key] != expected:
            return False
    return True

def findall(tree, pattern):
    """Find all nodes in tree matching pattern."""
    results = []
    def collect(node):
        if matches(node, pattern):
            results.append(node)
    visit(tree, {"_all": collect})
    return results
```

### 12.4 Can It Parse Python Features Monty Doesn't Support?

Yes — the parser represents all Python syntax as data:

```python
# Monty can't execute 'class Foo:', but it CAN tokenize it and build:
{"type": "ClassDef", "name": "Foo", "bases": [], "body": [...]}

# Monty can't execute 'yield x', but it CAN build:
{"type": "Yield", "value": {"type": "Name", "value": "x"}}

# Monty can't execute 'with open(f) as fh:', but it CAN build:
{"type": "With", "items": [{"type": "WithItem", ...}], "body": [...]}

# Monty can't execute 'match x: case 1: ...', but it CAN build:
{"type": "Match", "subject": {...}, "cases": [...]}
```

The tokenizer only needs `str.startswith()`, `str.find()`, and similar string ops —
all fully supported by Monty. The parser needs recursion (configurable depth, supported)
and dicts/lists (fully supported).

### 12.5 What Subset of LibCST Operations This Enables

| Operation | Feasible in Monty? | Notes |
|-----------|-------------------|-------|
| Parse Python source to dict tree | ✅ Yes | Recursive descent, ~800 lines |
| Find all functions/classes | ✅ Yes | `findall(tree, {"type": "FunctionDef"})` |
| Find all calls to X | ✅ Yes | `findall(tree, {"type": "Call", "func": {"type": "Name", "value": "X"}})` |
| Rename a symbol (all Name nodes) | ✅ Yes | Transform that replaces Name nodes |
| Add an import | ✅ Yes | Prepend to module body list |
| Remove a statement | ✅ Yes | Transform returns `None` sentinel |
| Generate source from tree | ✅ Yes | Codegen function per node type |
| Basic pattern matching | ✅ Yes | Dict comparison + findall |
| Count nodes by type | ✅ Yes | visit + counter |
| Scope analysis | ❌ No | Needs class hierarchy, LEGB rules, 1,254 lines |
| Qualified names | ❌ No | Depends on scope analysis |
| Type inference | ❌ No | Depends on external type checker |
| Whitespace-preserving round-trip | ⚠️ Partial | Possible but high effort (token-level tracking) |

### 12.6 Effort Estimate

| Component | Lines | Notes |
|-----------|-------|-------|
| Tokenizer | ~200 | Python tokenization with string ops |
| Recursive descent parser | ~800 | ~30 grammar rules for common constructs |
| Node types | 0 | Just dicts — no class definitions needed |
| Visitor/Transformer | ~110 | The `visit` and `transform` functions above |
| Code generator | ~300 | One branch per node type |
| Pattern matcher + findall | ~100 | Dict comparison |
| **Total** | **~1,510** | ~1.5% of LibCST's size |

This covers the most-used operations. For comparison, LibCST is ~101K Python + ~18K Rust lines.

### 12.7 The Three Approaches Compared

| Approach | Runs in sandbox? | Full LibCST power? | Effort | Recommendation |
|----------|-----------------|-------------------|--------|----------------|
| **External function** (Section 11) | No — calls out | 100% | Low | ✅ Do this first |
| **Monty-native mini-CST** | Yes | ~30% of features | Medium (~1,510 lines) | Later, if needed |
| **Hybrid** (external parse → dict → sandbox transform → external codegen) | Partially | ~60% | Low-medium | Good middle ground |

**Hybrid recommendation:** LibCST runs outside Monty and parses source to a JSON-serializable
dict tree. The dict is passed to Monty sandbox code, which does analysis/transformation
using `visit()` + `transform()` (both ~50 lines of Monty-compatible code). LibCST then
regenerates the source from the modified dict. This leverages LibCST's battle-tested parser
and codegen while giving the sandbox full control over the analysis logic.

---

## 13. Key Files Reference

### LibCST Key Files

| File | Lines | Purpose |
|------|-------|---------|
| `libcst/_nodes/base.py` | 499 | `CSTNode` abstract base class |
| `libcst/_nodes/expression.py` | 4,067 | All expression node types |
| `libcst/_nodes/statement.py` | 3,871 | All statement node types |
| `libcst/_nodes/module.py` | 165 | `Module` root node |
| `libcst/_nodes/op.py` | 1,031 | Operator node types |
| `libcst/_visitors.py` | ~150 | `CSTVisitor` + `CSTTransformer` |
| `libcst/_typed_visitor.py` | 7,669 | Auto-generated typed visitor stubs |
| `libcst/_parser/entrypoints.py` | 125 | `parse_module()`, `parse_statement()`, `parse_expression()` |
| `libcst/metadata/wrapper.py` | 222 | `MetadataWrapper` |
| `libcst/metadata/base_provider.py` | 171 | `BaseMetadataProvider` |
| `libcst/metadata/scope_provider.py` | 1,254 | `ScopeProvider` (most complex) |
| `libcst/matchers/__init__.py` | 16,680 | Public matcher API (auto-generated) |
| `libcst/matchers/_matcher_base.py` | 1,943 | Combinator implementations |
| `libcst/codemod/_command.py` | ~150 | `CodemodCommand` base class |
| `libcst/codemod/_visitor.py` | ~100 | `ContextAwareTransformer` |
| `native/libcst/Grammar` | ~32 KB | Python PEG grammar specification |
| `native/libcst/src/py.rs` | ~300 | PyO3 Python bindings |

### Punie Files to Modify for LibCST Tool Integration

| File | Change Required |
|------|----------------|
| `src/punie/agent/typed_tools.py` | Add Pydantic result models (`CSTFindResult`, `CSTRenameResult`, `CSTImportResult`) |
| `src/punie/agent/toolset.py` | Add sync bridge functions (no async needed — LibCST is sync) |
| `src/punie/agent/stubs.py` | Add stubs for system prompt injection |
| `src/punie/agent/config.py` | Add guideline lines to `PUNIE_INSTRUCTIONS` |
| `src/punie/agent/monty_runner.py` | Add `Callable` fields to `ExternalFunctions` dataclass |
| `tests/test_typed_tools.py` | Add parse function unit tests |
| `tests/test_sandbox_typed_tools.py` | Add sandbox execution tests |

**Prerequisite:** Add `libcst` to `pyproject.toml` dependencies:

```toml
dependencies = [
    "libcst>=1.8.0",
    ...
]
```

---

## 14. Domain Tools — LibCST as the Foundation

### 14.1 Three Levels of Tools

Punie's 14 existing tools fall into two categories:

| Category | Tools | Question answered |
|----------|-------|------------------|
| **Language-level** | `typecheck`, `ruff_check`, `pytest_run`, `git_*` | "Is this valid Python / does this pass quality gates?" |
| **Navigation** | `goto_definition`, `find_references`, `hover`, `document_symbols`, `workspace_symbols` | "Where is X / what is X?" |

LibCST introduces a third category that neither of these covers:

| Category | Proposed Tools | Question answered |
|----------|-------|------------------|
| **Transformation** | `cst_find_pattern`, `cst_rename`, `cst_add_import` | "Change code in a structured way" |

But there is a fourth category that matters most for the Flywheel:

| Category | Examples | Question answered |
|----------|----------|------------------|
| **Domain validation** | `cst_validate_tdom_component`, `cst_check_di_pattern`, `cst_validate_service` | "Is this a valid artifact in *our* architecture?" |

This distinction — from the `holy-grail-tools-domain.md` research — is crucial. Language-level tools verify that code is valid Python. Domain tools verify that code is valid *in your specific domain*. A type checker cannot know whether a tdom component must have `@view`, return `Element`, and use `html(t"...")`. Only a domain validator built on LibCST can check that.

### 14.2 LibCST Is the Plumbing, Domain Validators Are the Value

The `cst_*` tools from Section 10 are general-purpose. The real Flywheel value comes one level higher: domain validators that encode *your project's architectural rules* as LibCST visitors.

```python
# Language-level tool (already exists):
result = typecheck("src/views/user.py")  # Is this valid Python?

# Domain validation tool (new, built on LibCST):
result = cst_validate_tdom_component("src/views/user.py")
# Checks:
#   @view decorator present?
#   Return type is Element?
#   Uses html(t"...") not f-strings?
#   DI params are keyword-only?
#   Name ends in _view?
```

The domain validator runs LibCST externally (Option 1 from Section 11) and returns a `Pydantic` result model — same pattern as `TypeCheckResult`, `RuffResult`, etc.

### 14.3 The tdom-svcs Rules Are Encodable Today

For Punie's primary domain (tdom-svcs), the architectural rules are well-defined and each maps to a concrete LibCST check:

| Rule | LibCST check | ~Lines |
|------|-------------|--------|
| `@view` decorator required | `m.findall(tree, m.FunctionDef(decorators=m.AtLeastN(m.Decorator(decorator=m.Name("view")), n=1)))` | 5 |
| Returns `Element` | Visit `FunctionDef` → check `returns` annotation | 10 |
| Uses `html(t"...")` not f-strings | `m.findall(tree, m.FormattedString())` → flag if outside `html()` | 15 |
| DI params are keyword-only | Check `Parameters.kwonly_params` contains service types | 20 |
| Service names end in `Service` | `m.findall(tree, m.Param())` → check annotation names | 10 |
| `svcs.register()` in service init | Find `Call(func=m.Attribute(attr=m.Name("register")))` | 10 |

Total: a `cst_validate_tdom_component()` visitor is roughly 200 lines and encodes all the rules a senior developer knows implicitly.

The model that currently generates tdom components with ~60% `@view` compliance (estimated, not yet measured) would, after training on validated examples, improve to 90%+. This is not a language-correctness improvement — it is a *domain-correctness* improvement that `typecheck` and `ruff` are blind to.

### 14.4 What Makes This Different From More Linters

Running `ruff` catches PEP 8 violations. It cannot catch:
- "This component is missing its dependency injection setup"
- "This service isn't registered with svcs"
- "This view uses f-strings where t-strings are required by the template engine"

These are *architectural* violations. The model ships code that passes all language checks but is wrong. Domain validators make the invisible visible — and once visible, capturable as training signal.

### 14.5 Feasibility and Dependency Chain

| Step | Effort | Prerequisite |
|------|--------|-------------|
| LibCST external tool integration (Section 10) | Low — follows 7-file pattern | Add `libcst` to deps |
| `cst_validate_tdom_component` visitor | Medium — ~200 lines of CST visitor | LibCST integration |
| `cst_validate_service` visitor | Medium — ~150 lines | LibCST integration |
| TrainingCollector captures validated generations | Low — already designed in flywheel doc | Domain validators exist |
| Retrain on validated examples | Standard pipeline | ~50-100 examples |

The domain validators need to be *correct and complete* before they contribute to training. LibCST is deterministic — a visitor that checks `@view` will not produce false positives. The risk is incompleteness, not incorrectness. Build one validator, run it on 20-30 real generations, measure actual failure rates, then use that data to drive training data generation.

---

## 15. Flywheel Data Capture Design

### 15.1 You Don't Need Every Step

The flywheel research (`docs/research/flywheel-capture.md`) describes spec-driven feature branches as the ideal unit of capture: spec → branch → implement → iterate → validate → commit → merge. In practice, a feature branch might be a 20-turn conversation.

Capturing all 20 turns and training on them directly is counterproductive:
- Creates long context windows (expensive, poor convergence)
- Dilutes high-signal moments with low-signal narrative
- Makes it hard to weight examples by quality

The value in a long interaction is distributed very unevenly:

| Turn type | Signal | Frequency |
|-----------|--------|-----------|
| Error → correction (retry loop after domain validator) | **Highest** — automatic contrastive pair | ~10-15% of turns |
| Multi-tool decision (`if result.X → call Y`) | **High** — cross-tool workflow pattern | ~5-10% of turns |
| User correction ("no, I meant...") | **High** — explicit negative signal | ~5% of turns |
| Successful single-tool call with field access | Medium — positive example | ~30% of turns |
| Model generating text without tools | Low | ~30% of turns |
| "Looks good, continue" back-and-forth | Near zero | ~20% of turns |

A 20-turn branch interaction produces **5-8 training examples worth keeping**, not 20. The extractor (Section 15.3) identifies those moments.

### 15.2 Event-Sourced Capture

Rather than logging full conversation state, capture *events* — moments when something interesting happened. Cheap to emit, sparse, high signal density:

```python
@dataclass
class PunieEvent:
    """A single capturable moment in an interaction."""
    timestamp: str
    session_id: str
    branch: str | None
    spec_ref: str | None          # path to spec file — context, not curriculum

    event_type: Literal[
        "tool_call",              # model called a tool
        "domain_validation",      # cst_validate_* ran
        "user_correction",        # user said "no, I meant..."
        "user_confirmation",      # user said "perfect" / continued workflow
        "commit",                 # checkpoint: code was committed
        "branch_merged",          # ground truth: it shipped
        "branch_closed",          # ground truth: it didn't ship
        "retry",                  # model corrected after validation failure
    ]

    # Tool call fields
    query: str | None             # user query that triggered this
    tool_name: str | None
    tool_args: dict | None
    tool_result_summary: dict | None  # shape + success, NOT full result
    fields_accessed: list[str]    # which result fields appeared in generated code

    # Domain validation fields
    validator_name: str | None
    validation_passed: bool | None
    validation_errors: list[str] | None

    # Retry / correction fields
    original_code: str | None     # what model generated before correction
    corrected_code: str | None    # what model generated after seeing error
    signal_text: str | None       # for user_correction: what the user said

    # Applied retroactively at branch_merged / branch_closed
    quality_weight: float | None
```

Events are emitted at instrumentation points in the tool execution layer and WebSocket handler — not by the model, not by the user. The model never knows it's being observed.

### 15.3 The Extractor: Events → Training Examples

Raw events become training examples via a post-hoc extractor. This runs offline, not in real-time:

```python
def extract_training_examples(
    events: list[PunieEvent],
) -> list[TrainingExample]:
    """Convert an event stream into dense training examples."""
    examples = []

    for event in events:
        if event.event_type == "retry":
            # Highest value: automatic error→fix contrastive pair
            # Model generated X → validator said "missing @view" → model corrected to Y
            examples.append(TrainingExample(
                context=load_spec_summary(event.spec_ref),
                conversation_window=get_window(event.session_id, event.timestamp, n=3),
                query=event.query,
                negative_response=event.original_code,
                error_signal=event.validation_errors,
                positive_response=event.corrected_code,
                example_type="corrective",
                base_weight=1.5,
            ))

        elif event.event_type == "domain_validation" and event.validation_passed:
            # Positive: model generated valid domain artifact on first try
            examples.append(TrainingExample(
                ...,
                example_type="positive",
                base_weight=1.0,
            ))

        elif event.event_type == "user_correction":
            # Strong negative — model misunderstood intent
            examples.append(TrainingExample(
                ...,
                example_type="negative",
                base_weight=2.0,
            ))

        elif event.event_type == "tool_call" and is_multi_tool_sequence(event, events):
            # Cross-tool workflow — the most valuable pattern currently missing
            examples.append(TrainingExample(
                ...,
                example_type="multi_tool",
                base_weight=1.3,
            ))

    # Apply branch outcome weighting retroactively
    # branch_merged → multiply all from that session by 1.2
    # branch_closed without merge → multiply by 0.5
    return apply_outcome_weights(examples, events)
```

### 15.4 The Spec: Context, Not Curriculum

The spec is not replayed as a sequence of steps. It is attached as **context** to each extracted training example — a few lines explaining *why* the user was asking:

```
# Training example header:
system: You are Punie. Context: User is implementing tdom view layer
        per spec at agent-os/specs/2026-02-17-user-profile/.

user: Create the UserProfileView

assistant: [correct tdom component code with @view, Element return, html(t"...")]
```

This lets the model learn domain patterns without needing to see the full 20-turn conversation. The spec gives domain grounding; the conversation window (last 3-5 turns) gives task context; the extracted example gives the learning signal.

### 15.5 Branch Outcome Is the Ground Truth Link

The one thing that genuinely requires end-to-end tracking is branch outcome. Whether the code merged is the ground truth label that weights *all* examples from that session.

Without branch outcomes, you cannot distinguish:
- "Model generated good code, user approved" — positive signal
- "Model generated mediocre code, user accepted it anyway" — ambiguous
- "Model generated bad code, user gave up and merged to unblock themselves" — negative signal that looks positive

The event stream links to git via `branch` field. A post-merge hook or CI step emits `branch_merged` / `branch_closed` events. The extractor then retroactively weights all examples from that session.

### 15.6 Expected Training Example Yield

| Branch type | Turns | High-signal events | Training examples |
|------------|-------|-------------------|------------------|
| Simple feature (1 session) | 8-10 | 2-3 retries, 1 confirmation | 3-5 |
| Complex feature (3 sessions) | 20-25 | 4-6 retries, 2-3 user corrections | 7-10 |
| Failed branch (closed) | 5-10 | 2-3 retries, 1 abandonment | 2-3 (weighted 0.5×) |

At one branch per week, this yields roughly **30-50 high-quality training examples per month** — small volume but high signal density. The flywheel doc's projection of "+100 real examples/week" assumes more active usage; at any usage level, quality-per-example is substantially higher than synthetic data.

### 15.7 Instrumentation Points

Where to emit events in the Punie codebase:

| Event type | Where to emit | File |
|-----------|--------------|------|
| `tool_call` | After each tool execution returns | `src/punie/agent/toolset.py` |
| `domain_validation` | Inside `cst_validate_*` result parsers | `src/punie/agent/typed_tools.py` |
| `retry` | When ModelRetry catches a domain validation failure | `src/punie/agent/factory.py` |
| `user_correction` | WebSocket message classifier (detect "no, I meant...") | `src/punie/http/websocket.py` |
| `user_confirmation` | WebSocket message classifier (detect "perfect", continued workflow) | `src/punie/http/websocket.py` |
| `commit` | Git post-commit hook or `git_status` tool detecting new commits | Git hook |
| `branch_merged` / `branch_closed` | Git post-merge / PR webhook | Git hook or CI |

The event store is a JSONL append file per session, rotated daily. The extractor runs weekly, producing a batch of training examples for the next fine-tuning cycle.

---

## References

- LibCST local source: `~/PycharmProjects/LibCST`
- LibCST GitHub: https://github.com/Instagram/LibCST
- Monty feature report: `docs/research/monty-language-features.md`
- Existing tool patterns: `src/punie/agent/typed_tools.py`, `src/punie/agent/toolset.py`
- Phase 27 implementation guide: `docs/phase27-complete-implementation.md`
- Flywheel capture design: `docs/research/flywheel-capture.md`
- Domain tools research: `docs/research/holy-grail-tools-domain.md`
