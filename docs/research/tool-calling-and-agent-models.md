# Tool Calling and Agent Models: A Hybrid Architecture

This document explores the architecture for building an AI coding agent that combines fuzzy LLM reasoning with deterministic tool execution, and techniques for enabling dynamic customization without retraining models.

## The Big Picture

```text
┌─────────────────────────────────────────────┐
│              Agent (LLM Brain)              │
│  "I see a type error, let me fix this..."   │
│  "This doesn't match the style, let me..."  │
├─────────────────────────────────────────────┤
│            Skill / Tool Layer               │
│  Composable, configurable behaviors         │
│  "fix_types", "apply_style", "refactor"     │
├─────────────────────────────────────────────┤
│         Deterministic Tool Layer            │
│  LSP │ Ruff │ mypy │ black │ tree-sitter   │
│  Custom Python tools │ AST transforms       │
└─────────────────────────────────────────────┘
```

The key insight: **you don't want the model rewriting code character by character when a deterministic tool can do it perfectly**. The model's job is to *decide what to do* and *interpret results*.

## Tool Orchestration Patterns

A "skill" isn't just one tool call—it's a recipe that composes deterministic tools with fuzzy reasoning:

```python
class FixTypeErrors:
    """An 'agent skill' that composes deterministic tools"""

    async def run(self, file_path: str, context: AgentContext):
        # Step 1: Deterministic - get diagnostics from LSP/mypy
        diagnostics = await self.lsp.get_diagnostics(file_path)
        type_errors = [d for d in diagnostics if d.severity == "error"]

        # Step 2: Fuzzy - model interprets and plans
        plan = await self.agent.think(
            f"I found these type errors: {type_errors}\n"
            f"What's the minimal fix strategy?"
        )

        # Step 3: Deterministic - apply structured transforms
        edits = await self.code_tools.apply_edits(plan.edits)

        # Step 4: Deterministic - verify the fix
        new_diagnostics = await self.lsp.get_diagnostics(file_path)

        # Step 5: Fuzzy - did it work? What next?
        if new_diagnostics:
            return await self.agent.decide_next(new_diagnostics)
        return Success(edits)
```

## LSP Client Integration

The Language Server Protocol provides deterministic capabilities that models are bad at:

```python
# What LSP gives you FOR FREE that models are bad at:
# - Go to definition (exact, not hallucinated)
# - Find all references (complete, not approximate)
# - Diagnostics (type errors, lint errors)
# - Code actions (auto-fixes)
# - Hover info (type signatures)
# - Completions (context-aware, deterministic)

# The model should CONSUME this info, not replicate it
```

Key libraries: `pygls` (server implementation), `pylsp`/`lsprotocol` (client implementation).

## The "Skills" Abstraction

Skills are **parameterized workflows** that bridge fuzzy and deterministic execution:

```python
@skill(
    name="write_pythonic_code",
    description="Write Python code following project conventions",
    params={
        "style": "google | numpy | project_custom",
        "type_strictness": "strict | gradual | none",
        "patterns": ["dataclasses", "protocols", "functional"],
    }
)
class WritePythonicCode(Skill):

    async def execute(self, task: str, params: SkillParams):
        # 1. Model generates code (fuzzy)
        code = await self.agent.generate_code(task, params)

        # 2. Deterministic pipeline validates/transforms
        code = await self.pipeline([
            RuffCheck(select=params.lint_rules),
            BlackFormat(line_length=params.line_length),
            MypyCheck(strict=params.type_strictness == "strict"),
            CustomStyleCheck(params.style),  # YOUR rules
        ]).run(code)

        # 3. If pipeline produced errors, model fixes (fuzzy)
        for attempt in range(max_retries):
            errors = self.pipeline.errors
            if not errors:
                break
            code = await self.agent.fix(code, errors)
            code = await self.pipeline.run(code)

        return code
```

## Tree-sitter for Code Understanding

Tree-sitter provides exact, fast AST parsing without requiring the model to understand code structure:

```python
import tree_sitter_python as tspython
from tree_sitter import Language, Parser

# Use tree-sitter to:
# - Extract function signatures
# - Find all classes in a file
# - Locate specific code patterns
# - Make SURGICAL edits (not regenerate whole files)
# - Build context for the model ("here's the function and its callers")

# This is "deterministic tool providing fuzzy context"
```

