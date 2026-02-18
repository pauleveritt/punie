# Flywheel Runner

This research looked at aspects of how to re-imagine a test runner using modern Python machinery in 3.14+. It then
expanded this to profiling and testing, driven by svcs and subinterpreters, with dependency tracking. Closing with using
it as a way to collect signal for Flywheel.

## A Conversation About Rethinking Python Testing

---

## Table of Contents

1. [Are there lean pytest alternatives embracing modern Python?](#1-modern-python-test-runners)
2. [How might svcs impact the sketch?](#2-svcs-and-inversion-of-control)
3. [How does registry/container map into subinterpreters?](#3-registries-and-subinterpreters)
4. [Would object sharing help or hurt?](#4-object-sharing)
5. [Dependency tracking and always-on run/test/debug/profile mode](#5-dependency-tracking-and-always-on-modes)
6. [SQLite as the nervous system](#6-sqlite-as-the-nervous-system)
7. [Skeptical and ambitious analysis](#7-analysis)

---

## 1. Modern Python Test Runners

**Q: Are there any new, lean Python test runners as alternatives to pytest that embrace modern Python 3.13+ features for
re-thinking the testing experience? Execution in subinterpreters, low-impact monitoring, typing improvements, better
error messages, template strings.**

### What Actually Exists Now

Honest answer first: **no dominant lean alternative has emerged yet** that fully embraces the post-3.12/3.13 feature
set.

**`ward`** - Most serious pytest alternative:

```python
from ward import test, fixture


@fixture
def user():
    return {"name": "Alice", "role": "admin"}


@test("admin users can access dashboard")
def _(user=user):
    assert user["role"] == "admin"
```

**`unittest`** still ships with stdlib and gets quiet improvements each release. Others (`virtue`, `slash`) exist but
have low momentum.

### The Modern Python Features Worth Building On

**1. Subinterpreters (PEP 734, Python 3.13)**

```python
import _interpreters  # 3.13 stdlib (low-level)

# Concept: each test module in its own subinterpreter
# - Real isolation (no shared GIL in free-threaded builds)
# - Faster than spawning processes
# - Still experimental API surface
# Nobody has built a test runner on this yet seriously
```

**2. PEP 669 - Low Impact Monitoring (3.12+)**

```python
import sys

# sys.monitoring is MUCH cheaper than settrace()
# Old approach (pytest uses this, it's expensive):
sys.settrace(my_trace_fn)  # Fires on EVERY event

# New approach:
sys.monitoring.set_tool(sys.monitoring.COVERAGE_ID, "my_runner")
sys.monitoring.set_events(
    sys.monitoring.COVERAGE_ID,
    sys.monitoring.events.LINE
)
sys.monitoring.register_callback(
    sys.monitoring.COVERAGE_ID,
    sys.monitoring.events.LINE,
    lambda code, line: ...
)
# Result: coverage collection with ~1/10th the overhead
# No test runner has fully pivoted to this yet
```

**3. Template Strings (PEP 750, 3.14) - Testing Goldmine**

```python
# PEP 750 t-strings are not f-strings - they're lazy/inspectable

def assert_that(template: Template):
    for part in template.args:
        print(f"Expression: {part!r}")
        print(f"Value:      {part.value!r}")


x, y = 42, 43
assert_that(t"expected {x} to equal {y}")
# Could print:
# Expression: 'x'  (the source code!)
# Value:      42
# Expression: 'y'  
# Value:      43

# This is better than pytest's AST rewriting hack
# pytest rewrites bytecode to get variable names
# t-strings give you this for FREE at the language level
```

**4. Better Typing (3.12+)**

```python
# PEP 695 type aliases - cleaner fixture typing
type TestResult[T] = tuple[T, list[str]]
type Fixture[T] = Callable[[], T]


class fixture[T]:
    def __init__(self, fn: Callable[[], T]) -> None: ...

    def __call__(self) -> T: ...
```

**5. Exception Groups (3.11+) - Underused in Testing**

```python
def assert_all(*assertions):
    errors = []
    for fn, msg in assertions:
        try:
            fn()
        except AssertionError as e:
            errors.append(e)
    if errors:
        raise ExceptionGroup("assertion failures", errors)

# Shows ALL failures, not just the first
# pytest soft assertions are a plugin hack around this
```

### What a Modern Runner Would Actually Look Like

```python
# hypothetical: lean_test/__init__.py
import sys
import _interpreters
from string.templatelib import Template

_tests: list[Test] = []


def test(template: Template):
    def decorator(fn):
        _tests.append(Test(template, fn))
        return fn

    return decorator


def expect(template: Template) -> None:
    expr_part = template.args[0]
    if not expr_part.value:
        raise AssertionError(
            f"Expected truthy, got {expr_part.value!r}\n"
            f"Expression: {template!s}"
        )


@test(t"addition works for positive numbers")
def _():
    x, y, expected = 1, 2, 4
    expect(t"{x} + {y} == {expected}")
    # Fails with:
    # Expected truthy, got False
    # Expression: 1 + 2 == 4
```

### Feature Status

| Feature                       | Status                                                   |
|-------------------------------|----------------------------------------------------------|
| `sys.monitoring` for coverage | Available 3.12, **nobody's built a runner on it**        |
| Subinterpreter isolation      | API stable in 3.13, **no runner uses it**                |
| t-string assertions           | 3.14 (alpha), genuinely **game-changing for assertions** |
| ExceptionGroup soft-asserts   | 3.11, **ward/pytest have partial support**               |
| PEP 695 typed fixtures        | Available now, **mostly ignored**                        |

The Python testing ecosystem is in an interesting moment. pytest is powerful but carries **15 years of design decisions
** made before free-threaded Python, subinterpreters, `sys.monitoring`, t-strings, and exception groups. The tooling for
a genuinely modern runner exists in the stdlib — it just hasn't been assembled yet.

---

## 2. svcs and Inversion of Control

**Q: Imagine the use of the svcs package for registries and inversion of control containers. How might that impact the
sketch?**

### What svcs Gives You

```python
import svcs

# svcs core concepts that matter for testing:
# - Registry: defines HOW to create services (test suite level)
# - Container: resolves services for a specific scope (test level)
# - Containers are cheap to create and throw away
# - Async and sync factories, health checks built in
```

The key insight: **svcs containers are already the thing pytest fixtures are trying to be**, but with explicit scoping,
type-safety, and no magic.

### Rethinking Fixtures as svcs Registries

**Current pytest mental model (implicit, decorator-magic):**

```python
@pytest.fixture(scope="session")
def db():
    conn = create_connection()
    yield conn
    conn.close()


@pytest.fixture(scope="function")
def user(db):  # implicit dependency on db
    return db.insert({"name": "Alice"})
```

**svcs mental model (explicit, typed, composable):**

```python
def build_suite_registry() -> svcs.Registry:
    reg = svcs.Registry()

    async def make_db() -> AsyncDatabase:
        db = await AsyncDatabase.connect("postgresql://test")
        yield db
        await db.disconnect()

    reg.register_factory(AsyncDatabase, make_db)
    return reg


async with svcs.Container(suite_registry) as container:
    db = await container.aget(AsyncDatabase)
```

### Scoped Registries

```python
class TestRegistries:
    """
    Three explicit scopes backed by svcs registries.
    No magic scope inference - you choose explicitly.
    """

    def __init__(self):
        self.session = svcs.Registry()  # process lifetime
        self.module = svcs.Registry()  # per test file
        self.test = svcs.Registry()  # per test function
```

### Test Registration

```python
@dataclass
class Test:
    name: Template  # t-string: inspectable, not just a str
    fn: TestFn
    needs: list[type]  # explicit service types, not name-matched strings
    module: str


def test(name: Template, *, needs: list[type] = []):
    """
    @test(t"admin {role} can access {resource}", needs=[Database, CurrentUser])
    async def _(db: Database, user: CurrentUser):
        ...

    - Name is a t-string: values inspectable for parametrize
    - Dependencies are explicit TYPES not magic names
    """
```

### Container Lifecycle

```python
class Runner:
    def __init__(self, registries: TestRegistries):
        self.reg = registries
        self._session_container = svcs.Container(registries.session)

    async def run_module(self, module: str, tests: list[Test]):
        async with svcs.Container(self.reg.module) as module_container:
            for t in tests:
                await self.run_test(t, module_container)

    async def run_test(self, t: Test, module_container: svcs.Container):
        async with svcs.Container(self.reg.test) as test_container:
            layered = LayeredContainer(
                test_container,
                module_container,
                self._session_container,
            )
            services = await layered.aget_all(*t.needs)
            await t.fn(*services)
```

### Layered Container Resolution

```python
class LayeredContainer:
    """
    Explicit scope chain. Test → Module → Session.
    No hidden scope promotion, no pytest fixture confusion.
    """

    def __init__(self, *containers: svcs.Container):
        self._layers = containers  # ordered: narrowest first

    async def aget[T](self, svc_type: type[T]) -> T:
        for container in self._layers:
            with contextlib.suppress(svcs.exceptions.ServiceNotFoundError):
                return await container.aget(svc_type)
        raise svcs.exceptions.ServiceNotFoundError(svc_type)
```

### Assertions Using t-strings + Exception Groups

```python
def expect(template: Template) -> None:
    for part in template.args:
        if isinstance(part, Interpolation):
            if not part.value:
                raise AssertionError(
                    f"\n  Expression : {part!s}\n"
                    f"  Value      : {part.value!r}\n"
                    f"  Context    : {template!s}"
                )


@contextlib.contextmanager
def expect_all():
    """Collect ALL assertion failures. Uses ExceptionGroup - no plugin needed."""
    failures: list[AssertionError] = []

    class Collector:
        def __call__(self, template: Template) -> None:
            try:
                expect(template)
            except AssertionError as e:
                failures.append(e)

    yield Collector()

    if failures:
        raise ExceptionGroup(f"{len(failures)} assertion(s) failed", failures)


@test(t"user profile is complete", needs=[Database])
async def _(db: Database):
    user = await db.find_user(id=1)
    async with expect_all() as check:
        check(t"{user.name} is not empty")
        check(t"{user.email} contains '@'")
        check(t"{user.role} in {'admin', 'editor'}")
```

### What This Architecture Buys You

```
pytest approach                 svcs-backed approach
─────────────────────────────────────────────────────
Fixture scope: magic strings    Scope: which registry you register with
Fixture deps: name matching     Deps: explicit type list in @test(needs=[...])
Fixture sharing: implicit       Sharing: container hierarchy, explicit
Cleanup: yield + finalizers     Cleanup: svcs handles via async context
Parallel isolation: hard        Parallel: new Container per subinterpreter
Health checks: plugin           Health checks: svcs built-in
Type safety: partial            Type safety: full, generics via PEP 695
```

The core shift: **svcs separates service definition (registry) from service resolution (container)**, which maps cleanly
onto the test collection/execution split. pytest fixtures collapse these two things together, which is why fixture
scoping is confusing.

---

## 3. Registries and Subinterpreters

**Q: How does registry/container map into subinterpreters?**

### The Core Problem

```python
# This cannot work across subinterpreter boundaries:
registry = svcs.Registry()  # lives in main interpreter

# In subinterpreter - this object does not exist here
# Memory is not shared. Period.
db = await container.aget(Database)  # ← what container? which registry?
```

### What Can Actually Cross the Boundary

```python
# What CAN be shared (Python 3.13+):
# - Primitive data: str, int, bytes, bool, None
# - Channels: _interpreters.create_channel()
# - Queues via interpreters.Queue (3.13 stdlib)
# - Code objects (send source or bytecode)

# What CANNOT cross:
# - Arbitrary Python objects (Registry, Container, connection pools)
# - Locks, Events, most synchronization primitives
# - Anything with __dict__ that isn't explicitly designed for it
```

### Registry as Serializable Configuration

```
MAIN INTERPRETER                    SUBINTERPRETER
────────────────                    ──────────────
Registry (blueprint)    ──────►     Registry (reconstructed)
  "how to make things"   serialize    "same recipe, new instance"
  
Container (runtime)     ✗ never ►   Container (fresh, local)
  "live object graph"                "built from local registry"
```

```python
@dataclass
class ServiceSpec:
    """Serializable description of how to build one service."""
    svc_type_ref: FactoryRef  # (module, qualname) - serializable
    factory_ref: FactoryRef
    scope: str  # "session" | "module" | "test"
    ping_ref: FactoryRef | None


@dataclass
class RegistrySpec:
    """
    The full blueprint for a test run.
    Can be pickled, sent over a channel, reconstructed anywhere.
    """
    services: list[ServiceSpec] = field(default_factory=list)

    def to_bytes(self) -> bytes:
        import pickle
        return pickle.dumps(self)

    def build_svcs_registry(self) -> svcs.Registry:
        """Reconstruct a live svcs.Registry from this spec."""
        reg = svcs.Registry()
        for spec in self.services:
            svc_type = _from_ref(spec.svc_type_ref)
            factory = _from_ref(spec.factory_ref)
            reg.register_factory(svc_type, factory)
        return reg
```

### Runner Architecture with Subinterpreters

```python
class SubinterpreterRunner:

    async def run(self, tests: list[Test]) -> list[TestOutcome]:
        spec_bytes = self.spec.to_bytes()  # Serialize the registry ONCE
        result_queue = interpreters.Queue()
        partitions = self._partition_by_module(tests, self.worker_count)

        for i, partition in enumerate(partitions):
            interp = _interpreters.create()
            await self._run_worker(interp, i, spec_bytes, partition, result_queue)

    def _partition_by_module(self, tests, n):
        """
        Keep tests from the same module together.
        Module-scoped svcs services are rebuilt per-interpreter,
        but we minimize rebuilds by co-locating module tests.
        """
```

### The Worker Script (Runs Inside Subinterpreter)

```python
WORKER_SCRIPT = """
async def main():
    request: RunRequest = await request_queue.get_async()
    
    # Reconstruct svcs registry LOCALLY in this interpreter
    # Same recipe, fresh ingredients
    spec = RegistrySpec.from_bytes(request.registry_spec)
    registry = spec.build_svcs_registry()
    
    # Health check before running any tests
    async with svcs.Container(registry) as probe:
        health = await probe.aget_health_report()
    
    session_container = svcs.Container(
        spec.build_scoped_registry("session")
    )
    try:
        for test_ref in request.test_refs:
            outcome = await run_one(test_ref, spec, session_container)
            await result_queue.put_async(outcome)
    finally:
        await session_container.aclose()
"""
```

### What "Session" Scope Now Means

```
PYTEST MODEL                        SUBINTERPRETER MODEL
────────────────────────────────────────────────────────
session scope = one object,         session scope = N identical objects,
shared by all tests                 one per interpreter

@pytest.fixture(scope="session")    @session_service(Database)
def db(): ...                       async def make_db() -> Database:
                                        # called once PER INTERPRETER
# One DB connection for             # 4 workers = 4 connections
# entire suite                      # but fully isolated
```

### The Complete Scope Picture

```
MAIN INTERPRETER
├── true_session scope
│   ├── Run migrations
│   ├── Start docker containers  
│   ├── Capture connection strings → bytes
│   └── Send bytes to workers via Queue
│
SUBINTERPRETER 1                SUBINTERPRETER 2
├── Receive spec_bytes           ├── Receive spec_bytes
├── Reconstruct Registry         ├── Reconstruct Registry (identical recipe)
├── worker_session scope         ├── worker_session scope
│   └── svcs.Container          │   └── svcs.Container (separate instance)
├── module scope                 ├── module scope
│   └── svcs.Container           │   └── svcs.Container
├── test scope (per test)        ├── test scope (per test)  
│   └── svcs.Container           │   └── svcs.Container
```

The deepest consequence: **svcs's value proposition shifts from managing shared object lifetimes to managing
isolated-but-consistently-constructed object lifetimes**. The registry stops being a shared singleton and becomes a
replication recipe.

---

## 4. Object Sharing

**Q: Would having some kind of object sharing help or hurt?**

### The Spectrum

```
NOTHING SHARED          SOME SHARED              FULLY SHARED
──────────────────────────────────────────────────────────────
Current sketch          What we're exploring     Free-threaded Python
serialize everything                             (not subinterpreters)

Most isolation          Pragmatic middle         Least isolation
Most serialization      ground                   Most risk
overhead
```

### Case 1: Sharing the Registry Itself — NO

```python
# What a Registry actually contains:
@dataclass
class svcs.Registry:
    _factories: dict[type, Factory]  # type objects + callables
    _ping_factories: dict[type, ...]  # more callables
    _on_registry_close: list[...]  # callbacks

# Callable objects: NOT safe - have __closure__ with live refs
# The dict itself: NOT safe - mutable, refcounted
# Verdict: RegistrySpec blueprint approach costs almost nothing.
```

### Case 2: Sharing Read-Only Fixture Data — YES

```python
class SharedFixtureData:
    """
    Immutable test data in shared memory.
    Workers map it read-only - zero copy, zero parse overhead.
    """

    def __init__(self, data: bytes):
        self._shm = SharedMemory(create=True, size=len(data))
        self._shm.buf[:] = data

    @property
    def ref(self) -> tuple[str, int]:
        return (self._name, self._size)  # serializable

# 50MB of test fixtures × 4 workers:
# Without sharing: 200MB + 4× parse time
# With SharedMemory: 50MB + small per-worker parse overhead
```

### Case 3: Sharing Live Service Objects — NO

```python
class DatabaseConnection:
    def __init__(self):
        self._socket = socket(...)  # file descriptor
        self._lock = threading.Lock()  # NOT shareable
        self._buffer = bytearray(...)  # NOT safely shareable
        self._protocol_state = {}  # mutable, NOT safe

# Worker 1: await conn.execute("SELECT ...")  ← modifies protocol state
# Worker 2: await conn.execute("INSERT ...")  ← race condition
# No GIL to protect you.
# Use a connection pool on the DB server side instead.
```

### Case 4: Sharing Compiled Bytecode — MAYBE

```python
class CodeCache:
    """Pre-compile test modules. Send bytecode to workers. Skip parse+compile."""

    def precompile(self, module_path: str) -> tuple[str, int]:
        source = Path(module_path).read_text()
        code = compile(source, module_path, "exec")
        bytecode = marshal.dumps(code)
        shm = SharedMemory(create=True, size=len(bytecode))
        shm.buf[:] = bytecode
        return (shm.name, len(bytecode))
    # Each worker still gets its own module namespace (correct isolation)
    # But compilation work done once
```

### Case 5: Channel-Based Service Broker — MAYBE (for singular resources)

```python
class ServiceBroker:
    """
    Runs in main interpreter.
    Workers request primitive-serializable service data via channel.
    NOT live objects - transformed representations.
    Only worth it for genuinely singular, expensive, or 
    externally-constrained services (rate-limited APIs, ML models).
    """
```

### The Honest Map

```
Sharing candidate          Worth it?   Why
──────────────────────────────────────────────────────────────────
svcs.Registry object        NO         Reconstruct from spec, near-zero cost
svcs.Container object       NO         Must be local, that's the whole point
Large immutable test data   YES        SharedMemory, real memory + time savings  
DB connections              NO         Use server-side pool, isolation matters
Compiled bytecode           MAYBE      Real win for large suites, adds complexity
Auth tokens / config        MAYBE      Channel-based broker for singular resources
ML models / large caches    YES        SharedMemory read-only mapping
```

For svcs specifically: **the registry is the right thing to replicate, the container is the right thing to keep local**.

---

## 5. Dependency Tracking and Always-On Modes

**Q: Vitest has server-mode with a watcher, dependency tracking to know which tests need to run based on which code
changes, and in non-watcher mode runs only tests needed for git unstaged changes. Do we have enough information to track
dependencies? Then: with sys.monitoring, could we imagine a system where you're always in run/test/debug/profile mode?**

### What Information Do We Have?

```python
# We already collect, or could collect:
# 1. From collection phase:
test.module  # which file the test lives in
test.needs  # which service TYPES it depends on (svcs)

# 2. From RegistrySpec:
spec.services  # ServiceSpec with factory_ref: (module, qualname)

# 3. From sys.monitoring (already planned):
# We can record exactly which lines/functions each test touches
# This is the missing piece - runtime import graph
```

The static information is partial. The dynamic information from `sys.monitoring` is complete. The key insight: **run
every test once to build the dependency graph, then use it forever**.

### Building the Import Graph

```python
class DependencyTracker:

    def install(self):
        sys.monitoring.set_tool(self._tool_id, "lean_test_deps")
        sys.monitoring.set_events(
            self._tool_id,
            sys.monitoring.events.PY_START  # function entry only
        )
        sys.monitoring.register_callback(
            self._tool_id,
            sys.monitoring.events.PY_START,
            self._on_function_entry,
        )

    def _on_function_entry(self, code, instruction_offset: int):
        if self._current_test is None:
            return
        path = Path(code.co_filename).resolve()
        if self._is_project_file(path):
            self._touched.add(path)
        return sys.monitoring.DISABLE  # per-code-object disable
        # This is the sys.monitoring superpower:
        # disable per code object after first hit
        # subsequent calls to same function: zero overhead
```

### Persisting the Graph

```python
class DependencyStore:
    """SQLite for the dependency graph. Fast enough, queryable, survives restarts."""

    def tests_affected_by(self, changed_files: set[Path]) -> set[tuple[str, str]]:
        placeholders = ",".join("?" * len(changed_files))
        rows = self._conn.execute(f"""
            SELECT DISTINCT test_module, test_qualname
            FROM test_files
            WHERE source_file IN ({placeholders})
        """, [str(f) for f in changed_files]).fetchall()
        return {(row[0], row[1]) for row in rows}
```

### Watcher Integration

```python
class TestServer:
    async def _handle_changes(self, changes):
        changed_paths = {Path(path).resolve() for _, path in changes}

        # Query the graph
        affected = self.deps.tests_affected_by(changed_paths)

        # Invalidate stale dependency records
        for path in changed_paths:
            self.deps.invalidate_file(path)

        print(f"  {len(changed_paths)} file(s) changed → "
              f"{len(affected)} test(s) affected")

        await self._run_with_tracking(tests_to_run)
```

### Git Unstaged Mode

```python
async def run_for_git_changes(runner, dep_store, mode="unstaged"):
    match mode:
        case "unstaged":
            changed = get_unstaged_files(root)
        case "uncommitted":
            changed = get_unstaged_files(root) | get_uncommitted_files(root)
        case str(s) if s.startswith("since="):
            ref = s.removeprefix("since=")
            changed = get_changed_since(root, ref)

    if not dep_store.is_graph_complete():
        print("Dependency graph incomplete - running full suite to build it")
        await runner.run_all_with_tracking()

    affected = dep_store.tests_affected_by(changed)
    await runner.run(affected)
```

### Always-On Modes

```python
class Observe(Flag):
    """What we're paying attention to right now."""
    NOTHING = 0
    DEPS = auto()  # which files are touched (near-zero cost)
    COVERAGE = auto()  # which lines are touched
    PROFILE = auto()  # timing per function  
    TRACE = auto()  # full execution trace (for debugging)
    EXCEPTIONS = auto()  # exception sites (always cheap)

    NORMAL = DEPS | EXCEPTIONS
    FULL = DEPS | COVERAGE | PROFILE | EXCEPTIONS


@dataclass
class FailurePolicy:
    capture_locals: bool = True
    capture_trace: bool = False
    open_debugger: bool = False
    profile_failure: bool = False
    replay: bool = False
```

### Automated Debugging During Tests

```python
class TestDebugger:
    """Not pdb. Observation machinery that activates on failure."""

    def arm(self):
        sys.monitoring.set_events(
            self._tool_id,
            sys.monitoring.events.PY_START |
            sys.monitoring.events.RAISE |
            sys.monitoring.events.EXCEPTION_HANDLED
        )

    def _on_enter(self, code, offset):
        self._call_stack.append(FrameInfo(code=code, offset=offset))
        return sys.monitoring.DISABLE  # first-time-only, cheap

    def _on_raise(self, code, offset, exception):
        frame = sys._getframe(1)
        self._exception_sites.append(ExceptionSite(
            code=code,
            exception=exception,
            locals=self._safe_capture_locals(frame),
        ))
        # Escalate: turn on full tracing for stack unwind
        sys.monitoring.set_events(
            self._tool_id,
            sys.monitoring.events.PY_START |
            sys.monitoring.events.PY_RETURN |
            sys.monitoring.events.LINE |
            sys.monitoring.events.RAISE
        )
```

### The Failure → Insight Pipeline

```python
async def run_one_test(t, container, ctx):
    debugger = TestDebugger(tool_id=LEAN_TEST_DEBUG_SLOT)
    debugger.arm()

    try:
        services = await container.aget_all(*t.needs)
        await t.fn(*services)
        return TestOutcome(test=t, passed=True)

    except AssertionError as e:
        debug_report = debugger.disarm()
        outcome = TestOutcome(test=t, passed=False, exception=e)

        match ctx.on_failure:
            case FailurePolicy(replay=True):
                profile_report = await replay_with_profile(t, container)
                outcome.profile = profile_report
            case FailurePolicy(open_debugger=True):
                await interactive_debug_session(t, debug_report, container)
            case FailurePolicy(capture_trace=True):
                outcome.trace = debug_report

        return outcome
```

### What "Always On" Actually Looks Like

```python
# Watch mode:       Observe.DEPS | Observe.EXCEPTIONS
# CI mode:          Observe.DEPS | Observe.COVERAGE | Observe.EXCEPTIONS  
# Interactive:      Observe.NORMAL (fast, minimal)
# Debug specific:   Observe.FULL + open_debugger=True
# Profile specific: Observe.DEPS | Observe.PROFILE

# Same test runner, same svcs containers, same subinterpreters
# Only the observation layer and failure policy differ
```

`sys.monitoring`'s per-code-object disable means the cost of observation **approaches zero for code that runs correctly
and repeatedly**. You only pay for events you haven't seen before, or events at exception sites. That's exactly the
right cost model for a test runner that's always watching.

---

## 6. SQLite as the Nervous System

**Q: Imagine this "always-on" system was driven by SQLite, which had an object model somewhat like git's database — a
huge pile of opaque JSON blobs with hashes, then a hierarchical computed/indexed view of different snapshots. The file
watcher would populate changes into the object store. Via transactions and triggers, a series of calculations would be
made: AST representations, CST representations, import/dependency graphs. All calculated quickly as hashes would let you
know what was out-of-date. Then, once that's done, services could happen. The database could also act as time-travel.**

### The Object Store

```sql
-- Immutable. Content-addressed. Never updated, only inserted.
CREATE TABLE objects
(
    hash       TEXT PRIMARY KEY, -- sha256
    type       TEXT NOT NULL,    -- 'blob'|'tree'|'ast'|'frame'|'result'
    content    BLOB NOT NULL,    -- raw bytes or JSON
    created_at REAL NOT NULL DEFAULT (unixepoch('now', 'subsec'))
);

-- Mutable pointers into the object store
CREATE TABLE refs
(
    name       TEXT PRIMARY KEY, -- 'HEAD'|'last_passing'|'before_change'
    hash       TEXT NOT NULL REFERENCES objects (hash),
    updated_at REAL NOT NULL DEFAULT (unixepoch('now', 'subsec'))
);

-- Current state of files on disk. Populated by watchfiles.
CREATE TABLE working_tree
(
    path       TEXT PRIMARY KEY,
    hash       TEXT    NOT NULL REFERENCES objects (hash),
    mtime      REAL    NOT NULL,
    size_bytes INTEGER NOT NULL
);

-- Computed from objects. Invalidated by hash mismatch.
CREATE TABLE derivations
(
    output_hash TEXT PRIMARY KEY REFERENCES objects (hash),
    input_hash  TEXT NOT NULL,
    kind        TEXT NOT NULL, -- 'ast'|'cst'|'imports'|'deps'|'test_result'
    cost_ms     REAL,
    derived_at  REAL NOT NULL DEFAULT (unixepoch('now', 'subsec'))
);
```

### JSON Schema for Key Object Types

```json
// AST Object
{
  "source_hash": "abc123...",
  "path": "src/auth.py",
  "nodes": {
    "imports": [
      {
        "module": "svcs",
        "line": 1
      }
    ],
    "functions": [
      {
        "name": "authenticate",
        "line_start": 10,
        "line_end": 24,
        "calls": [
          "db.find_user",
          "hash_password"
        ]
      }
    ]
  }
}

// Test Result
{
  "test_ref": [
    "tests.test_auth",
    "test_login_success"
  ],
  "dep_hashes": {
    "src/auth.py": "abc123..."
  },
  "passed": true,
  "duration_ns": 45231000,
  "observation": {
    "lines_hit": [
      ...
    ],
    "exception_sites": []
  }
}

// Frame Snapshot
{
  "test_ref": [
    "tests.test_auth",
    "test_login_fails"
  ],
  "exception": "AssertionError",
  "frames": [
    {
      "file": "src/auth.py",
      "line": 18,
      "function": "authenticate",
      "locals": {
        "user": {
          "repr": "User(id=1, role='viewer')",
          "type": "User"
        },
        "required_role": {
          "repr": "'admin'",
          "type": "str"
        }
      }
    }
  ]
}
```

### Triggers as Reactive Computation

```sql
CREATE TABLE work_queue
(
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT    NOT NULL,
    input_hash  TEXT    NOT NULL,
    path        TEXT,
    priority    INTEGER NOT NULL DEFAULT 5,
    enqueued_at REAL    NOT NULL DEFAULT (unixepoch('now', 'subsec')),
    UNIQUE (kind, input_hash)
);

-- file change → enqueue AST parse
CREATE TRIGGER trg_file_updated
    AFTER UPDATE OF hash
    ON working_tree
    WHEN OLD.hash != NEW.hash
BEGIN
DELETE
FROM derivations
WHERE input_hash = OLD.hash;
INSERT
OR IGNORE INTO work_queue(kind, input_hash, path, priority)
    VALUES ('parse_ast', NEW.hash, NEW.path, 1);
END;

-- AST ready → enqueue import resolution
CREATE TRIGGER trg_ast_ready
    AFTER INSERT
    ON derivations
    WHEN NEW.kind = 'ast'
BEGIN
    INSERT OR IGNORE INTO work_queue(kind, input_hash, path, priority)
    VALUES ('resolve_imports', NEW.output_hash, NULL, 2);
END;

-- imports ready → enqueue dep graph
-- deps ready → enqueue affected tests
-- (cascade continues automatically)
```

### Time-Travel: Snapshot Model

```sql
CREATE TABLE snapshots
(
    hash        TEXT PRIMARY KEY,
    parent_hash TEXT REFERENCES snapshots (hash),
    label       TEXT,
    created_at  REAL NOT NULL DEFAULT (unixepoch('now', 'subsec'))
);

CREATE TABLE snapshot_tree
(
    snapshot_hash TEXT NOT NULL REFERENCES snapshots (hash),
    path          TEXT NOT NULL,
    object_hash   TEXT NOT NULL REFERENCES objects (hash),
    PRIMARY KEY (snapshot_hash, path)
);

-- Test result timeline with LAG for change detection
CREATE VIEW test_timeline AS
SELECT json_extract(o.content, '$.test_ref')    as test_ref,
       json_extract(o.content, '$.passed')      as passed,
       json_extract(o.content, '$.duration_ns') as duration_ns,
       o.created_at,
       LAG(json_extract(o.content, '$.passed'))
                                                   OVER (PARTITION BY json_extract(o.content, '$.test_ref')
              ORDER BY o.created_at) as prev_passed
FROM objects o
WHERE o.type = 'test_result';

-- Tests that recently changed status (flaky candidates)
CREATE VIEW status_changes AS
SELECT test_ref, passed, prev_passed, created_at
FROM test_timeline
WHERE passed != prev_passed AND prev_passed IS NOT NULL;
```

### Frame History for Time-Travel Debugging

```sql
-- What was different in locals between the last two failures?
CREATE VIEW frame_history AS
SELECT json_extract(o.content, '$.test_ref') as test_ref,
       json_extract(o.content, '$.frames')   as frames,
       o.created_at,
       LAG(json_extract(o.content, '$.frames'))
                                                OVER (PARTITION BY json_extract(o.content, '$.test_ref')
              ORDER BY o.created_at) as prev_frames
FROM objects o
WHERE o.type = 'frame_snapshot';
```

### The Cascade in One Picture

```
watchfiles
    │
    ▼
working_tree (upsert)
    │
    └─► [trigger] → work_queue: parse_ast
                         │
                         ▼
                    objects: blob → ast
                    derivations (ast)
                         │
                    [trigger] → work_queue: resolve_imports
                                     │
                                     ▼
                                objects: imports
                                derivations (imports)
                                     │
                                [trigger] → work_queue: resolve_deps
                                                 │
                                                 ▼
                                            objects: dep_graph
                                            derivations (deps)
                                                 │
                                            [trigger] → work_queue: run_test
                                                             │
                                                             ▼
                                                        subinterpreter
                                                        svcs container
                                                        sys.monitoring
                                                             │
                                                        objects: test_result
                                                        objects: frame_snapshot
                                                        snapshots (HEAD)
```

The database is not storing results. It **is the computation**. Every layer is content-addressed, so work is never
repeated. Every layer is queryable JSON, so any question about any state — past or present — is a SQL query.

---

## 7. Analysis

**Q: First, the skeptical view — does this have a chance of fulfilling its ambition? Then the ambitious view: what crazy
new ideas could it spawn when tied to a "holy grail" Flywheel agent?**

### The Skeptical View

#### The Complexity Cliff

```python
components = [
    "watchfiles integration",
    "content-addressable object store",
    "SQLite trigger pipeline",
    "AST/CST extraction workers",
    "import graph resolver",
    "RegistrySpec serialization",
    "subinterpreter orchestration",
    "LayeredContainer across scopes",
    "sys.monitoring multi-slot management",
    "frame snapshot capture",
    "work queue priority scheduling",
    "snapshot/ref system",
    "time-travel query views",
    "t-string assertion engine",
    "git integration",
]
# Each individually is manageable.
# Together they form a distributed system
# that happens to run on one machine.
```

#### SQLite Is Not a Computation Engine

```
1. Triggers are synchronous and blocking
   A slow AST parse inside a trigger blocks the writer
   You end up moving work OUT of triggers anyway

2. JSON in SQLite is not typed
   json_extract(o.content, '$.frames[0].locals.user.repr')
   This is strings all the way down.
   No schema enforcement. Silent null on typo.

3. The "reactive pipeline" is actually polling
   SELECT ... FROM work_queue ORDER BY priority LIMIT 1
   You've built a worse version of celery inside a file on disk

4. Transactions and triggers don't compose cleanly
   with async Python workers
   You will fight connection contention constantly
```

#### The Hash Invalidation Bootstrap Problem

```python
# The dependency graph doesn't exist yet on:
# - First run ever
# - After a large refactor
# - After switching branches

# Static analysis can't tell without full call graph
# Dynamic tracking requires running the tests first
# Which requires knowing which tests to run
# Which requires the dependency graph

# The thing you most want to avoid
# is unavoidable at the moments of highest churn
```

#### Subinterpreters Are Not Production-Ready

```python
# Many C extensions don't support subinterpreters:
# numpy: not ready
# sqlalchemy: not ready  
# Most database drivers: not ready

# Your test suite almost certainly uses one of these.
# The isolation guarantee evaporates when your
# service factory imports a non-compliant extension.
```

#### sys.monitoring Sharp Edges

```python
# The per-code-object disable is the killer feature.
# It's also a subtle correctness hazard.

# If factory() calls helper() and helper() was already
# disabled from a previous test, we miss that test_b
# also depends on helper(). The graph is silently incomplete.

# Also: tool slots
# sys.monitoring gives you 6 user slots
# Python 3.15 profiler takes one
# We want: deps, coverage, profiling, debugging = 4 more
# Slot exhaustion is silent and hard to debug.
```

#### The Object Store Grows Forever

```
A busy developer: 100 saves/hour × 8 hours = 800 blobs/day
Each with AST derivation, import graph, dep graph
Frame snapshots for every failure (potentially large)
After one month: the database is the project

"But we can GC old objects"
Now you need a GC that understands reachability from refs.
You've reimplemented git object GC
for a schema you control less well.
```

#### The Honest Summary

```
What works well:
  ✓ Content-addressable storage concept (solid)
  ✓ watchfiles + SQLite for change tracking (solid)
  ✓ Test result history as queryable data (solid)
  ✓ sys.monitoring for dep tracking (solid with caveats)
  ✓ svcs for service lifecycle (solid in single interpreter)

What is genuinely hard:
  ✗ Trigger pipeline vs async workers (impedance mismatch)
  ✗ Cold start / bootstrap cycle (no clean solution)
  ✗ Subinterpreter extension compatibility (years away)
  ✗ Frame snapshot storage at scale (unbounded growth)
  ✗ Factory serialization constraints (leaks into user code)

The deepest problem:
  The system is most valuable when the codebase is most stable.
  It is most broken when the codebase is most in flux.
  That's an inversion of what developers need.
```

---

### The Ambitious View: The Flywheel Agent

#### The Database Is a Model of Your Codebase's Mind

```python
# What we've actually built, if it works:
# Every function that has ever existed: stored
# Every import relationship: stored and queryable
# Every test execution: stored with full frame data
# Every failure: stored with locals at every frame
# Every change: stored with before/after

# An agent with access to this database
# doesn't need to "understand" your code.
# It can QUERY your code's behavior.
```

#### Failure as a Fully-Specified Repair Problem

```sql
-- When a test fails, the agent gets a complete query interface:

-- "What changed since this test last passed?"
SELECT path, hash_before, hash_after
FROM snapshot_diff
WHERE snapshot_a = last_passing_snapshot
  AND snapshot_b = 'HEAD'
  AND change_type = 'modified';

-- "What were the locals at the failure site last time it passed?"
SELECT prev_frames
FROM frame_history
WHERE test_ref = :failing_test
ORDER BY created_at DESC LIMIT 1;

-- "Which specific locals differ between passing and failing?"
-- (the frame diff view)
```

```python
async def repair_cycle(failing_test: str, agent: FlywheelAgent):
    context = await db.query("""
        SELECT 
            changed_files,
            changed_functions,  -- AST diff, not just file diff
            locals_at_failure,
            locals_at_last_pass,
            other_affected_tests,
            historical_failure_rate
        FROM failure_context WHERE test_ref = ?
    """, failing_test)

    # Agent has complete information. Not "here's a stack trace, good luck."
    # Here's exactly what changed, what the values were,
    # and every other test that will break if you fix it the wrong way.
    patch = await agent.propose_repair(context)
    # Apply patch → triggers fire → tests run. The flywheel turns immediately.
```

#### The Agent Learns Your Codebase's Failure Grammar

```python
class FailureGrammar:
    """
    Mined from test_timeline + frame_history + snapshot_diff.
    These are YOUR codebase's specific failure modes.
    Not generic programming knowledge. No LLM needed for pattern recognition.
    SQL is sufficient.
    """

    async def find_analogous_failures(self, current_failure):
        return await db.query("""
            SELECT 
                fh.frames as failure_frames,
                sd.path as what_changed,
                next_passing.snapshot_hash as fix_snapshot
            FROM frame_history fh
            JOIN snapshot_diff sd ON ...
            WHERE json_extract(fh.frames, '$[0].function') 
                = json_extract(:current_frames, '$[0].function')
            ORDER BY similarity_score DESC
            LIMIT 5
        """)
```

#### Speculative Execution: Testing Changes Before You Make Them

```python
class SpeculativeRunner:

    async def evaluate_patch(self, patch, agent):
        # 1. Apply patch to in-memory object store (don't touch disk)
        speculative_hashes = self._apply_patch_to_store(patch)

        # 2. Compute which tests are affected (pure SQL, no execution)
        affected = await self._query_affected_tests(speculative_hashes)

        # 3. Run only affected tests with speculative source
        results = await self.runner.run(
            affected, source_override=speculative_hashes
        )

        return SpeculativeResult(
            tests_fixed=results.newly_passing,
            tests_broken=results.newly_failing,
            net_health_delta=len(results.newly_passing)
                             - len(results.newly_failing)
        )

    async def search_repair_space(self, target_test, agent):
        """
        Agent proposes patches. We evaluate speculatively.
        No disk writes until we're confident.
        The database IS the sandbox.
        """
        candidates = await agent.propose_patches(
            failure_context=self.db, target=target_test
        )
        results = await asyncio.gather(*[
            self.evaluate_patch(p, agent) for p in candidates
        ])
        return max(
            (r for r in results if not r.tests_broken),
            key=lambda r: r.net_health_delta
        )
```

#### The Flywheel: Continuous Autonomous Health Maintenance

```python
class FlywheelAgent:
    """
    Not a code generator. Not a chat interface.
    A continuous background process that maintains
    codebase health as a thermostatic goal.
    The database tells it the distance from target at all times.
    """

    async def run(self):
        async for event in self.db.subscribe_to_changes():
            match event:

                case TestFailed(test_ref, failure_context):
                    known = await self.grammar.find_analogous(failure_context)
                    if known and known.fix_confidence > 0.9:
                        patch = known.generate_patch()
                        result = await self.speculative.evaluate_patch(patch)
                        if result.is_clean:
                            await self.propose_to_developer(patch, result)
                    else:
                        await self.request_replay_with_profile(test_ref)

                case PerformanceRegression(test_ref, delta_ns):
                    hotspot = await self.db.query("""
                        SELECT function, avg_duration_ns
                        FROM profile_timeline
                        WHERE test_ref = ?
                        ORDER BY duration_delta DESC LIMIT 1
                    """, test_ref)
                    await self.annotate_code(hotspot)

                case TestNeverRun(test_ref):
                    await self.db.execute("""
                        INSERT INTO work_queue(kind, input_hash, priority)
                        VALUES ('run_test', ?, 1)
                    """, test_ref)
```

#### Tests As Executable Specifications That Write Themselves

```python
class SpecificationMiner:
    """
    The object store has every function signature, every call site,
    every set of locals at every call, every return value.
    This is a complete input/output record for every function
    that has ever been exercised.
    """

    async def generate_tests_for(self, function_ref: str) -> list[Test]:
        call_patterns = await self.db.query("""
            SELECT 
                json_extract(frames, '$[?(@.function == :fn)].locals') 
                    as observed_inputs,
                COUNT(*) as frequency
            FROM frame_history
            WHERE json_extract(frames, '$[*].function') LIKE :fn_pattern
            GROUP BY observed_inputs
            ORDER BY frequency DESC
        """, fn=function_ref)

        # Each observed input pattern becomes a test case
        # grounded in real usage - not generic, not hallucinated
        return [self._pattern_to_test(p) for p in call_patterns]
```

#### The Real Holy Grail

```
What we've been describing, if fully realized, is not a test runner.

It's a system where:

  THE CODEBASE KNOWS ITS OWN HISTORY
  and can answer questions about it.

  THE AGENT OPERATES ON FACTS
  not on source code text.

  SPECULATIVE EXECUTION IS FREE
  because the database is the sandbox.

  DEVELOPER CONFIRMATION IS THE ONLY GATE
  for net-positive changes.

The shift isn't "AI writes your code."
It's closer to:
  "Your codebase has developed an immune system
   that understands its own pathology."

The developer's role changes from
  "fix the failing test"
to
  "confirm this proposed fix matches my intent"
or more radically:
  "override the immune system's decision"

Which raises the question the skeptic would ask:
If the system is right 95% of the time,
do developers lose the ability to understand
why things fail at all?

That's not a technical problem.
That's the actual design question.
```

---

## 8. Flywheel Signal Collection via the Execution Engine

**Q: The Flywheel idea depends on capturing high-quality signals from real interactions — which tool was called, which
result fields were accessed, whether multi-step workflows ran correctly, and whether the outcome was good. Could this
execution engine — its SQLite object store, sys.monitoring instrumentation, and reactive pipeline — serve as the
sensor layer for the Flywheel? What specifically could sys.monitoring observe during Monty code execution that would
be directly useful as training data?**

### The Core Opportunity

The execution engine built in Sections 1–6 was motivated by test running. But the machinery is domain-agnostic: it
observes Python execution, content-addresses results, and cascades reactive computation from file changes. A Punie
interaction is just a different kind of Python execution — Monty runs LLM-generated code that calls tool functions
and accesses structured results.

```
TEST RUNNER                         PUNIE FLYWHEEL
────────────────────────────────────────────────────
Subject: test functions             Subject: Monty-generated code
Observation: which lines execute    Observation: which tool results accessed
Event: AssertionError raised        Event: domain validation failed
Signal: test passed/failed          Signal: code correct/incorrect for domain
Ground truth: test suite            Ground truth: branch merged / user confirmed
Database: test_result objects       Database: punie_event objects
```

The same `sys.monitoring` hooks, the same SQLite cascade, the same content-addressed object store — pointed at
the Punie execution loop instead of a test suite.

### sys.monitoring Events During Monty Execution

The Monty sandbox runs LLM-generated Python code. That code calls external functions (the tools) and then accesses
fields on the returned Pydantic result objects. Every interesting moment in this execution is observable.

**What fires when:**

```python
# Generated code:
result = typecheck("src/")             # → C_START on the sync bridge function
if result.error_count > 0:            # → LINE event; JUMP event (branch taken/not taken)
    for error in result.errors:        # → LINE event; loop entry
        print(f"{error.file}:{error.line}")  # → LINE events inside loop

# If result.errors is None (the git_log bug):
for error in result.errors:           # → RAISE (TypeError/NoneType)
                                       # → EXCEPTION_HANDLED or propagates up
```

The events that matter most, in order of value:

| Event | What it reveals | Cost |
|-------|----------------|------|
| `C_START` on tool bridges | Which tool was called, with what args | Near-zero |
| `C_RETURN` on tool bridges | Tool execution succeeded, result shape | Near-zero |
| `RAISE` | Code failed — field access error, wrong type, None field | Near-zero |
| `EXCEPTION_HANDLED` | Model recovered from an error gracefully | Near-zero |
| `JUMP` | Which branch of `if result.X > 0` was taken | Low |
| `LINE` (selective) | Which lines in generated code executed | Medium |

**Installing the sensor:**

```python
class PunieSensor:
    """
    sys.monitoring observer for Monty code execution.
    Emits PunieEvents to the SQLite store.

    Uses per-code-object disable so it only pays for
    events it hasn't seen before — same trick as DependencyTracker.
    """

    TOOL_ID = sys.monitoring.OPTIMIZER_ID  # use an available slot

    def install(self, session_id: str, spec_ref: str | None):
        self._session_id = session_id
        self._spec_ref = spec_ref
        self._tool_call_stack: list[ToolCallEntry] = []
        self._emitted: list[PunieEvent] = []

        sys.monitoring.set_tool(self.TOOL_ID, "punie_sensor")
        sys.monitoring.set_events(
            self.TOOL_ID,
            sys.monitoring.events.C_START |    # tool function entries
            sys.monitoring.events.C_RETURN |   # tool function returns
            sys.monitoring.events.RAISE |      # failures
            sys.monitoring.events.EXCEPTION_HANDLED,  # recoveries
        )
        sys.monitoring.register_callback(self.TOOL_ID, sys.monitoring.events.C_START,   self._on_c_start)
        sys.monitoring.register_callback(self.TOOL_ID, sys.monitoring.events.C_RETURN,  self._on_c_return)
        sys.monitoring.register_callback(self.TOOL_ID, sys.monitoring.events.RAISE,     self._on_raise)

    def _on_c_start(self, code, instruction_offset, callable, arg0):
        # Filter: only care about our sync bridge functions
        if not _is_punie_tool_bridge(callable):
            return sys.monitoring.DISABLE  # never pay for this again

        self._tool_call_stack.append(ToolCallEntry(
            tool_name=callable.__name__,
            args=_safe_serialize(arg0),
            started_at=time.monotonic(),
        ))

    def _on_c_return(self, code, instruction_offset, callable, retval):
        if not self._tool_call_stack:
            return
        entry = self._tool_call_stack.pop()

        self._emitted.append(PunieEvent(
            event_type="tool_call",
            session_id=self._session_id,
            tool_name=entry.tool_name,
            tool_args=entry.args,
            tool_result_summary=_summarize_result(retval),
            # fields_accessed filled in later by attribute proxy (see below)
        ))

    def _on_raise(self, code, instruction_offset, exception):
        frame = sys._getframe(1)
        self._emitted.append(PunieEvent(
            event_type="raise_in_generated_code",
            session_id=self._session_id,
            tool_name=_infer_context(frame),
            validation_errors=[f"{type(exception).__name__}: {exception}"],
            original_code=_get_generated_code(frame),
        ))
```

### The Attribute Proxy: Tracking Field Access for Free

`sys.monitoring` does not have an `ATTR_ACCESS` event. But we don't need one. The Pydantic result objects
returned by tools can be wrapped in a thin proxy that records every `.field` access before returning the value.

This is the direct solution to the "field access" gap (60% accuracy in Phase 27.5 — the model calls tools but
doesn't reliably access result fields). Rather than guessing from static analysis, we *observe* what the
generated code actually reads at runtime:

```python
class FieldAccessProxy:
    """
    Wraps a Pydantic result model. Records every attribute access.
    Transparent to the generated code — it sees the same interface.
    Emits field access data to the PunieSensor.

    The model generates: if result.error_count > 0: ...
    The proxy intercepts: result.__getattr__("error_count") → record "error_count" accessed
    """

    __slots__ = ("_wrapped", "_accessed", "_sensor", "_tool_name")

    def __init__(self, wrapped, sensor: PunieSensor, tool_name: str):
        object.__setattr__(self, "_wrapped", wrapped)
        object.__setattr__(self, "_accessed", [])
        object.__setattr__(self, "_sensor", sensor)
        object.__setattr__(self, "_tool_name", tool_name)

    def __getattr__(self, name: str):
        object.__getattribute__(self, "_accessed").append(name)
        return getattr(object.__getattribute__(self, "_wrapped"), name)

    def __del__(self):
        # When proxy goes out of scope, report what was accessed
        sensor = object.__getattribute__(self, "_sensor")
        accessed = object.__getattribute__(self, "_accessed")
        tool = object.__getattribute__(self, "_tool_name")
        if accessed:
            sensor.record_field_access(tool, accessed)
```

The sync bridge functions in `toolset.py` wrap their return values:

```python
# Before (in toolset.py):
def sync_typecheck(path: str) -> TypeCheckResult:
    ...
    return result

# After:
def sync_typecheck(path: str) -> TypeCheckResult:
    ...
    sensor = get_active_sensor()  # thread-local, set by execution context
    return FieldAccessProxy(result, sensor, "typecheck") if sensor else result
```

Now every interaction automatically records:
- `result.error_count` was accessed (positive signal if code checks it)
- `result.errors` was iterated (positive signal for list traversal)
- `result.success` was never accessed (the model skipped the guard check)
- Accessing `result.author` on a `GitLogResult` raised `AttributeError` (the git_log bug, caught automatically)

This is the "execution-level telemetry" the flywheel doc identifies as critical. Not "did the model say
`result.error_count`" (keyword presence, meaningless), but "did the code *execute* that access."

### Branch Coverage as Decision Pattern Signal

The `JUMP` event fires when the interpreter takes or skips a conditional branch. For Flywheel, the most
valuable conditional is exactly: `if result.X > 0:` — the pattern that distinguishes models that check
results before using them from models that blindly iterate.

```python
# Turn on JUMP selectively for generated code blocks:
sys.monitoring.set_events(
    TOOL_ID,
    sys.monitoring.events.C_START |
    sys.monitoring.events.C_RETURN |
    sys.monitoring.events.RAISE |
    sys.monitoring.events.JUMP,   # ← add branch tracking
)

def _on_jump(self, code, instruction_offset, destination_offset):
    # Is this jump inside the generated code block?
    if not _is_generated_code_frame(code):
        return sys.monitoring.DISABLE

    # Was this a forward jump (if branch taken)?
    # Was this a backward jump (loop iteration)?
    branch_type = "loop" if destination_offset < instruction_offset else "conditional"

    self._branches.append(BranchRecord(
        code_line=code.co_firstlineno,
        branch_type=branch_type,
        taken=True,  # JUMP fires when branch IS taken
    ))
```

Combined with the generated code's AST (stored in the object store as a derivation), branch records answer:
- Did the model generate an `if result.error_count > 0:` guard? (AST check)
- Did it execute when the result actually had errors? (JUMP record)
- Did it iterate the full list, or break early? (loop iteration count)

This is training signal at a resolution no static analysis can achieve.

### Frame Snapshots as Automatic Contrastive Pairs

The `RAISE` event fires when domain validation fails. The frame at that moment contains everything needed
for a contrastive training pair — automatically, without any human annotation:

```python
def _on_raise(self, code, instruction_offset, exception):
    if not isinstance(exception, DomainValidationError):
        return

    frame = sys._getframe(1)
    generated_code = _get_generated_code_from_context()

    # Store the complete failure snapshot in the object store
    failure_hash = db.store_object("punie_failure", {
        "session_id": self._session_id,
        "validator": exception.validator_name,
        "generated_code": generated_code,       # what the model wrote
        "validation_errors": exception.errors,  # what was wrong
        "fields_accessed_so_far": self._accessed_log,
        "frame_locals": _safe_capture_locals(frame),
    })

    # The RETRY event fires when the model corrects this.
    # At that point, we have: original_code + error + corrected_code
    # = a complete error→fix contrastive pair, zero human effort.
    self._pending_failure = failure_hash
```

When the model retries after seeing the validation error and succeeds, the sensor links the failure
snapshot to the successful generation — producing a `(wrong_code, error_message, correct_code)` triple
that is precisely the contrastive training format Phase 26 used to jump field access from 5% to 90%.

### The SQLite Cascade for Flywheel Events

The `PunieEvent` records fit directly into the object store from Section 6. The trigger cascade
that drove test dependency resolution can drive Flywheel data quality instead:

```sql
-- Punie interactions stored as content-addressed objects
INSERT INTO objects (hash, type, content) VALUES
    (:hash, 'punie_event', json(:event_data));

-- New tool_call event → enqueue field access summary
CREATE TRIGGER trg_tool_call_ready
    AFTER INSERT ON objects
    WHEN NEW.type = 'punie_event'
      AND json_extract(NEW.content, '$.event_type') = 'tool_call'
BEGIN
    INSERT OR IGNORE INTO work_queue(kind, input_hash, priority)
    VALUES ('summarize_field_access', NEW.hash, 2);
END;

-- New retry event with linked failure → enqueue training example extraction
CREATE TRIGGER trg_retry_pair_ready
    AFTER INSERT ON objects
    WHEN NEW.type = 'punie_event'
      AND json_extract(NEW.content, '$.event_type') = 'retry'
      AND json_extract(NEW.content, '$.original_code') IS NOT NULL
      AND json_extract(NEW.content, '$.corrected_code') IS NOT NULL
BEGIN
    INSERT OR IGNORE INTO work_queue(kind, input_hash, priority)
    VALUES ('extract_training_example', NEW.hash, 1);  -- high priority
END;

-- Branch merged → retroactively weight all events from that session
CREATE TRIGGER trg_branch_merged
    AFTER INSERT ON objects
    WHEN NEW.type = 'punie_event'
      AND json_extract(NEW.content, '$.event_type') = 'branch_merged'
BEGIN
    UPDATE objects
    SET content = json_set(content, '$.quality_weight', 1.2)
    WHERE type = 'punie_event'
      AND json_extract(content, '$.session_id')
          = json_extract(NEW.content, '$.session_id');
END;
```

### The Observe Flags for Punie Interactions

Adapting Section 5's `Observe` flag model to the Flywheel context:

```python
class PunieObserve(Flag):
    """What to pay attention to during a Punie interaction."""
    NOTHING = 0
    TOOL_CALLS   = auto()  # C_START/C_RETURN on bridge functions (near-zero cost)
    FIELD_ACCESS = auto()  # attribute proxy on result objects (near-zero cost)
    BRANCHES     = auto()  # JUMP events in generated code (low cost)
    RAISES       = auto()  # RAISE events anywhere in generated code (near-zero)
    FULL_TRACE   = auto()  # LINE events (medium cost, for debugging bad examples)

    # Normal operation: capture tool calls and field access
    NORMAL = TOOL_CALLS | FIELD_ACCESS | RAISES

    # During active model improvement cycle: add branch coverage
    TRAINING = TOOL_CALLS | FIELD_ACCESS | RAISES | BRANCHES

    # Diagnosing a specific failure: full trace
    DEBUG = TOOL_CALLS | FIELD_ACCESS | RAISES | BRANCHES | FULL_TRACE
```

Same interaction, same generated code, same tools — only the observation layer changes. In production,
`NORMAL` costs essentially nothing: only fires on bridge functions (a handful per interaction) and raises
(rare). `TRAINING` adds branch coverage for the generated code block only, gated on
`_is_generated_code_frame()` checks that disable themselves after first hit.

### What the System Captures vs. What the Flywheel Doc Describes

The flywheel document (`docs/research/flywheel-capture.md`) proposed a `PunieEvent` dataclass with
manually-populated fields. The execution engine makes most of those fields automatic:

| Signal | Flywheel doc approach | Execution engine approach |
|--------|----------------------|--------------------------|
| Which tool called | Instrument WebSocket handler | `C_START` fires automatically |
| Which fields accessed | Static analysis of generated code | `FieldAccessProxy.__getattr__` fires at runtime |
| Whether branch was taken | Not captured | `JUMP` event |
| Domain validation failure | Catch in result parser | `RAISE` fires with full frame |
| Error→fix pair | Manual linkage of retry events | `_pending_failure` + next success = automatic pair |
| Field access on None | Not captured | `RAISE` fires with `AttributeError` |
| Branch out: which session this belongs to | Manual session_id threading | `session_id` on sensor, attached to all events |
| Quality weight from branch outcome | Post-hoc SQL update | Trigger on `branch_merged` event |

The execution engine turns a manual instrumentation problem into an observation problem. You install the
sensor once; it observes everything after that.

### The Virtuous Cycle

```
Monty executes generated code
    │
    ▼
PunieSensor fires (C_START, C_RETURN, RAISE, JUMP)
FieldAccessProxy fires (__getattr__)
    │
    ▼
objects: punie_event records (content-addressed, immutable)
    │
    └─► [trigger] → work_queue: summarize_field_access
    └─► [trigger, on RAISE] → work_queue: extract_contrastive_pair
    └─► [trigger, on branch_merged] → retroactive quality weighting
    │
    ▼
work_queue workers:
    - extract_training_example: converts event pairs → ChatML format
    - summarize_field_access: compute field access frequency distributions
    - update_failure_grammar: add new failure mode to failure_grammar table
    │
    ▼
training_examples table:
    - error→fix pairs (from RAISE + retry)
    - positive tool_call examples (from successful interactions)
    - cross-tool sequences (from multi-event session patterns)
    - weighted by branch outcome
    │
    ▼ (weekly)
Fine-tuning run on accumulated examples
    │
    ▼
Better model → fewer RAISE events → fewer retries → better data
```

The flywheel doesn't need to "start." It runs automatically from the moment the sensor is installed.
Every Punie interaction contributes to the next training cycle without any manual annotation.

### One Insight That Doesn't Fit Elsewhere

`sys.monitoring`'s per-code-object disable is designed for test running, where a function
`helper()` is called many times across many tests and you only need to record it once.

For Flywheel, the same mechanism serves a different purpose: **deduplication of training examples**.
If the model generates nearly identical code in two interactions, the same code objects execute.
The sensor can detect this via the code object hash and avoid generating redundant training examples.
Only genuinely new code patterns contribute to the training set.

This directly addresses the "345 junk examples" problem from Phase 27.5 — where volume metrics
looked good but examples were repetitive loops with only the index changing. The execution engine
makes deduplication structural rather than a filtering step.

---

## 9. Developer Execution as Flywheel Input

**Q: The signal collection in Section 8 assumed the agent is in the loop — monitoring Monty code execution, watching
tool calls, catching validation failures. But what about the developer's own work? When they run tests, fix failures,
change files, and exercise domain code during normal development of a web application — could the execution engine
observe *that* and feed it into the Flywheel? Punie doesn't need to be involved at all.**

### The Shift in Perspective

Section 8 described Punie as the subject: observe what the agent does, capture its mistakes, collect its successes.
This section describes the developer as the subject: observe what the developer does, and let that build the
agent's domain model before the agent is ever asked anything.

```
SECTION 8 MODEL                   SECTION 9 MODEL
────────────────────────────────────────────────────────
Subject: Punie generates code      Subject: Developer writes/runs code
Signal: Agent called wrong tool    Signal: Test failed, developer fixed it
Captures: tool use competence      Captures: domain knowledge
Requires: Punie to be in loop      Requires: developer to run tests
Value: teaches tool calling        Value: teaches THIS codebase
```

The developer runs tests constantly. Every run is a free data collection session. The execution engine is
already watching.

### Test Failure → Fix as Training Pairs

The `test_timeline` view from Section 6 records every test status change. When a test goes from failing
to passing, the object store holds:

1. **The frame snapshot** at the moment of failure — locals at every frame on the call stack, including
   the values of real domain objects (`UserService`, `PaymentResult`, actual tdom components)

2. **The snapshot diff** between the failing run and the passing run — exactly which lines changed in
   which files

3. **The AST derivation** of both versions — structural diff, not just text diff

Together these form a `(broken_code, error_context, fix)` triple with no annotation required:

```python
class FailurePairExtractor:
    """
    Watches test_timeline for status changes.
    When a test moves failing → passing, constructs a training pair.
    """

    async def watch(self):
        async for change in self.db.subscribe("test_timeline", "status_changes"):
            if change["prev_passed"] is False and change["passed"] is True:
                await self._extract_pair(change["test_ref"])

    async def _extract_pair(self, test_ref: str):
        # Get the frame snapshot from the last failure
        failure = await self.db.query("""
            SELECT content FROM objects
            WHERE type = 'frame_snapshot'
              AND json_extract(content, '$.test_ref') = ?
            ORDER BY created_at DESC LIMIT 1
        """, test_ref)

        # Get the snapshot diff: what changed between failure and fix
        diff = await self.db.query("""
            SELECT * FROM snapshot_diff
            WHERE snapshot_a = (SELECT hash FROM refs WHERE name = 'last_failing')
              AND snapshot_b = (SELECT hash FROM refs WHERE name = 'HEAD')
        """)

        # The training pair:
        # - What the code looked like when it broke (from AST at failure snapshot)
        # - What the error was (from frame snapshot locals)
        # - What changed to fix it (from snapshot diff)
        # This is a real (broken_code → error → fix) triple, from real domain code
        pair = TrainingPair(
            broken_code=await self._get_code_at(failure["snapshot_hash"]),
            error_type=failure["exception"],
            error_locals=failure["frames"][0]["locals"],
            fix_diff=diff["changed_lines"],
            fixed_code=await self._get_code_at("HEAD"),
            domain_context=await self._infer_domain_context(test_ref),
        )
        await self.db.store_training_pair(pair)
```

A developer who runs tests regularly and fixes failures generates dozens of these pairs per week.
Each one is richer than anything synthetic: real domain objects, real error messages, real fixes
in real project structure.

### sys.monitoring During Test Runs: The Domain Oracle

When the developer runs their test suite with `sys.monitoring` active, every test execution is a
controlled experiment in domain behavior. The execution engine observes what no static analysis
can infer:

**`PY_RETURN` — what do domain functions actually return?**

```python
class DomainOracleCollector:
    """
    Records actual input/output pairs for domain functions.
    After enough test runs, the database is an oracle for domain behavior.
    """

    def _on_return(self, code, instruction_offset, retval):
        if not _is_domain_function(code):
            return sys.monitoring.DISABLE

        frame = sys._getframe(1)
        self.db.record_observation(
            function=code.co_qualname,
            module=code.co_filename,
            args=_safe_capture_locals(frame),    # actual input values
            return_value=_safe_serialize(retval), # actual output
            test_context=self._current_test,
        )
```

After 100 test runs, the database knows: "`user_service.get_user(user_id=1)` typically returns
`User(id=1, name='Alice', role='admin')` — here are 47 examples with their inputs and outputs."

When Punie later generates code calling `user_service.get_user()`, it can draw on those 47
observed input/output pairs. Not generic Python knowledge about what functions return. Knowledge
about what *this function, in this codebase, with these actual domain objects* returns.

**`RAISE` — what errors are native to this domain?**

```python
class DomainFailureGrammar:
    """
    Mines the frame history for recurring failure patterns specific to this codebase.
    These are not generic Python errors. They are THIS domain's failure modes.
    """

    async def get_common_errors(self) -> list[FailurePattern]:
        return await self.db.query("""
            SELECT
                json_extract(content, '$.exception')        as error_type,
                json_extract(content, '$.frames[0].function') as where,
                COUNT(*) as frequency,
                GROUP_CONCAT(
                    json_extract(content, '$.frames[0].locals'), '|||'
                ) as example_locals
            FROM objects
            WHERE type = 'frame_snapshot'
            GROUP BY error_type, where
            ORDER BY frequency DESC
            LIMIT 20
        """)
```

If `AttributeError: 'NoneType' object has no attribute 'id'` occurs 23 times in
`user_service.get_user()`, the Flywheel knows: this codebase has a pattern where `user_id`
can be None when passed to `get_user`. The agent trained on this data will generate defensive
checks (`if user_id is None: return None`) in exactly the right places — not because it was
told to, but because it learned the failure grammar of this specific codebase.

**`JUMP` — which code paths are actually exercised?**

The branch records from test runs answer: which `if/else` branches are tested, which are
dead code, which are on the hot path. Punie generating code for a hot path can draw on much
richer context than code for an untested edge case. The agent can calibrate its confidence:

```python
async def get_path_confidence(function_ref: str, branch_condition: str) -> float:
    """
    How often has this branch been exercised in test runs?
    High frequency = agent has good training signal.
    Low frequency = agent should hedge or ask for clarification.
    """
    row = await db.query("""
        SELECT
            COUNT(CASE WHEN taken = 1 THEN 1 END) as taken_count,
            COUNT(*) as total_count
        FROM branch_records
        WHERE function = ? AND condition_text = ?
    """, function_ref, branch_condition)
    return row["taken_count"] / max(row["total_count"], 1)
```

### The Import Graph as Ubiquitous Language

The import derivation pipeline (Section 6) builds a graph of which modules import which. For
Flywheel, the more important question is: which *domain types* appear together in which contexts?

```sql
-- Which services appear together in view functions?
-- (This is the "natural vocabulary" of this domain)
SELECT
    json_extract(a.content, '$.module') as view_module,
    GROUP_CONCAT(DISTINCT json_extract(s.content, '$.name')) as services_used
FROM objects a
JOIN objects s ON json_extract(s.content, '$.used_in') = json_extract(a.content, '$.module')
WHERE a.type = 'ast'
  AND json_extract(a.content, '$.nodes.decorators') LIKE '%view%'
  AND s.type = 'service_usage'
GROUP BY view_module;
```

If `UserService` appears alongside `AuthService` in 80% of view functions, and `PaymentService`
always appears with `AuditService`, the agent has learned the natural clustering of this domain
before being asked to write a single line. When the developer asks "add a checkout view", the
agent already knows that checkout views in this codebase involve `PaymentService` + `AuditService`
+ the `@view` decorator + keyword-only DI — without being explicitly told any of this.

### Spec-Driven Episodes: Automatic Ground Truth

If the developer uses agent-os specs, the spec file lands in the object store when it's created.
The cascade of file changes that follows — as the spec is implemented — is also in the object store.
The merge event is the ground truth label.

```
spec created → objects: spec_blob
    │
    ▼ (developer implements over hours/days)
file changes → objects: blob (content-addressed per version)
                        ast derivations
                        import graph updates
                        test failure/pass events
    │
    ▼
branch merged → refs: HEAD updated
                      snapshot diff (spec → implementation)
                      test_timeline (all passing at merge)
    │
    ▼
SpecEpisodeExtractor queries:
    - spec requirements (from spec blob)
    - which files changed (from snapshot diff)
    - what errors occurred and were fixed (from frame_history)
    - final quality: test suite passing (from test_timeline at merge)
    = Complete Layer 3 episode, zero manual annotation
```

The developer never did anything special. They wrote a spec, implemented it, fixed the failures,
and merged. The execution engine captured the entire arc. That's a training episode with ground
truth, real domain code, real error/fix pairs, and a quality label (merged + tests passing).

### What Punie Gains Before Being Asked Anything

After a month of normal development with the engine running, the object store contains:

| What's captured | What Punie learns |
|----------------|------------------|
| Frame snapshots from ~200 test failures | The failure grammar of this codebase |
| PY_RETURN observations from domain functions | What values domain objects actually hold |
| Import graph across all modules | The natural vocabulary and clustering of this domain |
| Failure→fix pairs from test timeline | How errors in this codebase get resolved |
| Spec episodes from merged branches | Complete spec → implementation patterns |
| Branch coverage across test suite | Which code paths are well-understood vs. novel |

When the developer finally asks Punie "add a user profile endpoint", the agent isn't starting
from generic Python knowledge. It's starting from a model of *this specific codebase's behavior* —
learned passively, while the developer was just doing their job.

### The Cold-Start Problem Inverted

The test running architecture in Section 7 has a cold-start problem: you need the dependency graph
to know which tests to run, but you need to run tests to build the dependency graph.

The Flywheel learning problem has the opposite shape: **it gets better the more the developer
works**. The first test run gives some signal. After a week, the failure grammar is sketched.
After a month, domain function behavior is well-characterized. After a year, the agent has
seen every common failure mode in this codebase and knows how each one was resolved.

The execution engine transforms normal development activity into a continuously-improving
domain model. The Flywheel isn't a separate process to run — it's a property of the
development environment.

---

*This conversation explored the design space of a modern Python test runner built on: `svcs` for dependency injection,
subinterpreters for isolation, `sys.monitoring` for low-cost always-on observation, SQLite as a content-addressable
reactive computation engine, and a Flywheel agent that treats the accumulated execution history as a queryable model of
codebase behavior.*