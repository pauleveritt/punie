# Strategic Analysis: LSP Tools + Domain Tools as Next Phases

**Date:** 2026-02-15
**Status:** Analysis Complete
**Scope:** Evaluating Phase 26 (LSP integration) and Phase 27 (domain typed tools) as strategic directions

---

## Executive Summary

This analysis evaluates two strategic directions for Punie's post-Phase 25 roadmap:

1. **LSP Integration (Phase 26)** — Semantic code operations using ty's language server
2. **Domain Typed Tools (Phase 27)** — Holy grail Part B: tools that think in domain vocabulary

**Key Findings:**

- **Both directions are ready for implementation** — infrastructure exists, patterns proven, source materials available
- **LSP first, then domain tools** — LSP is lower risk, establishes semantic tool patterns, and ty is already available
- **Domain tools have highest strategic impact** — changes what the model reasons about (design decisions), not just how it navigates code
- **Training data strategy is clear** — LSP examples (~100) teach navigation/refactoring, domain examples (~150) teach domain reasoning workflows

---

## Question 1: How Useful is ty LSP? Are We Ready?

### Usefulness: Very High

The research documents (`integrate-lsp-into-agent-loop.md`, `lsp-trained-models.md`) establish that LSP provides **grounded code understanding** — real symbol locations, type information, and reference graphs vs. text grep.

**What LSP provides over text-based tools:**

| Text-Based Tool | Limitation | LSP Equivalent | Benefit |
|----------------|------------|----------------|---------|
| `grep "class Foo"` | Matches strings in comments, docstrings, literals | `goto_definition(symbol="Foo")` | Precise symbol location |
| `grep -r "AgentConfig"` | No type context | `hover(file, pos)` | Type info + docstring |
| Find all usages | Manual text search, false positives | `find_references(symbol)` | Semantic usage tracking |
| Rename across files | Text replacement, unsafe | `rename_symbol(old, new)` | Safe refactoring |
| File outline | Parse manually or grep headers | `document_symbols(file)` | Structured outline |

**Research Gap Identified:**

The gap table in `lsp-trained-models.md` confirms: **nobody has integrated LSP actions + RL training + coding agents**. This is an open research opportunity with clear value.

### Readiness: Yes

**Infrastructure is proven:**

1. **Typed tools pattern exists** (`typed_tools.py`)
   - `TypeCheckResult`, `RuffResult`, `TestResult` all follow the same pattern
   - Pydantic models define structured output
   - Parsers convert tool output to Python objects
   - Model interacts with structured data, not raw text

2. **Sandbox bridge pattern established** (`toolset.py`)
   - `sync_typecheck()`, `sync_ruff_check()`, `sync_pytest_run()`
   - All use same pattern: call external tool → parse output → return typed result
   - LSP would follow: call ty LSP server → parse JSON-RPC response → return `LSPResult`

3. **Stub generation works** (`stubs.py`)
   - Automatic system prompt generation
   - Function signatures with type hints
   - Docstrings explaining when/how to use tools

4. **ty is already installed and used**
   - Currently used for type checking via `ty check`
   - LSP server capability exists in ty
   - Just need to connect via JSON-RPC/stdio

5. **Training data generation scripts exist as templates**
   - `scripts/generate_ty_training_data.py` shows the pattern
   - Generate examples showing LSP usage
   - Contrast with text-based approaches

**What ty LSP gives Punie's model:**

```python
# Navigation
result = lsp_query("goto_definition", symbol="AgentConfig", file="src/punie/agent/config.py")
# → LSPResult(file="src/punie/agent/config.py", line=42, symbol_type="class", docstring="...")

# References
result = lsp_query("find_references", symbol="AgentConfig")
# → LSPResult(references=[{"file": "...", "line": 123, "context": "..."}, ...])

# Type info
result = lsp_query("hover", file="src/punie/agent/config.py", line=42, col=10)
# → LSPResult(type_info="class AgentConfig(BaseModel)", docstring="...")

# Refactoring
result = lsp_query("rename_symbol", old="old_name", new="new_name")
# → LSPResult(edits=[{"file": "...", "range": {...}, "new_text": "new_name"}, ...])
```

### What's Needed for Implementation