## Writing Python Your Way: Deterministic vs Fuzzy

Codify preferences as deterministic rules where possible, and fuzzy guidelines where not:

```python
# Deterministic (tools handle these):
# - Import ordering (ruff/isort)
# - Formatting (black/ruff format)
# - Type annotation style (mypy config)
# - Naming conventions (custom ruff rules or pylint)

# Fuzzy (model needs to learn these):
# - When to use a Protocol vs ABC
# - Preferred decomposition patterns
# - How much to abstract
# - Docstring content (not format - that's deterministic)
# - Error handling philosophy
# - "Pythonic" idiom preferences
```

## Beyond Fine-Tuning: Dynamic Customization

Four complementary approaches enable agent customization without retraining models. Each operates with frozen model weights and can be deployed on consumer hardware.

### 1. Context Engineering

**What it is:** Dynamic instruction assembly that places coding standards, style guides, and project rules directly in the prompt. Modern LLMs can utilize 100K+ token contexts efficiently.

**Key Research:**

- **Martin Fowler (2024)**: "Extending an LLM's Context Window" demonstrates that prompting patterns can achieve most customization goals that teams initially think require fine-tuning. Context engineering is lower-cost, more flexible, and easier to iterate than model training.

- **ACE (Advanced Context Engineering, arxiv:2510.04618)**: Framework for structured context assembly—decompose instructions into scoped layers (global rules, file-specific conventions, task-specific guidance), then inject only what's needed for each query. Reduces token waste while maintaining customization depth.

- **Prefix KV Cache Reuse (Claude Code pattern)**: Store common instruction prefixes (project standards, tool descriptions) in the KV cache across requests. Subsequent prompts reuse the cached prefix, achieving 3-5x speedup for repeated operations. Critical for interactive agent workflows.

**How it applies to Punie:**

- Load project-specific standards from `CLAUDE.md`, `pyproject.toml`, and `.ruff.toml` at agent startup
- Inject scoped rules per skill invocation (e.g., "use dataclasses" for data model generation)
- Use prefix caching for shared context (tool descriptions, common imports, style rules)

**Apple Silicon Feasibility:** Excellent. Context engineering has minimal overhead—prompt tokens are processed in parallel during prefill. MLX models handle 100K+ contexts efficiently on M-series chips.

### 2. Deterministic Tool Collaboration

**What it is:** Use external tools to **gather exact information** before the LLM reasons, and to **validate outputs** after generation. The LLM orchestrates but doesn't replicate tool capabilities.

**Key Research:**

- **LSPRAG (ICSE 2026, arxiv:2510.22210)**: "Retrieval-Augmented Generation from Language Servers" shows that LSP-provided context (type info, definitions, references) dramatically improves code generation accuracy. LSP retrieval is faster, more accurate, and cheaper than indexing code into vector DBs.

- **Lanser-CLI (arxiv:2510.22907)**: Combines LLM planning with CLI diagnostics as feedback. The agent proposes code, runs linters/type checkers, interprets diagnostics, and iterates. Diagnostics-as-rewards guide the LLM without backpropagation.

- **Aider's Tree-sitter Repo Maps**: Use tree-sitter to extract structural summaries (class/function signatures, imports) and PageRank to identify high-connectivity modules. Provide this map as context instead of dumping entire files into the prompt.

**How it applies to Punie:**

- LSP client via Agent Communication Protocol provides PyCharm's type info, diagnostics, and navigation
- Ruff and mypy validate generated code before returning to user
- Tree-sitter extracts structural context for fuzzy reasoning

**Apple Silicon Feasibility:** Excellent. All tools (LSP, Ruff, mypy, tree-sitter) are native binaries or Python libraries that run efficiently on Apple Silicon. No GPU required.

### 3. Memory and Personalization

**What it is:** Persistent memory layers that store user preferences, past interactions, coding patterns, and project knowledge. The agent retrieves relevant memories at query time and injects them into the prompt.

**Key Research:**

