# Flywheel for coding agents

We want a fast, local, accurate, ethical coding agent for Python web development. Built atop an innovative engine that
lets the developer drive and improve the agent.

Welcome to Flywheel, the AI coding agent engine inside Punie. It brings a layered set of new thinking:

- *Model*. A subset of an open source coding model, pruned to Python/HTML/CSS/JavaScript, and trained with ethical model
  datasets
  and tool-calling datasets
- *Code tools*. Re-build and re-train the model to work with Python *tooling* (ty, ruff, LSP, etc.) for semantics
  instead of syntax. Introduce *code skills* to let the developer steer these tools, agentically.
- *Sandboxed code tool generation*. Use Pydantic's Monty to generate tools that it needs, on the fly, from the model.
- *Domain tools*. Think in terms of larger building blocks from the domain, and train a model around that domain's
  entities, connections, rules, and code styles. Provide *domain skills* to let the developer interact with these tools,
  agentically.
- *Spec-driven development*. Formalize a way of working that helps Flywheel capture high-signal training data and
  continuously evolve and improve.

## Overview

Flywheel consists of:

- Small-ish model tuned on Python web development with a focus on tool-calling
- Based on Pydantic AI and Monty
- Code Mode: the model writes Python that calls tools as functions
- Quality triad: `typecheck()`, `ruff_check()`, `pytest_run()` — typed tools that return structured results
- Domain tools that think in domain vocabulary: components, services, middleware (not classes, functions, decorators)
- Code skills and domain skills as extension points
- Spec-driven development: specs generate all artifacts (code, tests, docs, training data)
- Monty: the model writes domain-specific tool code, validated against schemas
- A unifying principal: a focused system that gets better through usage

## Isn't this too opinionated?

It's true, this whole idea, and the Themester ecosystem it will power, will be feel very structured. But Flywheel
believes this is for a purpose. We want a broad ecosystem of quality themes, components, and tools. But we also want
agentic coding that promotes our ideals and writes the code we would have written ourselves. More structure can be put
to use by a new style of agent.

## The Core Idea

The self-improving loop in five steps:

1. **Generate** — The model writes code or calls tools
2. **Validate** — Tools return structured results (typed with Pydantic)
3. **Execute** — The system runs the code in a sandbox
4. **Capture** — Every interaction becomes a training trace
5. **Retrain** — Fine-tune on validated examples, deploy, repeat

What makes this different from fixed-tool agents: the model learns from its own usage. Domain tools capture design
knowledge, not just code mechanics. Each phase produces a better model that generates better training data.

The insight: domain tools are the key. They shift the model's reasoning from "how do I write this code?" to "what design
should I implement?"

## Model

We use Qwen3-Coder-30B-A3B as the base. It's a Mixture of Experts model: 30B total parameters, but only ~3B active per
forward pass. This gives us 30B model quality at near-7B inference cost.

After 5-bit quantization, the fused model fits in 20 GB. On an M1 Mac with 32GB unified memory, we have zero accuracy
loss and excellent speed (2.61s average per query in direct mode).

We've trained through 25+ phases with 857 training examples. The key discoveries: quality beats quantity, format
alignment is critical, 30B MoE is the minimum viable architecture for tool calling.

We tested 7B dense models. They failed conclusively. The 30B MoE architecture isn't just better — it's necessary for
reliable tool calling.

## Tool Calling

The central technical challenge: local models produce text, frameworks expect structured calls.

Code Mode solves this. The model generates Python code that calls tools as functions. No JSON, no XML, no format parsing
chains that break between versions.

This is industry convergence. Anthropic, Cloudflare, and Pydantic AI all arrived at the same pattern independently. The
model writes code, tools are functions, execution happens in a sandbox.

For multi-tool operations, Code Mode collapses N+2 model turns into 1-2 turns. Instead of sequential JSON calls with
re-reasoning between each tool, the model writes a Python loop that calls N tools. One generation, many executions.

## Code Tools, Code Skills

The quality triad: `typecheck()`, `ruff_check()`, `pytest_run()`.

These are typed tools. They return Pydantic models — `TypeCheckResult`, `RuffResult`, `TestResult` — not raw text. The
model can assess its own output quality. This is the foundation for self-improvement.

We adopted the progressive disclosure pattern from Pydantic AI: list available tools, load specific tool docs on demand,
execute with full context. This saves tokens and focuses attention.

The model doesn't just call tools. It reasons about structured results. It checks `result.error_count`, iterates over
`result.errors`, and makes decisions based on typed data.

## Domain Tools, Domain Skills

The key insight from research: language-level tools say "is this valid Python?" Domain tools say "is this valid
architecture?"

We model domain concepts as Pydantic objects: `ComponentSpec`, `ServiceRegistration`, `MiddlewareSpec`. These are the
nouns of the domain.