1. **LSP client implementation**
   - Use pygls or direct ty connection via JSON-RPC/stdio
   - Handle request/response cycle
   - Map LSP protocol to Python API

2. **`LSPResult` Pydantic model + parser**
   - Define structured output for each LSP operation
   - Parser converts JSON-RPC responses to Python objects
   - Follows same pattern as `TypeCheckResult`

3. **`sync_lsp_query()` bridge in sandbox** (`toolset.py`)
   - Wrapper that calls LSP client
   - Handles errors gracefully
   - Returns typed result

4. **Stub in `stubs.py`**
   - Add to system prompt generation
   - Document when to use LSP vs text tools

5. **Training data: ~100 examples**
   - LSP-based navigation (goto definition, find references)
   - Type-aware coding (hover for type info)
   - Safe refactoring (rename symbol)
   - Contrast with text-based approaches

### Training Data Impact

LSP examples would be a **new category** of tool. Unlike ruff/pytest/typecheck which *validate* code, LSP *navigates and understands* code.

This teaches the model to **explore before acting** — the same pattern senior engineers use:

1. Use LSP to understand the codebase structure
2. Navigate to relevant symbols and references
3. Read type information and documentation
4. Make informed changes
5. Verify with validation tools (ty, ruff, pytest)

---

## Question 2: Holy Grail Part B — Still Big Impact? Infrastructure Ready?

### Impact: Highest of Anything on the Roadmap

The Part B research (`holy-grail-tools-domain.md` lines 269-695) makes the strategic case clearly:

> "The model stops thinking in 'code' and starts thinking in **domain concepts that happen to be implemented as code**."

**Key insight:**

- **LSP improves HOW the model navigates code** (tactical)
- **Domain tools change WHAT the model reasons about** (strategic)

A model with domain tools makes better **design decisions**, not just fewer syntax errors.

### Why Higher Impact Than LSP

| Dimension | LSP Impact | Domain Tools Impact |
|-----------|-----------|---------------------|
| **Code navigation** | ✅ Precise symbol lookup | ✅ Semantic understanding |
| **Refactoring** | ✅ Safe renames | ✅ Domain-aware refactoring |
| **Design decisions** | ❌ Still thinks in code syntax | ✅ Thinks in domain concepts |
| **Architectural guardrails** | ❌ No design constraints | ✅ Validates domain invariants |
| **Learning curve** | Modest (better tool use) | Transformative (domain reasoning) |

**Example — Add authentication to a tdom-svcs app:**

**Without domain tools:**
```python
# Model thinks: "I need to check login state, maybe add middleware?"
# → Writes code manually, may miss: service registration, middleware ordering, DI bindings
```

**With domain tools:**
```python
# Model thinks: "I need an auth service and middleware"
result = validate_service_registration({
    "factory": "create_auth_service",
    "lifecycle": "request",
    "protocol": "AuthProtocol"
})
# → Tool says: "✓ Valid registration" or "✗ Missing protocol method: check_permissions()"

result = validate_middleware_chain([
    {"name": "auth", "priority": 100},
    {"name": "logging", "priority": 50}
])
# → Tool says: "✓ Valid ordering" or "✗ Conflict: auth middleware requires session middleware first"
```

The domain tools act as **architectural guardrails** — constraining solutions BEFORE code is written.

### Concrete Domain Tools for Punie's World

Based on the four domain repos (tdom, svcs, svcs-di, tdom-svcs):

#### tdom Domain Tools

| Tool | What it validates | Example check |
|------|------------------|---------------|
| `validate_component(spec)` | Component structure, props, children, escaping | Props are type-safe, children are valid nodes |
| `check_render_tree(template)` | Node hierarchy, no dangling refs | All template references resolve to components |
| `validate_escape_context(node)` | XSS prevention | HTML escaping is correct for context (attr vs text) |

**Domain vocabulary:**
- Component, template, props, children, escaping context
- NOT: function, string, return, if/else

#### svcs + svcs-di Domain Tools

| Tool | What it validates | Example check |
|------|------------------|---------------|
| `validate_service_registration(reg)` | Factory type, lifecycle, protocol conformance | Factory returns correct type, lifecycle is valid |
| `check_dependency_graph(registry)` | No circular deps, layer violations | Services don't form dependency cycles |
| `validate_injection_site(location)` | Service is registered before injection | Can't inject unregistered service |

