Me: "I am building an AI coding agent using Pydantic AI. I am exploring new ideas about how to integrate deterministic
tools such as type checkers into the agentic loop as tools, and how to train models that know how to work with these
tools and structures. Is there any research on this topic? Any prototypes? Specific to Python."

# Research & Prototypes: Integrating Deterministic Tools into AI Coding Agent Loops

This is an active and genuinely exciting area. Let me break down what exists across research, prototypes, and emerging
practice—specifically in the Python ecosystem.

---

## 1. Academic & Industry Research

### **LATS (Language Agent Tree Search)**

- Combines LLM reasoning with external feedback signals (including program execution, test results, and static analysis)
  as part of a tree search over action trajectories.
- Paper: *"Language Agent Tree Search Unifies Reasoning Acting and Planning in Language Models"* (Zhou et al., 2023)
- Key idea: **deterministic tool outputs (tests, type checkers) serve as value functions** that guide the search, rather
  than relying solely on the model's own confidence.

### **Reflexion**

- (Shinn et al., 2023) — An agent architecture where external feedback (e.g., test execution results, linting, type
  errors) is **fed back into the LLM as "reflections"** that persist in an episodic memory buffer.
- Directly relevant: the feedback loop is *tool-driven and deterministic*.

### **CodeRL / CodeT**

- **CodeRL** (Le et al., 2022): Trains a critic model on compiler/test feedback, then uses RL to improve code
  generation.
- **CodeT** (Chen et al., 2023): Uses dual execution and testing to filter and rank generated code.
- Both formalize the idea that **deterministic program analysis is a reward signal**.

### **LLM + Static Analysis / Type Checking Specifically**

- **"Guiding Language Models of Code with Global Context using Monitors"** (Agrawal et al., 2023): Uses static analysis
  monitors (including type information and scope analysis) to constrain LLM decoding in real time. This is the closest
  to "type checker in the loop."
- **"Learning Type Inference for Enhanced Dataflow Analysis"** (CodaMosa, others): Explores ML models that consume and
  produce type information.
- **"Types as Abstract Interpretations"** (classic, Cousot): Theoretical foundation for why types are uniquely
  well-suited as tool feedback—they are decidable, compositional abstractions.

### **RLEF (Reinforcement Learning from Execution Feedback)**

- Several groups (including Meta's CodeCompose, Google DeepMind's AlphaCode 2) use **execution-based signals as reward**
  during training or reranking. This generalizes to any deterministic tool.

---

## 2. Existing Prototypes & Open-Source Projects (Python-specific)

### **PydanticAI itself**

You're already in the right neighborhood. PydanticAI's tool abstraction is well-suited because:

- Tools are typed with Pydantic models → the agent framework itself enforces schemas.
- You can wrap `mypy`, `pyright`, `ruff`, `pytest`, etc. as tools with structured output.

A concrete pattern:

```python
from pydantic_ai import Agent, Tool
from pydantic import BaseModel
import subprocess


class TypeCheckResult(BaseModel):
    success: bool
    errors: list[str]
    num_errors: int


class LintResult(BaseModel):
    issues: list[str]
    fixable: int


agent = Agent(
    'anthropic:claude-sonnet-4',
    system_prompt="""You are a Python coding agent. After writing or modifying code,
    you MUST use the typecheck tool and the lint tool before considering your work done.
    Fix all type errors before proceeding. Treat tool outputs as ground truth—never
    argue with the type checker.""",
)


@agent.tool
async def typecheck(ctx, code: str) -> TypeCheckResult:
    """Run pyright on the given Python code and return structured type errors."""
    # Write to temp file, run pyright --outputjson, parse results
    proc = subprocess.run(
        ["pyright", "--outputjson", tmpfile],
        capture_output=True, text=True
    )
    diagnostics = parse_pyright_json(proc.stdout)
    return TypeCheckResult(
        success=len(diagnostics) == 0,
        errors=[d.message for d in diagnostics],
        num_errors=len(diagnostics),
    )


@agent.tool
async def lint(ctx, code: str) -> LintResult:
    """Run ruff on the given Python code."""
    proc = subprocess.run(
        ["ruff", "check", "--output-format=json", tmpfile],
        capture_output=True, text=True
    )
    issues = parse_ruff_json(proc.stdout)
    return LintResult(
        issues=[i.message for i in issues],
        fixable=sum(1 for i in issues if i.fixable),
    )
```

### **Aider**