We implement domain rules as deterministic tools: `validate_component()`, `check_state_transitions()`,
`validate_middleware_chain()`. These are the verbs.

We teach domain vocabulary through system prompts and skill docs: tdom, svcs, Hopscotch patterns. The model learns to
speak the domain language.

Layered validation: AST for fast syntax gates, libcst matchers for convention checking, libcst transformers for
auto-fixing, ty for type correctness. Each layer adds semantic depth.

This shifts the model from "how do I write this code?" to "what design should I implement?" The model makes
architectural decisions, not just syntax choices.

## The Key Insight: Minimize Model, Maximize Tools

The architecture has a core strategic realization: **each domain tool reduces what the model needs to learn.**

Two different mental models of what an AI coding agent does:

**Traditional approach:**
```
[User Query] → [Big Smart Model] → [Answer]
                      ↑
              (must be very capable)
```

**Punie's approach:**
```
[User Query] → [Small Fast Model] → [Tool Call] → [Deterministic Tool] → [Structured Result]
                      ↑                                    ↑
              (just needs to route)            (this is where the real work happens)
```

The agentic loop has two kinds of time:

| Time in model (non-deterministic) | Time in tools (deterministic) |
|---|---|
| Choosing which tool to call | Running typecheck, parsing AST, validating architecture |
| Parsing result fields | LibCST analysis, pattern matching, scope resolution |
| Deciding next step in sequence | Git operations, file I/O, test execution |
| Generating natural language response | LSP navigation, symbol resolution |

**The strategic goal: push as much work as possible from the left column to the right column.**

A domain validator that checks "does this component have @view, return Element, and use html(t'...')" runs in milliseconds, deterministically, with 100% accuracy. The model doesn't need to know those rules — it just needs to know to call `validate_tdom_component()` and read the result.

This inverts conventional wisdom: **Punie isn't trying to make a smarter model. It's trying to make a dumber model sufficient by making the tools smarter.**

In this frame:
- **The tools are the intelligence** (deterministic, fast, correct)
- **The model is just the router** (which tool, what args, in what order)
- **Fine-tuning teaches routing** (shallow correlations are the point, not a weakness)
- **Each new tool shrinks what the model must learn** (knowledge moves from model to tools)

This is fundamentally different from "competing with industrial labs at ML." It's closer to building a compiler with a thin ML-powered frontend.

## Spec Tools, Spec Skills

Spec-driven development: a spec is a unit of work that generates all artifacts.

We work with 3-layer context: Organization, Project, Feature. Each layer has its own vocabulary and rules.

The artifacts include: requirements, plan, code, tests, documentation, training data, interaction recordings, and
llms.txt. Everything flows from the spec.

Specs communicate not just to humans but to the system itself. The model reads its own specs. It knows what it's
building, why it's building it, and how success is measured.

This closes the loop. The model generates specs, specs generate artifacts, artifacts become training data, training data
improves the model.

## Monty

We've identified four levels of tool architecture:

1. **Fixed Tools** — Pre-defined Python functions (current baseline)
2. **Code Mode** — Model writes code that calls tools as functions (Phase 22+)
3. **Monty** — Model writes domain-specific tool code, validated against schemas
4. **Self-Improvement** — The training loop activates, model learns from usage

Monty means the model writes tool implementations on-demand. Not just calls tools, but defines new ones. For domain
artifact generation, this is more flexible than fixed tools.

The hybrid strategy: fixed tools for high-risk operations (delete, deploy, git push), Monty for domain artifact
generation (components, services, tests).

When the model generates tool code, we validate with `ModelRetry`. If it fails, the model sees the error and corrects.
This teach-then-validate loop is how the model learns tool patterns.

## The Training Loop

The real pipeline is simpler and more manual than initially envisioned:

1. **Data generation** — Write training examples alongside each new tool (20-50 examples per tool category)
2. **Data merging** — Combine with existing dataset, deduplicate
3. **LoRA training** — 2-hour run on Mac with proven hyperparameters (unchanged since Phase 7)
4. **Fusion + quantization** — Dequantize to float16, fuse LoRA adapters, re-quantize to 5-bit (1-2 hours)
5. **Validation** — Automated evaluation suite (27-57 queries across tool categories)
6. **Deploy** — Swap model file, restart server

This isn't monthly automation. It's manual retraining triggered by toolset changes — every 3-6 months when enough new tools accumulate.

The aspirational goal: automatic trace collection from real usage, filtering, curation, and retraining. The reality: Phase 33 reached 1,282 examples through 27+ phases of manual data generation. Each phase required days of script writing, data auditing, and validation work.

The training data isn't about "learning to use tools" — it's about teaching the model **when to call which tool**, with what arguments, in what order. That routing knowledge is domain-specific. When a new domain validator is added, the model needs examples showing how it fits into multi-turn sequences.