**Domain vocabulary:**
- Service, factory, lifecycle (request/session/app), protocol, registry, dependency graph
- NOT: class, function, decorator, attribute

#### tdom-svcs Domain Tools

| Tool | What it validates | Example check |
|------|------------------|---------------|
| `validate_middleware_chain(chain)` | Priority ordering, no conflicts | Auth before rate-limiting before logging |
| `check_di_template_binding(template)` | All injected services are registered | Template uses service X → X is registered |
| `validate_route_pattern(pattern)` | Route syntax, parameter types | `/users/{id:int}` is valid, `/users/{id:invalid}` is not |

**Domain vocabulary:**
- Middleware, priority, route, binding, service injection
- NOT: function, decorator, order, dictionary

### Readiness: Infrastructure is Sufficient

**Same pattern as LSP and existing typed tools:**

1. **Define domain Pydantic models** (ComponentSpec, ServiceRegistration, MiddlewareChain, etc.)
   - These are the "nouns" of the domain
   - Example: `ComponentSpec(name="Button", props={"label": str}, children=[...])`

2. **Implement deterministic validation functions**
   - Python code that checks domain invariants
   - Example: `validate_service_registration(spec) -> ValidationResult`
   - These functions don't execute user code — they validate structure/rules

3. **Add to sandbox as callable tools** (`toolset.py`)
   - `sync_validate_component()`, `sync_check_dependency_graph()`, etc.
   - Follow same pattern as `sync_typecheck()`

4. **Generate training data**
   - Show domain reasoning workflows
   - Example: "Add auth service" → validate registration → validate middleware → validate DI bindings → write code
   - ~150 examples covering all domain tool categories

5. **Train and evaluate**
   - Add domain examples to training set
   - Retrain model
   - Test: does model think in domain terms?

**Source material is rich and available:**

- **tdom:** Well-documented component patterns, escaping rules, template syntax
- **svcs:** Service locator pattern, lifecycle rules, protocol conformance
- **svcs-di:** Dependency injection rules, scanning, resolution
- **tdom-svcs:** Middleware ordering, route patterns, service integration

All four repos have comprehensive docs, examples, and tests to mine for validation rules.

### What's Needed for Implementation

1. **Define domain Pydantic models** (1-2 days)
   - ComponentSpec, ServiceRegistration, MiddlewareChain, RoutePattern, etc.
   - Model the domain nouns as Python dataclasses

2. **Implement validation functions** (3-5 days)
   - Write Python code that checks domain invariants
   - Make them deterministic (no side effects, no external calls)
   - Return structured ValidationResult

3. **Integrate into sandbox** (1 day)
   - Add sync wrappers in `toolset.py`
   - Add to `stubs.py` for system prompt

4. **Generate training data** (2-3 days)
   - Mine domain repos for patterns
   - Create examples showing domain reasoning workflows
   - Target: ~150 examples across all domains

5. **Train and evaluate** (1 day)
   - Retrain on expanded dataset
   - Test domain reasoning capabilities
   - Measure: does model use domain tools correctly?

**Total: ~2 weeks** for complete domain tools implementation.

---

## Training Data Strategy: Which is Needed More?

### Current Dataset Composition (857 examples after Phase 24)

- **Tool-calling examples:** ~128 (15%)
  - Show how to invoke tools correctly
  - Demonstrate tool sequencing
  - Cover error handling

- **Model/domain/direct-answer examples:** ~729 (85%)
  - Domain knowledge (what is tdom, svcs, etc.)
  - Direct answers (no tool calling)
  - Conceptual understanding

### What's Missing