- **A-Mem (NeurIPS 2025, arxiv:2502.12110)**: Agent memory system using Zettelkasten-inspired knowledge graphs. Memories are linked by semantic relevance and co-occurrence. Retrieval uses graph traversal (not just vector similarity), enabling agents to recall both similar situations and related concepts.

- **Mem0 (arxiv:2504.19413)**: Production-ready memory layer for LLM applications. Automatically extracts facts from conversations, stores in structured format, and retrieves contextually. Works as middleware between user and model—no model modification required.

- **ACE Playbooks (arxiv:2510.04618)**: Context engineering with evolving playbooks. The agent learns "recipes" for recurring tasks (e.g., "add a FastAPI endpoint") by saving successful interaction patterns. Future invocations retrieve and adapt these playbooks.

**How it applies to Punie:**

- Store user coding preferences (naming conventions, abstraction preferences, library choices)
- Remember past refactorings and apply similar patterns to new code
- Build project-specific playbooks for common operations (add endpoint, create test, fix type error)

**Apple Silicon Feasibility:** Excellent. Embedding models (e.g., `nomic-embed-text`) run on Apple Silicon via MLX. Graph-based retrieval (A-Mem) is CPU-bound and fast. Memory storage uses SQLite or lightweight vector DBs (Chroma, LanceDB).

### 4. Recursive Language Models (RLM)

**What it is:** Language models that can recursively call themselves to explore solution spaces beyond the base context window. The prompt itself becomes a "program" that can loop and invoke sub-queries.

**Key Research:**

- **MIT RLM Paper (arxiv:2512.24601)**: Demonstrates recursive self-calls for large-scale reasoning tasks. The model generates intermediate queries, invokes itself on sub-problems, and synthesizes results. Enables hierarchical exploration of codebases that don't fit in a single context.

- **RLM-Qwen3-8B**: 8B parameter model trained for recursive execution. Small enough to run on Apple Silicon (MLX quantized to 4-bit), yet capable of multi-step reasoning. Outperforms larger non-recursive models on tasks requiring exploration (e.g., "find all usages of this pattern across 100 files").

**How it applies to Punie:**

- Multi-file refactoring: recursive search finds all affected files, sub-queries plan changes per file, synthesis merges results
- Codebase exploration beyond context window: "find similar patterns" becomes recursive graph traversal
- Hierarchical planning: top-level call generates plan, sub-calls execute steps, root call validates

**Apple Silicon Feasibility:** Good. RLM-Qwen3-8B quantized to 4-bit runs at ~20-30 tokens/sec on M1 Pro/Max. Recursive calls increase latency (multiple inference passes), but total memory fits in 16GB. Use for deep exploration, not real-time interaction.

## Punie Customization Architecture

Integrating the four layers into Punie's existing ACP/Pydantic AI architecture:

```text
┌────────────────────────────────────────────────┐
│            User Prompt + Task                  │
└───────────────┬────────────────────────────────┘
                │
┌───────────────▼────────────────────────────────┐
│   LAYER 1: Context Engineering                 │
│   Load project standards (CLAUDE.md, config)   │
│   Inject scoped rules per skill                │
│   Use prefix KV cache for shared context       │
└───────────────┬────────────────────────────────┘
                │
┌───────────────▼────────────────────────────────┐
│   LAYER 2: Deterministic Tools (ACP)           │
│   LSP → type info, diagnostics, navigation     │
│   Ruff → linting, auto-fixes                   │
│   Tree-sitter → structural summaries           │
└───────────────┬────────────────────────────────┘
                │
┌───────────────▼────────────────────────────────┐
│   Agent Runtime (Pydantic AI)                  │
│   Model reasoning + tool orchestration         │
└───────────────┬────────────────────────────────┘
                │
┌───────────────▼────────────────────────────────┐
│   LAYER 3: Memory Layer                        │
│   Retrieve user preferences, past patterns     │
│   Store successful workflows as playbooks      │
│   Graph-based recall (A-Mem style)             │
└───────────────┬────────────────────────────────┘
                │
┌───────────────▼────────────────────────────────┐
│   LAYER 4: Recursive Exploration (RLM)         │
│   Multi-file search beyond context window      │
│   Hierarchical planning for large tasks        │
│   (Optional—use for deep exploration only)     │
└───────────────┬────────────────────────────────┘
                │
┌───────────────▼────────────────────────────────┐
│            Execute + Validate                  │
│   Apply edits, run tests, return results       │
└────────────────────────────────────────────────┘
```

