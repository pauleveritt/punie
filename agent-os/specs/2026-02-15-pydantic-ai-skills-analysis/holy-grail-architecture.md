# Holy Grail Architecture: Self-Improving Agent Skills with Monty

**Status:** Research & Design
**Date:** 2026-02-15
**Context:** Pydantic AI skills research + Punie's training data flywheel + tdom-svcs development acceleration

## Executive Summary

**Near-term goal:** Use Punie to write tdom-svcs components, middleware, and services faster with quality, while collecting tool-calling and model training data as we go.

**Core insight from Pydantic AI research:** The most powerful pattern is **progressive disclosure** + **dynamic tool composition** + **automatic observability**. Skills start simple (list → load → execute), then adapt based on usage patterns.

**The Monty Evolution:** Instead of fixed tools calling fixed APIs, the model writes domain-specific tool implementations on-demand, validated against schemas, and refined through training data feedback.

**Holy Grail:** A self-improving loop where:
1. Model generates domain-specific tool code (Monty)
2. Tool code executes in validated environment
3. Execution traces become training data
4. Model learns better tool generation patterns
5. Repeat → model gets better at writing tools for your domain

## What We Learned from Pydantic AI

### Key Patterns Worth Adopting

**1. Progressive Disclosure**
- Don't load all skill docs upfront → waste tokens
- Instead: `list_skills()` → `load_skill(name)` → `run_skill_script(name, script, args)`
- Apply to Punie: List available domain patterns → Load specific pattern docs → Generate implementation

**2. Dependency Injection via RunContext**
```python
@agent.tool
async def get_weather(ctx: RunContext[Deps], location: str) -> dict:
    # ctx.deps gives typed access to injected services
    return await ctx.deps.weather_api.fetch(location)
```
- Apply to Punie: `ctx.deps.svcs_registry`, `ctx.deps.project_structure`, `ctx.deps.tdom_schemas`

**3. Toolset Composition**
```python
# Combine, filter, prefix, approve
combined = CombinedToolset(core_tools, domain_tools)
filtered = FilteredToolset(combined, lambda t: user.can_use(t))
```
- Apply to Punie: Compose tdom-tools, svcs-tools, test-tools dynamically

**4. Automatic Observability**
```python
logfire.configure()
logfire.instrument_pydantic_ai()
# All tool calls, token usage, latencies tracked automatically
```
- Apply to Punie: Every tool call → training example + trace

**5. ModelRetry for Domain Validation**
```python
@agent.tool
def create_component(name: str) -> str:
    if not name.endswith('View'):
        raise ModelRetry('Component names must end with "View"')
    # ... generate component
```
- Apply to Punie: Validate generated code against domain rules, retry if invalid

### What Pydantic AI Does NOT Do (but we want)

1. **No code generation by default** — Tools are pre-defined Python functions
2. **No self-modification** — Tools can't rewrite themselves based on outcomes
3. **No training loop** — Observability data stays in telemetry systems, doesn't flow back to model
4. **No domain-specific code synthesis** — Model calls tools; doesn't write tool implementations

This is where **Monty** comes in.

## The Monty Idea: Model Writes Tool Code

### Evolution of Tool Architectures

**Level 0: Fixed Tools (Current Punie Phase 1-25)**
```
User: "Read test.py"
→ Model: call read_file(path="test.py")
→ Tool execution: executes read_file
→ Model: receives file contents
```

**Level 1: Code Mode (Punie Phase 22-24)**
```
User: "Read test.py and count lines"
→ Model:
    result = read_file("test.py")
    lines = result.split('\n')
    print(f"Line count: {len(lines)}")
→ Tool execution: executes Python code
→ Model: receives output
```

**Level 2: Monty — Domain-Specific Tool Generation**
```
User: "Create a UserProfileView component"
→ Model: Generates Python code using tdom/svcs patterns:
    @view
    def user_profile_view(user: User, *, request: Request) -> Element:
        return html(t"<div class='profile'>...</div>")
→ Validator: Checks against tdom/svcs schemas
→ Tool execution: Saves component to correct location
→ Model: Confirms + suggests next steps
```