Read [Flywheel Capture](./research/flywheel-capture.md) and [Flywheel Critique Analysis](./research/flywheel-critique-analysis.md) for more details.

## The spec workflow

To boost this idea of training loops, let's define a spec-driven workflow.

First, we'll use the three-layer context from Agent OS: Organization, Project, and Feature. (Later we might add a
broader one: Ecosystem.)

### Project spec

- Generate a `mission.md`, `tech-stack.md`, and `roadmap.md`.
- Have good tools to keep these up-to-date, such as slash commands or skills.
- Make it easy to put something in the parking lot without losing it.
- Also make it easy to refactor project-specific stuff out into Organization or even Ecosystem.

### Feature spec

This is where the real Flywheel kicks in.

- Draft some notes in `docs/features.md` as the starting point. Make it clear that this page will be rewritten during
  the life of the feature.
- Schedule this work onto the roadmap.
- When ready, start on the feature by making a feature branch or even better git worktree. Update the roadmap to reflect
  status.
- The branch and the spec are the unit of collection for Flywheel. All docs, prompts, results, user opinions, tool
  calls, etc. are stored per-feature.
- Do the equivalent of `/shape-spec` in plan mode to create the "spec":
    - `plan.md`
    - `references.md`
    - `shape.md`
- Perhaps we have the equivalent of a slash command:
    - Find the next roadmap item or choose it
    - Make a branch
    - Go into an analysis mode
    - Ask questions and generate spec
    - Leave analysis mode and start on first task group
    - Run verification suite at the end
    - Commit
    - Merge-squash
    - Update changelog
- Have a single format for `plan.md` as task groups
- Link this "spec" back to the roadmap and adjust the status
- From the beginning of the slash command, capture whatever training data Flywheel thinks it needs
- During each task group, record all the stuff
- As the user prompts to correct/refine/expand, add flags in the prompt that help the training. Perhaps explicitly say (
  with a slash command? a special prefix?) that we are doing a correction, or an addition, etc. Perhaps also a way to
  indicate happiness with that step, scale of 1 to 5.
- Let the developer define their acceptance test, validation suite, verification step, perhaps as a "skill."
- But run it as a formal step that is wired to really help collect high-signal training data.
- It might take multiple refinements and verification steps to finish the implementation.
- The user might also change their mind on the feature spec or even the project spec. This signal should be captured.
- Keep in mind that later features might make changes that affect the spec and implementation of earlier features. This
  should be encouraged and useful signals captured.
- We'll be using Hopscotch and Themester domains. In particular, service oriented architecture. This "domain tools" idea
  might let us design a higher-signal "domain training" capture.

## Other requirements

- We want Punie to run in a server mode
- So we want to structure `~/.punie/training_data/` as `project/feature/*`
- We need good tooling to work with this training data
    - Consolidate all the data for a feature into a nice tight curated dataset
    - Perhaps as a dialog with the user
    - Make sure we don't mess up the model by retraining on the same data
    - Perhaps put `~/.punie` under version control to easily see what's already been trained

## Where the Flywheel Stands Honestly

**Production model (Phase 33b, Feb 2026):**
- 1,282 training examples across 26 tools
- Qwen3-30B-A3B base (3B active / 30B total MoE)
- 5-bit quantized, 20 GB on disk
- 82.4% eval accuracy (27-prompt held-out test)
- 2-5 second average response time on M1 32GB
- Tools: typecheck, ruff, pytest, LSP (8 tools), LibCST (3 tools), domain validators (12 tools)

**What works:**
- ✅ Tool discrimination (100%) — knows when to call a tool vs answer directly
- ✅ Tool selection (100%) — chooses the right tool for each query
- ✅ Field access (92%) — reads structured results from Pydantic models
- ✅ Multi-tool workflows (81.9% overall) — chains tools in meaningful sequences
- ✅ Code Mode — model writes Python code that calls tools as functions
- ✅ LoRA training pipeline — proven config, 2-hour runs on Mac, automated validation

**What doesn't exist (but the early docs promised):**
- ❌ Automatic trace collection from real usage (design exists, not implemented)
- ❌ Monthly automated retraining (every phase is manual)
- ❌ A/B testing before deployment (not implemented)
- ❌ Metrics dashboards (not implemented)
- ❌ Automated quality filtering (manual data audits)
- ❌ TrainingCollector auto-capture (design only)

**Key findings across 27+ phases:**
- **Model size**: 30B MoE is minimum for reliable tool calling. 7B dense failed conclusively (Phase 25).
- **Quantization**: 5-bit optimal (32 levels preserve LoRA signal; 4-bit destroys it; 6-bit triggers memory warnings).
- **Format alignment**: Prompt format mismatch causes 60-point accuracy drops (Phase 26.1 incident).
- **Domain tools matter**: Multi-tool accuracy jumped from 35% to 81.9% when domain validators were added.