### Implementation Priority

1. **Context Engineering** (Immediate):
   - Parser for `CLAUDE.md` and `pyproject.toml` standards
   - Scoped instruction assembly per skill
   - Prefix caching for repeated context

2. **Deterministic Tools** (In Progress):
   - ACP integration with PyCharm LSP (already implemented)
   - Ruff/mypy validation loops (expand existing patterns)
   - Tree-sitter structural summaries (add for repo maps)

3. **Memory Layer** (Next Phase):
   - Preference storage (SQLite + embeddings)
   - Playbook extraction from successful runs
   - Graph-based retrieval for related memories

4. **RLM Integration** (Future):
   - RLM-Qwen3-8B as optional exploration model
   - Hierarchical planning for multi-file refactors
   - Use sparingly—most tasks fit in base context

### Hardware Requirements per Layer

| Layer | Model Size | Memory | Latency | Apple Silicon |
|-------|-----------|--------|---------|---------------|
| Context Engineering | Any | +context tokens | Parallel prefill | ✓ Excellent |
| Deterministic Tools | N/A | Minimal | <100ms per tool | ✓ Native binaries |
| Memory | Embeddings (~100M) | ~1GB | <50ms retrieval | ✓ MLX embeddings |
| RLM | 8B (4-bit quant) | ~6GB | 2-3x base latency | ✓ 16GB RAM sufficient |

All layers are feasible on M1 Pro/Max or better (16GB+ recommended).

## Learning Priority for Implementation

```text
1. Context engineering patterns        (instruction assembly, prefix caching)
2. LSP protocol + pygls/pylsp          (tool backbone)
3. Tree-sitter Python bindings         (structural code understanding)
4. Ruff as a library (not just CLI)    (fast linting/fixing)
5. Agent loop design patterns          (ReAct, plan-execute, tool validation)
6. Memory layer design                 (embeddings, graph retrieval, playbooks)
7. Evaluation harness                  (does it write code YOUR way?)
8. RLM integration                     (recursive exploration for large tasks)
```

The fundamental bet: **models are good at fuzzy reasoning and bad at precision; deterministic tools are the opposite. Marry them.** The challenge is designing the skill layer in the middle so it's expressive enough for the model to compose but rigid enough to be reliable.

## References

### Context Engineering

- Martin Fowler (2024). "Extending an LLM's Context Window." [martinfowler.com/articles/2024-llm-context.html](https://martinfowler.com/articles/2024-llm-context.html)
- ACE: Advanced Context Engineering. arxiv:2510.04618
- Claude Code documentation: CLAUDE.md pattern for project instructions

### Deterministic Tool Collaboration

- LSPRAG: Retrieval-Augmented Generation from Language Servers. ICSE 2026, arxiv:2510.22210
- Lanser-CLI: LLM-Enhanced Command Line Interaction. arxiv:2510.22907
- Aider documentation: Repository maps with tree-sitter and PageRank

### Memory and Personalization

- A-Mem: Agent Memory with Zettelkasten-Inspired Knowledge Graphs. NeurIPS 2025, arxiv:2502.12110
- Mem0: Memory Layer for LLM Applications. arxiv:2504.19413
- ACE Playbooks: Evolving task recipes from successful interactions (arxiv:2510.04618)

### Recursive Language Models

- Recursive Language Models. MIT, arxiv:2512.24601
- RLM-Qwen3-8B: 8B parameter model trained for recursive execution

### Tool Ecosystems

- Language Server Protocol (LSP): [microsoft.github.io/language-server-protocol](https://microsoft.github.io/language-server-protocol/)
- Tree-sitter: [tree-sitter.github.io/tree-sitter](https://tree-sitter.github.io/tree-sitter/)
- Ruff: [docs.astral.sh/ruff](https://docs.astral.sh/ruff/)
- MLX: Apple's ML framework for Apple Silicon [ml-explore.github.io/mlx](https://ml-explore.github.io/mlx/)