1. **LSP tool calling** — zero examples (completely new tool category)
2. **Domain tool calling** — zero examples (domain tools don't exist yet)
3. **Deep domain knowledge** — Phase 26 (domain examples mining) adds ~158 examples, but these are Q&A about domain concepts, not domain *tool* calls

### The Highest-Value New Training Data

**Domain tool calling examples** — teaching the model to reason in domain terms using domain tools.

This combines the best of both:
- **New tool-calling patterns** (like LSP)
- **Domain knowledge** (what's already growing in the dataset)

**Example domain tool calling workflow:**

```
User: "Add authentication to this tdom-svcs app"

Model thinks:
1. This requires an auth service, middleware, and DI bindings
2. Let me validate the service registration first

result = validate_service_registration({
    "factory": "create_auth_service",
    "lifecycle": "request",
    "protocol": "AuthProtocol"
})
# → ValidationResult(valid=False, errors=["AuthProtocol missing check_permissions method"])

3. Fix the protocol definition
4. Validate middleware chain

result = validate_middleware_chain([
    {"name": "auth", "priority": 100},
    {"name": "logging", "priority": 50}
])
# → ValidationResult(valid=True)

5. Validate DI template bindings
6. Write the code
```

This is fundamentally different from "use LSP to find symbol definitions" — it's **domain-driven design** encoded as tool usage.

---

## Proposed Implementation Order: LSP First, Then Domain

### Why LSP First?

1. **Lower risk** — follows proven typed tool pattern
2. **Faster to implement** — ty LSP client + 100 examples
3. **Establishes semantic tool pattern** — teaches model to use structured queries instead of text grep
4. **Directly useful** — improves code navigation immediately
5. **Informs domain tools** — LSP is a reference implementation of "semantic tools"

### Why Domain Tools Second?

1. **Higher impact** — changes the model's reasoning from code to domain concepts
2. **Benefits from LSP experience** — having LSP as a reference makes domain tools easier
3. **Needs LSP for implementation** — domain tools will use LSP internally (e.g., "find all service registrations" uses `find_symbol`)
4. **More complex** — requires defining domain models, validation rules, and training workflows
5. **Strategic** — this is the "holy grail" vision, worth doing right after proving the semantic tool pattern

---

## Revised Roadmap: Phases 26-28

### Phase 26: LSP-Based Tool Architecture

**Status:** Planned (next after Phase 25)
**Goal:** Replace text-based code navigation with semantic LSP operations
**Training data:** ~100 examples (1015 → 1115 total)

**Key deliverables:**

1. **LSP client implementation**
   - Connect to ty LSP server via JSON-RPC/stdio
   - Implement goto_definition, find_references, hover, rename_symbol
   - Handle errors and edge cases

2. **`LSPResult` Pydantic model**
   - Structured output for each LSP operation
   - Parser converts JSON-RPC to Python objects

3. **Sandbox integration**
   - `sync_lsp_query()` in `toolset.py`
   - Add to `stubs.py` system prompt

4. **Training data generation**
   - 100 LSP examples showing navigation, type queries, refactoring
   - Contrast with text-based approaches
   - Multi-step workflows (LSP query → read → edit → verify)

5. **Benchmark**
   - LSP precision vs text-based tools
   - Test: symbol lookup, reference finding, safe refactoring

**Success criteria:**
- Model chooses LSP for symbol operations, text tools for content search
- Refactoring operations succeed (rename, organize imports)
- No false positives (text matches in comments/strings)
- Training data demonstrates clear LSP advantages

---

### Phase 27: Domain Typed Tools (Holy Grail Part B)

**Status:** Planned (after Phase 26)
**Goal:** Tools that think in domain vocabulary, not code syntax
**Training data:** ~150 examples (1115 → 1265 total)

**Key deliverables:**

1. **Define domain Pydantic models**
   - ComponentSpec, ServiceRegistration, MiddlewareChain, RoutePattern
   - Model domain nouns as Python dataclasses

2. **Implement domain validation tools**
   - `validate_component(spec) -> ValidationResult`
   - `check_dependency_graph(registry) -> ValidationResult`
   - `validate_middleware_chain(chain) -> ValidationResult`
   - `check_di_template_binding(template) -> ValidationResult`

3. **Sandbox integration**
   - Add domain tool wrappers to `toolset.py`
   - Add to `stubs.py` system prompt
   - Document domain vocabulary

4. **Training data generation**
   - Mine domain repos (tdom, svcs, svcs-di, tdom-svcs) for patterns
   - 150 examples showing domain reasoning workflows
   - Cover all domain tool categories
   - Show design decisions using domain tools

5. **Evaluation**
   - Test: does model think in domain terms?
   - Measure: domain tool usage vs code-first approaches
   - Validate: domain tools catch design errors before code is written

**Success criteria:**
- Model reasons in domain vocabulary (components, services, middleware) not code (classes, functions, decorators)
- Domain tools act as architectural guardrails
- Design errors caught before code is written
- Training data demonstrates domain-driven design workflows

**Critical insight:**

Domain tools encode **architectural invariants** that constrain solutions. This is fundamentally different from validation tools (ruff, ty, pytest) which check *existing* code. Domain tools guide *future* code.

---

### Phase 28: Full Retrain + Training Data Flywheel

**Status:** Planned (after Phase 27)
**Goal:** Retrain on complete dataset, establish automatic data collection
**Training data:** ~1265 examples total (857 current + 158 domain examples + 100 LSP + 150 domain tools)

**Key deliverables:**

1. **Full retrain**
   - Train on complete 1265-example dataset
   - All tool categories: text, validation, LSP, domain
   - Maintain 70/30 tool/direct ratio
   - Target: strong multi-tool workflows

2. **Automatic data collection infrastructure**
   - Capture real Punie usage as training data
   - Log: queries → tool calls → results → actions
   - Filter for quality, remove sensitive data
   - Store as reusable training examples

3. **Curation pipeline**
   - Automatic quality checks (successful tool usage, correct outcomes)
   - Manual review for edge cases
   - Deduplication and diversity balancing

4. **Retraining pipeline**
   - Scheduled retraining on growing dataset
   - Track perplexity and benchmark scores over time
   - A/B test new models before deployment

**Success criteria:**
- Training data grows automatically from real usage
- Retraining happens regularly (monthly?)
- Model improves continuously as dataset grows
- Flywheel is self-sustaining (no manual example writing)

**The vision:**

This is the "holy grail" endgame — **the model teaches itself** by using domain tools on real projects. Every successful workflow becomes training data. The model gets smarter with use.

---

## What "Domain Typed Tool" Means Concretely

### Pattern: Domain Concepts → Pydantic Models → Validation Tools

**Step 1: Identify domain nouns**

From domain docs/code, extract the core concepts:
- tdom: Component, Template, Props, Children, EscapeContext
- svcs: Service, Factory, Lifecycle, Protocol, Registry
- svcs-di: InjectionSite, Scanner, Resolver, PackagePattern
- tdom-svcs: Middleware, Route, Binding, Priority

**Step 2: Model as Pydantic dataclasses**

```python
from pydantic import BaseModel

class ComponentSpec(BaseModel):
    """A tdom component specification."""
    name: str
    props: dict[str, type]
    children: list[str]  # Allowed child types
    escaping: str  # "auto" | "manual" | "none"

class ServiceRegistration(BaseModel):
    """A service registration in svcs."""
    factory: str  # Factory function name
    lifecycle: str  # "request" | "session" | "app"
    protocol: str  # Protocol class name
    dependencies: list[str]  # Other services this depends on

class MiddlewareSpec(BaseModel):
    """A middleware in tdom-svcs."""
    name: str
    priority: int
    dependencies: list[str]  # Services required
    position: str  # "before" | "after" | "first" | "last"
```

**Step 3: Implement validation functions**

```python
def validate_component(spec: ComponentSpec) -> ValidationResult:
    """Check if component spec follows tdom rules."""
    errors = []

    # Rule 1: Props must be JSON-serializable types
    for prop_name, prop_type in spec.props.items():
        if prop_type not in [str, int, bool, float, list, dict]:
            errors.append(f"Prop {prop_name} has non-serializable type {prop_type}")

    # Rule 2: Children must be valid component names or text nodes
    for child in spec.children:
        if child not in KNOWN_COMPONENTS and child != "text":
            errors.append(f"Unknown child type {child}")

    # Rule 3: Manual escaping requires explicit escape calls
    if spec.escaping == "manual":
        # Check implementation for escape() calls (would use LSP here!)
        pass

    return ValidationResult(valid=len(errors) == 0, errors=errors)

def check_dependency_graph(registry: list[ServiceRegistration]) -> ValidationResult:
    """Check for circular dependencies and layer violations."""
    errors = []

    # Build dependency graph
    graph = {svc.factory: svc.dependencies for svc in registry}

    # Check for cycles
    for start_node in graph:
        if has_cycle(graph, start_node):
            errors.append(f"Circular dependency detected starting at {start_node}")

    # Check for layer violations (e.g., data layer depends on presentation layer)
    for svc in registry:
        if violates_layer_rules(svc):
            errors.append(f"Layer violation: {svc.factory} depends on {svc.dependencies}")

    return ValidationResult(valid=len(errors) == 0, errors=errors)
```

**Step 4: Integrate into sandbox**

```python
# In toolset.py
def sync_validate_component(spec_dict: dict) -> str:
    """Validate a tdom component specification."""
    spec = ComponentSpec(**spec_dict)
    result = validate_component(spec)
    return json.dumps(result.model_dump())

# In stubs.py
DOMAIN_TOOLS = """
Domain validation tools for tdom, svcs, svcs-di, tdom-svcs:

def validate_component(spec: dict) -> str:
    '''
    Validate a tdom component specification.
    Returns JSON with ValidationResult.

    Example:
        result = validate_component({
            "name": "Button",
            "props": {"label": "str"},
            "children": ["text"],
            "escaping": "auto"
        })
    '''

def check_dependency_graph(registry: list[dict]) -> str:
    '''
    Check service dependency graph for cycles and layer violations.
    Returns JSON with ValidationResult.
    '''
"""
```

**Step 5: Generate training data**

```python
# Example training trace
{
    "query": "Create a tdom Button component with a label prop",
    "code": '''
# First validate the component spec
result = validate_component({
    "name": "Button",
    "props": {"label": str, "onClick": callable},  # ❌ callable not JSON-serializable
    "children": ["text"],
    "escaping": "auto"
})
# Result: ValidationResult(valid=False, errors=["Prop onClick has non-serializable type callable"])

# Fix: use string callback names, not callable types
result = validate_component({
    "name": "Button",
    "props": {"label": str, "on_click": str},  # ✅ string is serializable
    "children": ["text"],
    "escaping": "auto"
})
# Result: ValidationResult(valid=True, errors=[])

# Now write the component code
def Button(label: str, on_click: str = "") -> Template:
    return t'<button onclick="{on_click}">{label}</button>'
''',
    "result": "Created Button component following tdom rules"
}
```

### Key Difference from Validation Tools

| Validation Tools (ty, ruff, pytest) | Domain Tools |
|-------------------------------------|--------------|
| Check *existing* code for errors | Guide *future* code design |
| Syntax/type/test correctness | Architectural invariants |
| Run after code is written | Run before code is written |
| Answer: "Is this code correct?" | Answer: "Is this design valid?" |
| Reactive (fix bugs) | Proactive (prevent design errors) |

**The strategic insight:**

Domain tools shift the model's reasoning from **"How do I write this code?"** to **"What design should I implement?"**

This is the difference between a junior developer (writes code that compiles) and a senior architect (designs systems that scale).

---

## Conclusion

### Summary of Readiness

| Phase | Readiness | Risk | Impact | Implementation Time |
|-------|-----------|------|--------|-------------------|
| Phase 26: LSP | ✅ Ready | Low | High (tactical) | 1-2 weeks |
| Phase 27: Domain Tools | ✅ Ready | Medium | Very High (strategic) | 2-3 weeks |
| Phase 28: Flywheel | 🔄 Depends on 26+27 | Low | High (long-term) | 1 week |

### Recommended Sequence

1. **Complete Phase 25** (7B experiment) — validate model size tradeoffs
2. **Phase 26 (LSP)** — establish semantic tool pattern, ~100 examples
3. **Phase 27 (Domain Tools)** — holy grail implementation, ~150 examples
4. **Phase 28 (Full Retrain + Flywheel)** — retrain on ~1265 examples, establish automatic collection

### Strategic Rationale

- **LSP first:** Proves the semantic tool pattern at low risk, directly useful for navigation/refactoring
- **Domain tools second:** Benefits from LSP experience, highest strategic impact, changes model reasoning from code to design
- **Flywheel last:** Requires both LSP and domain tools to be effective, establishes long-term self-improvement

### The End Vision

After Phase 28, Punie will:
- Navigate code semantically (LSP)
- Validate code correctness (ty, ruff, pytest)
- Reason in domain concepts (domain tools)
- Teach itself from real usage (flywheel)

This is the complete picture: **a model that thinks like a senior engineer** — navigates precisely, validates thoroughly, designs architecturally, and learns continuously.
