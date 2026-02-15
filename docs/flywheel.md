# Flywheel for coding agents

Flywheel is the engine inside Punie. It consists of:

- Small-ish model tuned on Python web development with a focus on tool-calling
- Based on Pydantic AI and Monty
- Code Mode: the model writes Python that calls tools as functions
- Quality triad: `typecheck()`, `ruff_check()`, `pytest_run()` — typed tools that return structured results
- Domain tools that think in domain vocabulary: components, services, middleware (not classes, functions, decorators)
- Code skills and domain skills as extension points
- Spec-driven development: specs generate all artifacts (code, tests, docs, training data)
- Monty: the model writes domain-specific tool code, validated against schemas
- A unifying principal: a focused system that gets better through usage

## The Core Idea

The self-improving loop in five steps:

1. **Generate** — The model writes code or calls tools
2. **Validate** — Tools return structured results (typed with Pydantic)
3. **Execute** — The system runs the code in a sandbox
4. **Capture** — Every interaction becomes a training trace
5. **Retrain** — Fine-tune on validated examples, deploy, repeat

What makes this different from fixed-tool agents: the model learns from its own usage. Domain tools capture design knowledge, not just code mechanics. Each phase produces a better model that generates better training data.

The insight: domain tools are the key. They shift the model's reasoning from "how do I write this code?" to "what design should I implement?"

## Model

We use Qwen3-Coder-30B-A3B as the base. It's a Mixture of Experts model: 30B total parameters, but only ~3B active per forward pass. This gives us 30B model quality at near-7B inference cost.

After 5-bit quantization, the fused model fits in 20 GB. On an M1 Mac with 32GB unified memory, we have zero accuracy loss and excellent speed (2.61s average per query in direct mode).

We've trained through 25+ phases with 857 training examples. The key discoveries: quality beats quantity, format alignment is critical, 30B MoE is the minimum viable architecture for tool calling.

We tested 7B dense models. They failed conclusively. The 30B MoE architecture isn't just better — it's necessary for reliable tool calling.

## Tool Calling

The central technical challenge: local models produce text, frameworks expect structured calls.

Code Mode solves this. The model generates Python code that calls tools as functions. No JSON, no XML, no format parsing chains that break between versions.

This is industry convergence. Anthropic, Cloudflare, and Pydantic AI all arrived at the same pattern independently. The model writes code, tools are functions, execution happens in a sandbox.

For multi-tool operations, Code Mode collapses N+2 model turns into 1-2 turns. Instead of sequential JSON calls with re-reasoning between each tool, the model writes a Python loop that calls N tools. One generation, many executions.

## Code Tools, Code Skills

The quality triad: `typecheck()`, `ruff_check()`, `pytest_run()`.

These are typed tools. They return Pydantic models — `TypeCheckResult`, `RuffResult`, `TestResult` — not raw text. The model can assess its own output quality. This is the foundation for self-improvement.

We adopted the progressive disclosure pattern from Pydantic AI: list available tools, load specific tool docs on demand, execute with full context. This saves tokens and focuses attention.

The model doesn't just call tools. It reasons about structured results. It checks `result.error_count`, iterates over `result.errors`, and makes decisions based on typed data.

## Domain Tools, Domain Skills

The key insight from research: language-level tools say "is this valid Python?" Domain tools say "is this valid architecture?"

We model domain concepts as Pydantic objects: `ComponentSpec`, `ServiceRegistration`, `MiddlewareSpec`. These are the nouns of the domain.

We implement domain rules as deterministic tools: `validate_component()`, `check_state_transitions()`, `validate_middleware_chain()`. These are the verbs.

We teach domain vocabulary through system prompts and skill docs: tdom, svcs, Hopscotch patterns. The model learns to speak the domain language.

Layered validation: AST for fast syntax gates, libcst matchers for convention checking, libcst transformers for auto-fixing, ty for type correctness. Each layer adds semantic depth.

This shifts the model from "how do I write this code?" to "what design should I implement?" The model makes architectural decisions, not just syntax choices.

## Spec Tools, Spec Skills

Spec-driven development: a spec is a unit of work that generates all artifacts.

We work with 3-layer context: Organization, Project, Feature. Each layer has its own vocabulary and rules.

The artifacts include: requirements, plan, code, tests, documentation, training data, interaction recordings, and llms.txt. Everything flows from the spec.

Specs communicate not just to humans but to the system itself. The model reads its own specs. It knows what it's building, why it's building it, and how success is measured.

This closes the loop. The model generates specs, specs generate artifacts, artifacts become training data, training data improves the model.

## Monty

We've identified four levels of tool architecture:

1. **Fixed Tools** — Pre-defined Python functions (current baseline)
2. **Code Mode** — Model writes code that calls tools as functions (Phase 22+)
3. **Monty** — Model writes domain-specific tool code, validated against schemas
4. **Self-Improvement** — The training loop activates, model learns from usage

Monty means the model writes tool implementations on-demand. Not just calls tools, but defines new ones. For domain artifact generation, this is more flexible than fixed tools.

The hybrid strategy: fixed tools for high-risk operations (delete, deploy, git push), Monty for domain artifact generation (components, services, tests).

When the model generates tool code, we validate with `ModelRetry`. If it fails, the model sees the error and corrects. This teach-then-validate loop is how the model learns tool patterns.

## The Training Loop

`TrainingCollector` captures every generation as JSONL traces. Each trace includes: query, generated code, validation result, and outcome.

We filter for quality: only `validation_passed=True` examples make it to training. We augment with negative examples (common errors plus fixes) to teach correction patterns.

We fine-tune with mlx_lm LoRA: train → fuse → quantize to 5-bit → deploy. The metrics we track: validation pass rate (>90%), retry count (<2), and velocity improvement (faster time-to-working-code).

Each phase produces a better model. That model generates better code. That code produces better training data. The flywheel spins.

## Current State

**Working:** Tool discrimination (100%), Code Mode (perplexity 1.826), quality triad complete, 5-bit quantization (20GB, zero accuracy loss), automated training pipeline.

**Key gap:** The model calls tools correctly but doesn't reason about structured results. It generates tool calls but ignores the Pydantic objects they return. 0% field access rate. This needs targeted training data showing how to use `TypeCheckResult.errors`, not just how to call `typecheck()`.

**Next:** Field access training (teach structured result usage), LSP integration (Phase 26, semantic navigation), domain tools bootstrap (Phase 27, component/service/middleware validation), flywheel activation (Phase 28, full retrain with automatic collection).

**Constraint:** 30B MoE minimum for tool calling. 7B dense models conclusively failed in Phase 25. M1 32GB is the target hardware (20GB model + inference overhead).

## References

For detailed architecture and code examples:
- [Holy Grail Architecture](../agent-os/specs/2026-02-15-pydantic-ai-skills-analysis/holy-grail-architecture.md) — Monty evolution, skills framework, validation layers, training collector, milestones
- [Example tdom Skill](../agent-os/specs/2026-02-15-pydantic-ai-skills-analysis/example-tdom-skill.md) — Concrete end-to-end skill flow
- [Research: Holy Grail Tools (Domain)](research/holy-grail-tools-domain.md) — Domain-specific tools research
- [Research: Code Tools Convergence](research/code-tools-convergence.md) — Industry convergence (Anthropic, Cloudflare, Pydantic)

For the development narrative:
- [Diary](diary/) — 28 phases of development, false ends, breakthroughs