- [aider.chat](https://aider.chat) — Paul Gauthier's open-source AI pair programmer.
- Aider runs linters and tests in its loop, feeds errors back to the LLM, and iterates. It specifically integrates with
  `flake8`, `pytest`, and universal `lint` commands.
- Architecture is close to what you're describing: **deterministic tools as first-class loop participants**.

### **SWE-agent / SWE-bench**

- [SWE-agent](https://github.com/princeton-nlp/SWE-agent) (Princeton): Agent that interacts with real repos via a shell
  interface. It can (and does) invoke `pytest`, linters, type checkers as actions.
- SWE-bench is the benchmark. Top performers all use deterministic tool feedback in the loop.

### **Mentat (AbandonedAI)**

- Another open-source coding agent that integrates with the local development environment and runs checks as part of its
  edit loop.

### **OpenHands (formerly OpenDevin)**

- [github.com/All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands)
- Sandboxed agent that can run arbitrary tools. People have configured it with type checking and test execution in the
  loop.

---

## 3. The Key Design Insight You're Circling

There's a **spectrum of how tightly you integrate deterministic tools**:

```
Loose                                                    Tight
  |                                                        |
  Post-hoc          Tool-in-loop        Constrained        Training
  validation        (your current       decoding           signal
  (check after)     exploration)        (guide tokens)     (reward model)
```

| Level                    | Description                                                         | Example                                                 |
|--------------------------|---------------------------------------------------------------------|---------------------------------------------------------|
| **Post-hoc**             | Generate, then check, reject/retry                                  | Basic CI integration                                    |
| **Tool-in-loop**         | Agent calls type checker as a tool, reasons about output, retries   | What you're building with PydanticAI                    |
| **Constrained decoding** | Type information narrows the token distribution *during generation* | Monitors (Agrawal et al.), grammar-constrained sampling |
| **Training signal**      | Type checker correctness is a reward in RLHF/RLEF                   | CodeRL-style approaches                                 |

The most interesting and underexplored zone is **between tool-in-loop and constrained decoding**—where the agent has
learned (through training or prompting) *when and how* to invoke the type checker, and can predict/avoid type errors
proactively.

---

## 4. Training Models That "Know" These Tools

This is the frontier question. A few threads:

### **Tool-augmented fine-tuning**

- Fine-tune on traces where the model invokes `mypy`/`pyright`, observes output, and corrects code. This teaches the
  model the *calling convention and interpretation* of tool output.
- **Gorilla** (Patil et al., 2023) and **ToolLLM** (Qin et al., 2023) show that models fine-tuned on tool-use traces
  dramatically outperform prompted ones.

### **Process Reward Models (PRMs) informed by tools**

- Instead of training a monolithic reward model, use **type checker success as a step-level reward** in a process reward
  model.
- Paper: *"Let's Verify Step by Step"* (Lightman et al., 2023) — applied to math, but the architecture transfers to
  code + type checking.

### **Synthetic data generation for type-aware coding**

- Generate (code, type_error, fix) triples using `pyright` programmatically, then train on them.
- This is straightforward to do at scale and is likely what frontier labs are already doing.

### **A practical prototype for training-aware integration:**

```python
# Generating training data: type-error correction pairs
import subprocess, json, tempfile
from pathlib import Path


def generate_type_error_training_pair(
        buggy_code: str,
        fixed_code: str
) -> dict:
    """Create a training example with real pyright output."""

    with tempfile.NamedTemporaryFile(suffix='.py', mode='w', delete=False) as f:
        f.write(buggy_code)
        buggy_path = f.name

    result = subprocess.run(
        ["pyright", "--outputjson", buggy_path],
        capture_output=True, text=True
    )
    diagnostics = json.loads(result.stdout)

    # Format as a tool-use conversation for fine-tuning
    return {
        "messages": [
            {"role": "user", "content": f"Fix this code:\n```python\n{buggy_code}\n```"},
            {"role": "assistant", "content": None, "tool_calls": [{
                "function": {"name": "typecheck", "arguments": json.dumps({"code": buggy_code})}
            }]},
            {"role": "tool", "content": json.dumps({
                "success": False,
                "errors": [d["message"] for d in diagnostics["generalDiagnostics"]],
            })},
            {"role": "assistant",
             "content": f"The type checker found errors. Here's the fix:\n```python\n{fixed_code}\n```"},
        ]
    }
```

---

## 5. What's Missing / Open Problems

1. **Incremental type checking in the loop**: Running `pyright` on every iteration is slow. There's no good Python
   library for *incremental* type checking as a service (pyright's `--watch` mode is close but not API-friendly).
   Building a persistent pyright LSP connection as a PydanticAI tool dependency would be novel and valuable.

2. **Semantic type information as context**: Rather than just pass/fail, feeding the agent the *inferred types* of
   expressions (hover information from pyright) so it can reason about them. No one does this well yet.

3. **Multi-tool orchestration**: Combining type checker + test runner + coverage + linter into a coherent **tool
   selection policy** the agent learns. This is where PydanticAI's structured tool framework could shine.

4. **Formal verification of AI-generated code**: Using tools like `beartype`, `typeguard`, or `deal` (contracts) as
   runtime verification in the agent loop—going beyond static types.

---

## 6. Recommended Reading List

| Paper/Resource                                                                   | Why It Matters                                                 |
|----------------------------------------------------------------------------------|----------------------------------------------------------------|
| Agrawal et al. 2023, "Monitors"                                                  | Closest to type-checker-in-the-loop for LLM code generation    |
| Shinn et al. 2023, "Reflexion"                                                   | Architecture for tool feedback → episodic memory → improvement |
| Zhou et al. 2023, "LATS"                                                         | Using tool signals as value functions in search                |
| Qin et al. 2023, "ToolLLM"                                                       | Training models to use tools effectively                       |
| Lightman et al. 2023, "Let's Verify Step by Step"                                | Process reward models (applicable to step-level type checking) |
| Olausson et al. 2023, "Self-Repair"                                              | LLMs using execution feedback to fix their own code            |
| PydanticAI docs on [dependency injection](https://ai.pydantic.dev/dependencies/) | For wiring persistent tool services (LSP connections, etc.)    |

The short answer: **you're on a path that research supports but few have built end-to-end for Python with modern agent
frameworks.** The combination of PydanticAI's structured tool system + pyright/mypy as loop participants + training on
tool-use traces is genuinely frontier work.

Me: "This writeup thinks of tools with the traditional concept of Python tooling: linter, formatter, type checker, etc.
Are there other concepts of "tool" that might be more domain-specific, using the vocabulary of the domain? For example,
in component driven development, you have: components, props, a state store, actions, side effects, etc."

# Domain-Specific Tools: Thinking Beyond Developer Tooling

You're pointing at something important. The traditional tools (linter, type checker, test runner) operate at the
*language* level. They verify that code is valid Python. But they say nothing about whether the code is valid *in your
domain*. The interesting frontier is tools that operate at the *domain concept* level.

## The Shift in Perspective

```
Language-level tools:          Domain-level tools:
"Is this valid Python?"        "Is this valid in our domain?"

  typecheck("code")              validate_component("component")
  lint("code")                   check_state_transitions("store")
  test("code")                   verify_data_pipeline("pipeline")

The model learns:              The model learns:
  Python's type system           Your domain's rules
  PEP 8 conventions              Your architecture's constraints
  Testing patterns               Your business logic invariants
```

## Example: Component-Driven Development

Let's make this concrete. In a component-driven frontend architecture (React, but the concepts generalize), the domain
has specific vocabulary and rules that are *not captured by a type checker*:

```python
from pydantic_ai import Agent
from pydantic import BaseModel


# --- Domain vocabulary as Pydantic models ---

class Prop(BaseModel):
    name: str
    type: str
    required: bool
    description: str
    default: str | None = None


class ComponentSpec(BaseModel):
    name: str
    props: list[Prop]
    children: bool
    pure: bool  # no side effects in render
    state_dependencies: list[str]  # which store slices it reads
    actions_dispatched: list[str]  # which actions it can trigger


class StateSlice(BaseModel):
    name: str
    shape: dict  # the type structure
    initial_value: dict
    owned_by: str  # which module "owns" this state


class Action(BaseModel):
    name: str
    payload_schema: dict
    reducers: list[str]  # which state slices it affects
    side_effects: list[str]  # what external effects it triggers


class SideEffect(BaseModel):
    name: str
    trigger: str  # action that triggers it
    dependencies: list[str]  # external services it calls
    success_action: str  # action dispatched on success
    failure_action: str  # action dispatched on failure


class DomainArchitecture(BaseModel):
    components: list[ComponentSpec]
    state_slices: list[StateSlice]
    actions: list[Action]
    side_effects: list[SideEffect]
```

Now the tools speak this vocabulary:

```python
agent = Agent(
    "anthropic:claude-sonnet-4",
    system_prompt="""You are building a component-driven frontend application.
    You must validate all architectural decisions using the domain tools.
    Think in terms of components, props, state, actions, and side effects —
    not just code.""",
)


@agent.tool
async def validate_component(ctx, spec: ComponentSpec) -> ComponentValidation:
    """
    Validate a component spec against architectural rules.

    Checks:
    - Pure components don't dispatch actions
    - All state dependencies reference existing state slices
    - Props follow naming conventions
    - No circular component dependencies
    - Required props have no default values
    """
    errors = []

    if spec.pure and spec.actions_dispatched:
        errors.append(
            f"Component '{spec.name}' is marked pure but dispatches "
            f"actions: {spec.actions_dispatched}. Pure components "
            f"should only render based on props and state."
        )

    known_slices = await ctx.deps.get_state_slice_names()
    for dep in spec.state_dependencies:
        if dep not in known_slices:
            errors.append(
                f"Component '{spec.name}' depends on state slice "
                f"'{dep}' which doesn't exist. Known slices: {known_slices}"
            )

    return ComponentValidation(valid=len(errors) == 0, errors=errors)


@agent.tool
async def check_state_transitions(
        ctx, action: Action
) -> StateTransitionValidation:
    """
    Validate that an action's state transitions are safe.

    Checks:
    - All referenced reducers correspond to real state slices
    - The action's payload schema is compatible with reducer expectations
    - No two actions can put the same state slice into conflicting states
    - Side effects have corresponding success/failure actions defined
    """
    ...


@agent.tool
async def verify_data_flow(
        ctx, component_name: str
) -> DataFlowAnalysis:
    """
    Trace data flow from state through to a component's render.

    Returns the complete data path:
    state slice → selector → container → props → component → render

    Identifies:
    - Unnecessary re-renders (subscribing to state it doesn't use)
    - Missing selectors (reading raw state instead of derived)
    - Prop drilling (passing through intermediate components unnecessarily)
    """
    ...


@agent.tool
async def check_side_effect_boundaries(
        ctx, effect: SideEffect
) -> BoundaryValidation:
    """
    Verify that side effects are properly isolated.

    Checks:
    - Side effects don't directly modify state (must dispatch actions)
    - External service calls are behind dependency-injected interfaces
    - Error paths are handled (failure_action is defined and reachable)
    - No side effect triggers another side effect directly (must go
      through action → reducer → side effect chain)
    """
    ...
```

**Notice what happened**: the model isn't being asked "is this valid TypeScript?" It's being asked "is this valid
*architecture*?" The tool encodes domain rules that no general-purpose linter knows about.

## More Domains, More Vocabularies

### Data Engineering / Pipeline Domain

```python
class PipelineStage(BaseModel):
    name: str
    inputs: list[DataContract]
    outputs: list[DataContract]
    idempotent: bool
    retry_policy: RetryPolicy
    data_quality_checks: list[QualityCheck]


class DataContract(BaseModel):
    schema_name: str
    fields: list[FieldSpec]
    partitioning: PartitionSpec | None
    freshness_sla: timedelta
    owner: str


@agent.tool
async def validate_pipeline_stage(
        ctx, stage: PipelineStage
) -> PipelineValidation:
    """
    Validate a pipeline stage against data engineering rules.

    Checks:
    - Output schema is compatible with downstream consumers
    - Idempotency claim is consistent with the operations used
    - Data quality checks cover all NOT NULL and uniqueness constraints
    - Freshness SLA of outputs is achievable given input SLAs
    - No schema evolution breaks backward compatibility
    """
    ...


@agent.tool
async def check_lineage(
        ctx, field_name: str, output_contract: str
) -> LineageTrace:
    """
    Trace a field's lineage back through the pipeline.

    Returns every transformation applied to this field,
    every stage it passed through, and flags:
    - Type coercions that might lose precision
    - Aggregations that change cardinality
    - Joins that might produce NULLs where the contract says NOT NULL
    """
    ...


@agent.tool
async def simulate_backfill(
        ctx, stage: str, date_range: tuple[date, date]
) -> BackfillPlan:
    """
    Simulate what a backfill of this stage would require.

    Returns:
    - Upstream stages that need to be re-run
    - Estimated data volume
    - Downstream stages that would be invalidated
    - Whether the stage's idempotency guarantee holds for the range
    """
    ...
```

### Domain-Driven Design / Business Logic

```python
class Aggregate(BaseModel):
    name: str
    root_entity: str
    entities: list[str]
    value_objects: list[str]
    invariants: list[str]  # business rules in natural language
    commands: list[str]
    events_emitted: list[str]


class BoundedContext(BaseModel):
    name: str
    aggregates: list[Aggregate]
    exposed_events: list[str]  # events other contexts can subscribe to
    consumed_events: list[str]  # events from other contexts
    anti_corruption_layers: list[str]


@agent.tool
async def validate_aggregate_boundaries(
        ctx, aggregate: Aggregate
) -> BoundaryValidation:
    """
    Validate aggregate design against DDD rules.

    Checks:
    - Aggregate isn't too large (entity count, indicates wrong boundaries)
    - All invariants reference only entities within this aggregate
    - No command modifies entities in multiple aggregates
    - Events are named in past tense (domain convention)
    - Value objects are truly immutable in the implementation
    """
    ...


@agent.tool
async def check_context_coupling(
        ctx, context_a: str, context_b: str
) -> CouplingAnalysis:
    """
    Analyze coupling between two bounded contexts.

    Flags:
    - Shared entities (should be separate, mapped through ACL)
    - Synchronous calls between contexts (should be event-driven)
    - Leaked domain language (context A using context B's vocabulary)
    - Missing anti-corruption layer
    """
    ...


@agent.tool
async def verify_invariant(
        ctx, aggregate: str, invariant: str, implementation_code: str
) -> InvariantVerification:
    """
    Check whether the code actually enforces the stated business invariant.

    Uses a combination of:
    - Static analysis (does the code check the condition?)
    - Test generation (create scenarios that would violate the invariant)
    - The type checker (are the types constraining enough to prevent violations?)
    """
    ...
```

### API Design Domain

```python
@agent.tool
async def validate_resource_design(
        ctx, resource: RESTResource
) -> ResourceValidation:
    """
    Validate a REST resource against API design standards.

    Checks:
    - Resource naming follows plural noun convention
    - Sub-resources don't exceed 2 levels of nesting
    - All state mutations have corresponding events for webhooks
    - Pagination is present on all list endpoints
    - Error response schemas are consistent
    - No endpoint returns unbounded collections
    """
    ...


@agent.tool
async def check_backward_compatibility(
        ctx, old_schema: OpenAPISchema, new_schema: OpenAPISchema
) -> CompatibilityReport:
    """
    Verify the new API version is backward compatible.

    Detects:
    - Removed fields (breaking)
    - Changed field types (breaking)
    - New required fields on request bodies (breaking)
    - Narrowed enum values (breaking)
    - New optional fields (safe)
    - Widened enum values (safe)
    """
    ...
```

## The Pattern That Emerges

Every domain has the same structure:

```
Domain Concepts     →  Pydantic Models
     (nouns)              (typed, validated, serializable)

Domain Rules        →  Tool Implementations
     (invariants)         (deterministic checks)

Domain Vocabulary   →  System Prompt + Tool Descriptions
     (ubiquitous           (the model learns to "speak"
      language)             the domain language)

Domain Workflows    →  Training Traces
     (how experts           (examples of correct reasoning
      make decisions)        in domain terms)
```

The model stops thinking in "code" and starts thinking in **domain concepts that happen to be implemented as code**. The
tools enforce that the model's output is valid not just syntactically but *architecturally* and *semantically*.

## What Makes This Different From Just "More Linters"

There's a qualitative difference between language-level tools and domain-level tools. Consider what happens when you
give the model a task like "add a feature to let users export their data":

**With only language-level tools**, the model:

1. Writes code
2. Type checks it ✓
3. Lints it ✓
4. Tests pass ✓
5. Ships code that *works* but puts the export logic inside the User aggregate, couples two bounded contexts, breaks the
   data freshness SLA, and creates a prop-drilling chain five components deep

**With domain-level tools**, the model:

1. Designs the component spec → validates against component rules
2. Defines the new action and state → validates state transitions
3. Checks which bounded context this belongs in → validates boundaries
4. Designs the data flow → validates pipeline impact
5. *Then* writes code, type checks, lints, tests
6. Ships code that is architecturally sound

The domain tools act as **architectural guardrails** that constrain the solution space *before* code is written. This is
how senior engineers actually work — they think about the design in domain terms first and write code second.

## The Training Implication

This is where it connects back to your earlier question about training. When you train a model on traces that include
domain tools:

- It learns the **vocabulary** (components, aggregates, state slices, data contracts)
- It learns the **rules** (pure components don't dispatch actions, aggregates can't span bounded contexts)
- It learns the **workflow** (design first, then implement, then verify at both levels)
- It learns **when to use which tool** (check boundaries before writing code, type check after)

A model trained on these traces doesn't just write better code. It makes better *design decisions*. And those decisions
are verifiable, because the domain tools are deterministic checkers with typed outputs.

That's the real impact. You're not just adding more checks. You're **encoding expert domain knowledge as executable,
verifiable tools** and teaching models to reason with that knowledge.