**Level 3: Monty + Self-Improvement (Holy Grail)**
```
User: "Create a UserProfileView component"
→ Model: Generates code (Level 2)
→ Execution: Code runs, validates, passes tests
→ Training collector: Captures (prompt, generated_code, execution_result, validation_passed)
→ Fine-tuning: Improves model's ability to generate valid tdom-svcs code
→ Repeat: Model gets better at domain-specific generation
```

### Why Monty > Fixed Tools for Domain Work

**Fixed Tools:**
- ✅ Safe (pre-defined behavior)
- ✅ Fast (no generation latency)
- ❌ Limited (can't compose novel behaviors)
- ❌ Generic (not domain-aware)

**Monty (Code Generation):**
- ✅ Flexible (arbitrary compositions)
- ✅ Domain-aware (learns tdom/svcs patterns)
- ✅ Self-improving (training loop)
- ⚠️ Requires validation (must check generated code)
- ⚠️ Higher latency (generation + validation)

**The sweet spot:** Hybrid approach
- Fixed tools for high-risk operations (delete, deploy, git push)
- Monty for domain artifact generation (components, services, tests)

## Near-Term Goal: Accelerating tdom-svcs Development

### The Use Case

You want to write tdom-svcs applications faster:

**Artifacts to generate:**
1. **tdom Components/Views** — HTML generation with type-safe interpolation
2. **svcs Services** — Registered services with DI
3. **Middleware** — ASGI middleware with service access
4. **Tests** — Pytest tests with fixtures and Sybil doctests
5. **Integration glue** — Wiring components + services + routes

**Current workflow (slow):**
1. Manually write component boilerplate
2. Look up svcs registration patterns
3. Write middleware with correct signatures
4. Add tests with correct fixtures
5. Debug type errors
6. Repeat

**Desired workflow (fast + data collection):**
1. Describe component: "Create a user profile view with avatar, name, bio"
2. Punie generates code using learned tdom-svcs patterns
3. Code validates against schemas
4. Tests auto-generated
5. Execution traced → training data
6. Model improves over time

### Architecture Proposal: Punie + Monty for tdom-svcs

```
┌─────────────────────────────────────────────────────────────┐
│                    Punie Agent (Qwen3)                      │
│                                                             │
│  System Prompt: "You are Punie, expert in tdom-svcs..."   │
│  + Domain Skills: [tdom-patterns, svcs-patterns, ...]      │
└─────────────────┬───────────────────────────┬───────────────┘
                  │                           │
                  ↓ Tool Call                 ↓ Observability
         ┌─────────────────┐         ┌────────────────────┐
         │  Tool Execution │         │  Training Collector│
         │  Environment    │         │                    │
         └────────┬────────┘         └──────────┬─────────┘
                  │                              │
      ┌───────────┼──────────────┐              │
      ↓           ↓              ↓              │
┌──────────┐ ┌─────────┐  ┌──────────┐         │
│Fixed Tool│ │ Monty   │  │Validator │         │
│(read_file)│ │(execute_│  │(schemas) │         │
│          │ │ code)   │  │          │         │
└──────────┘ └─────────┘  └──────────┘         │
                  │             │               │
                  └──────┬──────┘               │
                         ↓                      ↓
                  ┌─────────────┐      ┌──────────────┐
                  │   File I/O  │      │ Training Data│
                  │   (write,   │      │  (JSONL)     │
                  │    read)    │      │              │
                  └─────────────┘      └──────┬───────┘
                                              │
                                              ↓
                                      ┌──────────────┐
                                      │ Fine-Tuning  │
                                      │  (mlx_lm)    │
                                      └──────────────┘
```

### Component: Domain Skills System

**Skill Structure (inspired by Pydantic AI + Claude Code)**

```
punie/skills/
├── tdom-components/
│   ├── SKILL.md                    # Progressive disclosure docs
│   ├── schemas/
│   │   ├── component_schema.py    # Pydantic models for validation
│   │   └── view_schema.py
│   ├── examples/
│   │   ├── basic_view.py          # Reference implementations
│   │   └── complex_view.py
│   └── templates/
│       └── component.py.jinja2    # Optional: scaffolding templates
├── svcs-services/
│   ├── SKILL.md
│   ├── schemas/
│   │   └── service_schema.py
│   └── examples/
│       └── registry_service.py
└── middleware/
    ├── SKILL.md
    └── examples/
        └── asgi_middleware.py
```

**SKILL.md Format:**

```yaml
---
name: tdom-components
version: "1.0"
description: "Generate tdom components/views with type-safe HTML"
requires:
  - tdom
  - svcs-di
patterns:
  - "@view decorator"
  - "html(t'...')"
  - "dependency injection via hopscotch"
---

# tdom Components Skill

## When to Use
Generate a tdom component when the user requests:
- "Create a {name} view/component"
- "Build a UI for {feature}"
- "Add a {element} to {page}"

## Component Patterns

### Basic View
```python
from tdom import html, t
from hopscotch import view

@view
def hello_view(name: str) -> Element:
    return html(t"<h1>Hello, {name}!</h1>")
```

### View with Services
```python
from svcs import Container
from hopscotch import view

@view
def user_view(user_id: int, *, svcs: Container) -> Element:
    user_service = svcs.get(UserService)
    user = user_service.get(user_id)
    return html(t"<div class='user'>{user.name}</div>")
```

## Validation Rules
1. Function name must end with `_view`
2. Must use `@view` decorator
3. Return type must be `Element`
4. Dependencies injected via keyword-only args
5. Must use `html(t"...")` for HTML generation

## Common Mistakes
- ❌ Returning strings instead of Element
- ❌ Using f-strings instead of t-strings
- ❌ Forgetting `@view` decorator
```

### Component: Monty Tool with Validation

**Implementation:**

```python
from dataclasses import dataclass
from pydantic import BaseModel, ValidationError
from punie.tools import Tool, ToolResult
from punie.validation import validate_generated_code

@dataclass
class MontyTool(Tool):
    """Execute domain-specific code generation with validation."""

    name = "generate_artifact"
    description = """Generate domain-specific code (components, services, middleware).

    Args:
        artifact_type: Type of artifact (component, service, middleware, test)
        name: Artifact name (e.g., 'UserProfileView')
        description: What the artifact should do
        code: Python implementation code

    Returns:
        Validation result + file path if saved
    """

    async def execute(
        self,
        ctx: RunContext,
        artifact_type: str,
        name: str,
        description: str,
        code: str,
    ) -> ToolResult:
        # Step 1: Load schema for artifact type
        schema = ctx.deps.schema_registry.get(artifact_type)

        # Step 2: Validate generated code
        try:
            validation = await validate_generated_code(
                code=code,
                schema=schema,
                artifact_type=artifact_type,
            )
        except ValidationError as e:
            # Model can retry with corrections
            raise ModelRetry(f"Code validation failed: {e}")

        # Step 3: Run static analysis (ruff, ty)
        if not validation.passes_type_check:
            raise ModelRetry(f"Type errors: {validation.type_errors}")

        # Step 4: Save to correct location
        file_path = ctx.deps.project_structure.get_path(
            artifact_type, name
        )
        await ctx.deps.file_writer.write(
            path=file_path,
            content=code,
        )

        # Step 5: Record for training
        ctx.deps.training_collector.record(
            prompt=description,
            artifact_type=artifact_type,
            generated_code=code,
            validation_result=validation,
            file_path=file_path,
        )

        return ToolResult(
            success=True,
            output=f"Created {artifact_type} at {file_path}",
            metadata={
                "file_path": file_path,
                "validation": validation.model_dump(),
            }
        )
```

### Component: Schema Validation

**Example: tdom Component Schema**

```python
from pydantic import BaseModel, Field, field_validator
import ast

class TdomComponentSchema(BaseModel):
    """Schema for validating generated tdom components."""

    code: str = Field(description="Python source code")
    name: str = Field(description="Function name")

    @field_validator("code")
    def validate_structure(cls, code: str) -> str:
        """Validate component structure."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Syntax error: {e}")

        # Find the view function
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]

        if not functions:
            raise ValueError("No function definition found")

        func = functions[0]

        # Check for @view decorator
        has_view_decorator = any(
            (isinstance(d, ast.Name) and d.id == "view")
            or (isinstance(d, ast.Attribute) and d.attr == "view")
            for d in func.decorator_list
        )

        if not has_view_decorator:
            raise ValueError("Missing @view decorator")

        # Check return annotation
        if func.returns is None:
            raise ValueError("Missing return type annotation")

        # Check for html(t"...") pattern in function body
        has_html_call = any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "html"
            for n in ast.walk(func)
        )

        if not has_html_call:
            raise ValueError("Must use html(t'...') for HTML generation")

        return code

    @field_validator("name")
    def validate_naming(cls, name: str) -> str:
        """Validate naming conventions."""
        if not name.endswith("_view"):
            raise ValueError("View function names must end with '_view'")
        return name
```

## Code Analysis: AST vs libcst (CST)

### The Layered Approach

When validating and modifying generated code, we need different tools for different purposes. Research shows that **combining ast and libcst in layers** gives the best results:

| Layer | Tool | Purpose | Why |
|-------|------|---------|-----|
| Fast gate | `ast.parse()` | Syntax validation | ~10x faster, built-in, no deps |
| Convention checking | `libcst.matchers` | Pattern matching (@view, return type, etc.) | More ergonomic than isinstance chains |
| Auto-fixing | `libcst` transformers | Fix validation errors | Preserves comments/formatting (lossless) |
| Code generation | `libcst` templates | Build code from scratch | `parse_template_statement()` is powerful |

**Key architectural insight:** Don't pick one — use both in layers. ast for the fast path, libcst when you need to understand or modify structure.

### What libcst Uniquely Enables for Monty

1. **Validate-then-fix**: Model generates code → ast validates syntax → libcst matchers check conventions → libcst transformers auto-fix issues (add missing imports, fix decorator, adjust return type) → code preserved perfectly

2. **Matchers API**: Replace verbose `ast.walk() + isinstance()` checks with declarative patterns:
   ```python
   # Instead of walking the AST manually
   for node in ast.walk(tree):
       if isinstance(node, ast.FunctionDef):
           for decorator in node.decorator_list:
               if isinstance(decorator, ast.Name) and decorator.id == "view":
                   # found it!

   # Use libcst matchers
   import libcst.matchers as m
   if m.matches(node, m.FunctionDef(decorators=[m.AtLeastN(
       n=1,
       matcher=m.Decorator(decorator=m.Name("view"))
   )])):
       # found it!
   ```

3. **Codemods for batch refactoring**: When a pattern changes across the project (e.g., `@view` → `@component`), libcst codemods can update all generated files while preserving formatting

4. **Template-based code generation**: Build code programmatically with full type safety:
   ```python
   from libcst import parse_template_statement

   func = parse_template_statement(
       "def {name}(*, {dep}: {dep_type}) -> Element: ...",
       name=cst.Name("user_view"),
       dep=cst.Name("user_service"),
       dep_type=cst.Name("UserService")
   )
   ```

### Concrete Example: Layered Validation in TdomComponentSchema

```python
import ast
import libcst as cst
import libcst.matchers as m

class TdomComponentValidator:
    """Layered validation: ast fast gate → libcst deep analysis."""

    def validate(self, code: str) -> ValidationResult:
        # Layer 1: Fast syntax check (ast)
        try:
            ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(valid=False, error=f"Syntax: {e}")

        # Layer 2: Convention check (libcst matchers)
        tree = cst.parse_module(code)
        functions = m.findall(tree, m.FunctionDef())

        if not functions:
            return ValidationResult(valid=False, error="No function found")

        func = functions[0]

        # Check for @view decorator using matchers
        has_view = m.matches(
            func,
            m.FunctionDef(decorators=[m.AtLeastN(
                n=1,
                matcher=m.Decorator(decorator=m.Name("view"))
            )])
        )

        if not has_view:
            return ValidationResult(
                valid=False,
                error="Missing @view decorator",
                fixable=True,  # libcst can add it
            )

        # Layer 3: Auto-fix if needed (libcst transformer)
        if not has_view:
            transformer = AddViewDecoratorTransformer()
            tree = tree.visit(transformer)
            return ValidationResult(valid=True, fixed_code=tree.code)

        return ValidationResult(valid=True)


class AddViewDecoratorTransformer(cst.CSTTransformer):
    """Add @view decorator to functions missing it."""

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        # Check if already has @view
        has_view = any(
            m.matches(d, m.Decorator(decorator=m.Name("view")))
            for d in updated_node.decorators
        )

        if not has_view:
            # Add @view decorator
            view_decorator = cst.Decorator(decorator=cst.Name("view"))
            return updated_node.with_changes(
                decorators=[view_decorator] + list(updated_node.decorators)
            )

        return updated_node
```

### Updating Existing Validation

The current `TdomComponentSchema.validate_structure()` uses pure ast. Here's how to enhance it with the layered approach:

**Before (ast only):**
```python
# Check for @view decorator
has_view_decorator = any(
    (isinstance(d, ast.Name) and d.id == "view")
    or (isinstance(d, ast.Attribute) and d.attr == "view")
    for d in func.decorator_list
)
if not has_view_decorator:
    raise ValueError("Missing @view decorator")
```

**After (layered approach):**
```python
# Layer 1: ast for fast syntax check (keep as-is)
try:
    tree = ast.parse(code)
except SyntaxError as e:
    raise ValueError(f"Syntax error: {e}")

# Layer 2: libcst matchers for convention checking
cst_tree = cst.parse_module(code)
functions = m.findall(cst_tree, m.FunctionDef())

if not functions:
    raise ValueError("No function definition found")

func = functions[0]

# More ergonomic decorator check
if not m.matches(func, m.FunctionDef(decorators=[m.AtLeastN(
    n=1, matcher=m.Decorator(decorator=m.Name("view"))
)])):
    # Layer 3: Offer to auto-fix
    raise ValueError("Missing @view decorator - run with auto_fix=True to add it")
```

### Honest Assessment

**When ast is better:**
- ✅ Pure syntax validation (fast, built-in, sufficient)
- ✅ Simple pattern checking (single decorator, return type)
- ✅ When you don't need to modify code
- ✅ When dependencies matter (ast is stdlib, libcst adds a dep)

**When libcst shines:**
- ✅ **Validation → modification workflow** (the validate-then-fix pattern)
- ✅ **Complex pattern matching** (matchers API is genuinely better than isinstance chains)
- ✅ **Code generation from templates** (type-safe construction)
- ✅ **Batch refactoring** (codemods that preserve style)
- ✅ **When formatting matters** (lossless roundtrip through CST)

**The trade-off:**
- libcst adds a non-trivial dependency (requires Rust compilation for native parser)
- For pure validation, ast is faster and simpler
- libcst's value appears when validation leads to modification

**Recommendation for Monty:**
1. **Start with ast-only validation in Milestone 2** — Fast, simple, no new dependencies
2. **Add libcst in Milestone 3** when auto-fixing patterns emerge from real usage
3. **Use libcst for:**
   - Auto-fixing common validation errors
   - Template-based code generation in MontyTool
   - Future codemods when patterns evolve
4. **Keep ast for:**
   - Fast syntax checking (Layer 1)
   - Simple boolean checks (has decorator? has return type?)

### Integration with MontyTool

Update the `MontyTool.execute()` validation flow to use layered approach:

```python
# Step 2: Validate generated code (layered)
try:
    # Layer 1: Fast syntax check (ast)
    validation = await validate_syntax(code)  # uses ast.parse()

    # Layer 2: Convention check (libcst matchers)
    conventions = await validate_conventions(code, schema)  # uses libcst.matchers

    # Layer 3: Auto-fix if needed (libcst transformers)
    if not conventions.passed and conventions.fixable:
        code = await auto_fix_code(code, conventions.errors)  # uses libcst transformers
        # Re-validate after fixing
        conventions = await validate_conventions(code, schema)

except ValidationError as e:
    raise ModelRetry(f"Code validation failed: {e}")
```

### Milestone 2 Deliverables Update

Update the Milestone 2 acceptance criteria:

**Original:**
- Valid code passes type checking (ty)

**Enhanced:**
- Schema registry with layered validation (ast + libcst matchers)
- Optional auto-fix for common errors (libcst transformers)
- 90%+ validation pass rate with auto-fix enabled

### Component: Training Data Collector

**Automatic capture during execution:**

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json

@dataclass
class TrainingCollector:
    """Collect training examples from Monty executions."""

    output_dir: Path

    def record(
        self,
        prompt: str,
        artifact_type: str,
        generated_code: str,
        validation_result: ValidationResult,
        file_path: Path,
    ) -> None:
        """Record a training example."""
        example = {
            "timestamp": datetime.now().isoformat(),
            "artifact_type": artifact_type,
            "user_request": prompt,
            "generated_code": generated_code,
            "validation_passed": validation_result.is_valid,
            "type_check_passed": validation_result.passes_type_check,
            "file_path": str(file_path),
            "metadata": {
                "validation_errors": validation_result.errors,
                "retries": validation_result.retry_count,
            }
        }

        # Append to JSONL
        output_file = self.output_dir / f"monty-traces-{datetime.now():%Y-%m-%d}.jsonl"
        with output_file.open("a") as f:
            f.write(json.dumps(example) + "\n")

    def to_training_data(self, examples: list[dict]) -> list[TrainingExample]:
        """Convert collected traces to training examples."""
        training_examples = []

        for ex in examples:
            if not ex["validation_passed"]:
                continue  # Skip failed generations for now

            # Format as tool-calling conversation
            conversation = ChatMLConversation(
                messages=(
                    ChatMessage(role="system", content=SYSTEM_PROMPT),
                    ChatMessage(role="user", content=ex["user_request"]),
                    ChatMessage(
                        role="assistant",
                        content=f"I'll generate the {ex['artifact_type']}:\n\n{ex['generated_code']}"
                    ),
                    ChatMessage(
                        role="user",
                        content=f"Validation passed. File saved to {ex['file_path']}"
                    ),
                    ChatMessage(
                        role="assistant",
                        content=f"Successfully created {ex['artifact_type']}."
                    ),
                )
            )

            training_examples.append(
                TrainingExample(messages=conversation.messages)
            )

        return training_examples
```

## The Self-Improvement Loop

### Phase 1: Bootstrap (Manual Examples)

```
1. Manually create 20-50 reference tdom-svcs implementations
2. Annotate with descriptions: "User profile view with avatar"
3. Fine-tune Qwen3 on these examples
4. Deploy as Punie Phase 26
```

### Phase 2: Assisted Generation (Model + Validation)

```
1. User: "Create a UserProfileView"
2. Model generates code using Phase 26 weights
3. Validation catches errors → ModelRetry
4. Model corrects → passes validation
5. Code saved to project
6. Example recorded to training collector
```

### Phase 3: Continuous Improvement (Flywheel Spins)

```
1. Collect 100-200 validated generations
2. Filter: keep only validation_passed=True examples
3. Augment: add negative examples (common errors + fixes)
4. Fine-tune Qwen3 → Phase 27 weights
5. Deploy Phase 27
6. Model now better at tdom-svcs patterns
7. Repeat → Phase 28, 29, ...
```

### Metrics to Track

**Quality Metrics:**
- Validation pass rate (target: >90%)
- Type check pass rate (target: >95%)
- Test pass rate (target: >85%)
- Retry count per generation (target: <2)

**Velocity Metrics:**
- Components generated per hour
- Lines of code per hour
- Time saved vs manual coding

**Model Improvement:**
- Validation pass rate trend (should increase)
- Retry count trend (should decrease)
- Token efficiency (should improve)

## Implementation Roadmap

### Milestone 1: Domain Skills Framework (1 week)

**Deliverables:**
- `punie/skills/` directory structure
- Skill loader (list, load, execute pattern)
- SKILL.md parser with YAML frontmatter
- Initial skills: tdom-components, svcs-services

**Acceptance:**
- Punie can list available skills
- Punie can load skill docs on-demand
- Token usage reduced vs loading all docs upfront

### Milestone 2: Monty Tool + Validation (1 week)

**Deliverables:**
- `generate_artifact` tool implementation
- Schema registry (tdom, svcs, middleware)
- Pydantic validators for each artifact type
- ModelRetry integration for validation errors

**Acceptance:**
- Model can generate tdom components
- Invalid code rejected with clear errors
- Model can retry with corrections
- Valid code passes type checking (ty)

### Milestone 3: Training Data Collector (3 days)

**Deliverables:**
- TrainingCollector class
- Automatic trace recording on generation
- JSONL output format
- Conversion to ChatML training examples

**Acceptance:**
- Every generation captured to JSONL
- Traces include prompt, code, validation, outcome
- Can convert traces to mlx_lm training format

### Milestone 4: Bootstrap Dataset (1 week)

**Deliverables:**
- 30 reference tdom components
- 20 reference svcs services
- 15 reference middleware implementations
- Annotations + descriptions
- Fine-tuned Phase 26 weights

**Acceptance:**
- Model can generate basic tdom components
- Validation pass rate >70%
- Can handle common patterns (list view, form, detail page)

### Milestone 5: Self-Improvement Loop (ongoing)

**Deliverables:**
- Automated data collection during daily work
- Weekly fine-tuning jobs (phases 27, 28, ...)
- Metrics dashboard (validation rates, retry counts)
- A/B testing: Phase N vs Phase N+1

**Acceptance:**
- Validation pass rate increases over time
- Model learns from corrections
- Development velocity improves

## Near-Term Action Plan (This Week)

### Day 1-2: Skill System Foundation

```
Tasks:
1. Create punie/skills/ directory structure
2. Write tdom-components/SKILL.md with patterns + examples
3. Implement skill loader (list_skills, load_skill)
4. Add skill tools to Punie agent
5. Test: "List available skills" → "Load tdom-components skill"
```

### Day 3-4: Monty Tool + Basic Validation

```
Tasks:
1. Implement generate_artifact tool
2. Create TdomComponentSchema with basic validation
3. Integrate with file writer (write_file)
4. Test: "Create a HelloView component" → generates valid code
5. Validate: Code has @view, returns Element, uses html(t"...")
```

### Day 5: Training Collector + First Examples

```
Tasks:
1. Implement TrainingCollector
2. Record first 5 manual generations
3. Convert to ChatML format
4. Inspect JSONL output
5. Plan Phase 26 bootstrap dataset
```

### Weekend: Build Reference Dataset

```
Tasks:
1. Manually write 10 tdom components (varied complexity)
2. Write 5 svcs services
3. Annotate with descriptions
4. Generate training data
5. Ready for Phase 26 fine-tuning
```

## Comparison: Punie vs Pydantic AI

| Feature | Pydantic AI | Punie (Proposed) |
|---------|-------------|------------------|
| **Tool Definition** | Python decorators | Skills + Monty |
| **Composition** | Toolsets | Skill collections |
| **Code Gen** | No (external only) | Yes (Monty core) |
| **Validation** | Pydantic + ModelRetry | Pydantic + AST + ty |
| **Observability** | OpenTelemetry | Training collector |
| **Training Loop** | No | Yes (flywheel) |
| **Domain-Specific** | Generic tools | tdom-svcs specialized |
| **Self-Improvement** | No | Yes (continuous) |

## Risks & Mitigations

### Risk 1: Generated Code Quality

**Risk:** Model generates syntactically valid but semantically wrong code.

**Mitigation:**
- Multi-layer validation (syntax → types → tests)
- Reference examples in skill docs
- ModelRetry for common mistakes
- Manual review for first 50 examples

### Risk 2: Training Data Quality

**Risk:** Bad examples pollute training data.

**Mitigation:**
- Only collect validation_passed=True examples
- Manual curation of first 100 examples
- Negative examples for common errors
- A/B test each phase before deploying

### Risk 3: Overfitting to Your Codebase

**Risk:** Model learns your specific patterns, doesn't generalize.

**Mitigation:**
- Include diverse examples (simple + complex)
- Augment with synthetic variations
- Test on held-out patterns
- Periodically add external tdom-svcs examples

### Risk 4: Validation is Too Strict

**Risk:** Over-constrained schemas reject valid creative solutions.

**Mitigation:**
- Start with loose validation, tighten over time
- Allow schema overrides for experimental code
- Track false-negative rate
- Iterate on schemas based on rejections

## Future Extensions

### Extension 1: Multi-File Generation

Generate entire features (component + service + test + route):

```python
@agent.tool
async def generate_feature(
    ctx: RunContext,
    feature_name: str,
    description: str,
) -> ToolResult:
    # Generate component
    component = await generate_artifact(ctx, "component", f"{feature_name}View", ...)

    # Generate service
    service = await generate_artifact(ctx, "service", f"{feature_name}Service", ...)

    # Generate tests
    tests = await generate_artifact(ctx, "test", f"test_{feature_name}", ...)

    # Wire together
    # ...
```

### Extension 2: Code Review Tool

Model reviews generated code before saving:

```python
@agent.tool
async def review_code(ctx: RunContext, code: str) -> ReviewResult:
    """Self-review generated code for quality."""
    # Prompt model to critique its own generation
    # Check for: edge cases, error handling, type safety, style
    # Return suggestions for improvement
```

### Extension 3: Iterative Refinement

Model generates → tests fail → model fixes → tests pass:

```python
@agent.tool
async def refine_until_tests_pass(
    ctx: RunContext,
    code: str,
    test_command: str,
    max_iterations: int = 3,
) -> str:
    for i in range(max_iterations):
        result = await run_tests(ctx, test_command)
        if result.passed:
            return code
        # Prompt model with test failures
        code = await fix_code(ctx, code, result.errors)
    raise ModelRetry("Could not fix tests after {max_iterations} attempts")
```

### Extension 4: Style Transfer

Learn from existing codebase style:

```python
@agent.tool
async def generate_in_style_of(
    ctx: RunContext,
    artifact_type: str,
    reference_file: Path,
    description: str,
) -> str:
    """Generate new artifact matching style of reference file."""
    # Read reference file
    # Extract style patterns (naming, structure, comments)
    # Generate new artifact with same style
```

### Extension 5: Cross-Project Learning

Share training data across projects:

```
punie-collective/
├── tdom-svcs-examples/    # Your data
├── flask-examples/         # Community data
├── fastapi-examples/       # Community data
└── django-examples/        # Community data

# Fine-tune on collective data → generalize better
```

## Conclusion

**The holy grail is not a single feature — it's a flywheel:**

1. **Domain Skills** give model structured knowledge (tdom, svcs patterns)
2. **Monty Tool** lets model generate domain-specific code
3. **Validation** ensures quality (schemas + types + tests)
4. **Training Collector** captures successful generations
5. **Fine-tuning** improves model on your domain
6. **Repeat** → model gets better, you move faster

**Near-term focus:**
- Week 1: Skills + Monty + validation
- Week 2: Bootstrap dataset (30-50 examples)
- Week 3: Phase 26 fine-tuning
- Week 4: Daily usage → data collection → Phase 27

**Long-term vision:**
- Phases 26-30: Continuous improvement on tdom-svcs
- Phases 31+: Extend to other domains (APIs, CLIs, data pipelines)
- Phase 50: Model is expert in your entire stack

**Start small, iterate fast, let the flywheel spin.**

---

## Next Steps

1. **This week:** Implement Milestone 1 (skills framework)
2. **Review point:** After 5 successful generations, assess quality
3. **Decision point:** If validation pass rate >70%, proceed to bootstrap dataset
4. **Commit:** Once bootstrap complete, run Phase 26 fine-tuning

**Question for you:** Should we start with tdom-components only, or also add svcs-services in Milestone 1?