**The colleague's critique (Feb 2026):**

A colleague challenged the flywheel concept: "You're competing with industrial labs on ML when your advantage is domain knowledge. Fine-tuning requires infrastructure you don't have. The moment a tool changes format, the model breaks."

The honest analysis ([documented here](./research/flywheel-critique-analysis.md)) found they were:
- **Right about infrastructure**: The fully automated flywheel is over-engineered. 27+ phases = manual work, not automation.
- **Right about cost**: Each phase took days of data generation, merging, validation — not just 2 hours of training.
- **Wrong about LoRA lightweight**: 2-hour Mac training is NOT "GPU infrastructure." It's closer to running a cron job.
- **Wrong about fragility**: Pydantic models abstract tool output. Format changes affect parsers, not trained model.
- **Wrong about competition**: Training teaches tool **routing** for domain-specific tools no industrial lab has, not general intelligence.

The strategic realization: **invest 70% in tools, 20% in lightweight retraining when tools change, 10% monitoring zero-shot foundation model progress.**

**Next phases (see roadmap):** Fix Phase 28/29 bugs → ACP router infrastructure → simplified observability → smaller model experiment.

## The Smaller Model Trajectory

If "minimize model, maximize tools" succeeds, the model should get dumber over time — **on purpose.**

Each new domain tool encodes knowledge the model no longer needs to reason about. Each LibCST validator replaces a judgment call with a deterministic check. Each Pydantic contract replaces ambiguous output parsing with typed field access. The model's job converges toward a small, well-defined task: **route queries to the right tool, in the right order, with the right arguments.**

Routing is simpler than reasoning. Simpler tasks can be done by smaller models.

**Model size trajectory:**

| Phase | Model | Params (Active) | What the model does | What tools do |
|-------|-------|-----------------|--------------------|----|
| Phase 27 | Qwen3-30B-A3B | 3B active / 30B total | Route + reason + parse | Run tools, return JSON |
| Phase 33 | Qwen3-30B-A3B | 3B active / 30B total | Route + parse (domain tools reason for it) | Run tools, validate architecture, return typed results |
| Future | Qwen3-8B or similar? | 1-3B | Route only | All reasoning is in tools |

**What a smaller model needs:**
1. Python/HTML/CSS/JS literacy (not Go, Rust, Java, or 50+ other languages)
2. Tool vocabulary (the 26 tool names, arguments, return types)
3. Multi-turn sequencing (which tool next based on previous result)
4. Discrimination (when to answer directly vs call a tool)

**What a smaller model can shed:**
1. General knowledge (history, science, math — not needed for tool routing)
2. Non-target languages (shedding 50+ languages makes the model smaller)
3. Deep code generation (Monty + domain tools handle validation)
4. Long-form reasoning (tools do the thinking; model just orchestrates)

**The experiment:** Phase 25 tried 7B and failed — the model lacked capacity for complex reasoning. But that was **before domain tools existed**. With 26 tools handling the reasoning, the 7B model only needed to route — a fundamentally easier job. Phase 33 consolidation (1,282 examples, 26 tools) is the right moment to revisit this question.

**The test:** Fine-tune Qwen3-8B with the same 1,282 examples. If tool routing accuracy holds (≥80% on the 27-prompt eval), the tools-first strategy is validated. If it fails, 30B MoE remains the minimum.

A smaller model that fits in 4-5 GB instead of 20 GB would:
- Run on 8GB machines (not just 32GB)
- Respond in <1s instead of 2.3s
- Run alongside IDE without memory pressure

This is the flywheel's real payoff, viewed differently: **each iteration doesn't just improve the current model — it makes a smaller model viable by moving intelligence into tools.** The flywheel shrinks the model, not just improves it.

## References

For detailed architecture and code examples:

- [Holy Grail Architecture](../agent-os/specs/2026-02-15-pydantic-ai-skills-analysis/holy-grail-architecture.md) — Monty
  evolution, skills framework, validation layers, training collector, milestones
- [Example tdom Skill](../agent-os/specs/2026-02-15-pydantic-ai-skills-analysis/example-tdom-skill.md) — Concrete
  end-to-end skill flow
- [Research: Holy Grail Tools (Domain)](research/holy-grail-tools-domain.md) — Domain-specific tools research
- [Research: Code Tools Convergence](research/code-tools-convergence.md) — Industry convergence (Anthropic, Cloudflare,
  Pydantic)

For the flywheel critique and strategic analysis:

- [Flywheel Critique Analysis](research/flywheel-critique-analysis.md) — Counter-arguments to colleague's critique, tool-first strategy, smaller model trajectory
- [Colleague Counter-Argument](research/colleague-counter-argument.md) — Skeptical challenges to the counter-arguments (to be written)

For the development narrative:

- [Diary](diary/) — 28 phases of development, false ends, breakthroughs
