# Honest Analysis: Colleague's Critique of the Flywheel

## Context

A colleague challenged the Flywheel concept -- the self-improving loop where Punie collects traces from real usage, curates them, and retrains the model. This analysis evaluates each critique against Punie's actual evidence (27+ phases of training, benchmarks, and the Devstral experiment).

---

## Critique 1: "Fine-tuning on tool-use traces is shallow"

> "The model learns superficial correlations between error message patterns and code edits... the moment the tool changes its output format, the fine-tuned model falls over."

### Honest verdict: Partially correct, but overstated for this use case

**Where they're right:**

The model IS learning shallow correlations. Punie's own data proves this:

- Phase 26.1 incident: Changing the prompt format (not the content, just the template wrapping) caused a **60-point accuracy drop** (88% → 28%). That's a model clinging to surface patterns, not understanding.
- The model doesn't "understand" type checking. It learned: user says "type errors" → call `typecheck_direct()` → parse JSON → report `errors[].message`. If ty changed from JSON to SARIF output tomorrow, the model would break.
- Base Qwen3 (same architecture, no fine-tuning) scores 0% on tool discrimination. Fine-tuned scores 100%. That delta is learned correlation, not understanding.

**Where they're wrong:**

For tool calling, shallow correlation IS the right thing to learn. The model's job is:

1. **Discrimination** -- When should I call a tool vs answer directly? (100% accuracy)
2. **Selection** -- Which of 14 tools fits this query? (100% accuracy)
3. **Field access** -- Which fields from the result answer the question? (92% accuracy)

None of these require "internalizing the type system." A human doesn't internalize ty's implementation either -- they learn to read its output.

**The real vulnerability:**

The colleague's stronger argument (implied but unstated): **A foundation model with a good system prompt and the tool available at inference will adapt to format changes immediately, while the fine-tuned model needs retraining.** This is true and important. When ty v2 ships with a different output format:

- Foundation model: Update the system prompt. Done in minutes.
- Fine-tuned model: Generate new training examples, retrain (4-6 hours), validate, deploy.

**Mitigating factor:** Punie's typed tools (`TypeCheckResult`, `RuffResult`) abstract the raw tool output. The Pydantic model is the contract, not ty's JSON. If ty changes format, only the parser changes -- the model's training data references the Pydantic fields, not the raw output. This reduces but doesn't eliminate the fragility.

---

## Critique 2: "The flywheel iteration is not cheap"

> "Fine-tuning requires GPU infrastructure, hyperparameter tuning, evaluation benchmarks, regression testing, and someone to verify."

### Honest verdict: Largely correct. Punie's own evidence supports this.

**The flywheel documents promise automation that doesn't exist:**

| What's Promised | What Actually Exists |
|-----------------|---------------------|
| Monthly automated retrain | Never happened. Every phase is manual. |
| A/B testing before deployment | Not implemented |
| Metrics dashboard | Doesn't exist |
| Automated quality filtering | Manual data audits |
| TrainingCollector auto-capture | Not implemented (design only) |
| PunieEvent instrumentation | Not implemented (design only) |

**The real cost of each training phase:**

Looking at the actual codebase: there are **18 training library modules**, **dozens of phase-specific scripts** (generate_ty_training_data.py, generate_ruff_training_data.py, merge_phase28_data.py...), and **separate scripts for every phase** (train_phase28.sh, fuse_phase28.sh, quantize...). Each phase required:

1. Custom data generation scripts (days of work)
2. Data merging and deduplication (hours)
3. Training run (4-6 hours on Mac)
4. Fusion + quantization (1-2 hours)
5. 57-query, 6-layer validation suite (hours to run + interpret)
6. Debugging failures and iterating (days)

**The one genuine cost advantage:** Training runs on a local Mac via MLX LoRA. No cloud GPU bills. No GPU scheduling. This is real and significant -- but it's the training step only. The human effort surrounding each training run dwarfs the compute cost.

**The yield problem:**

The flywheel projects 30-50 high-quality training examples per month at 1 branch/week. The current production dataset is 1,104 examples built over weeks of manual effort. At 40 examples/month, it would take **28 months** to double the dataset through the flywheel alone. That's not a flywheel -- it's a drip.

---

## Critique 3: "We're competing on the wrong turf"

> "We have great domain knowledge to build the tools and no ML infrastructure. Industrial labs have the ML infrastructure and orders of magnitude more data."

### Honest verdict: This is the strongest critique. It cuts to the core.

**The numbers are damning:**

| | Punie | Industrial Labs |
|---|---|---|
| Training examples | 1,215 (planned) | Billions |
| Training infra | 18 Python modules, manual scripts | Automated pipelines, GPU clusters |
| Iteration speed | Weeks per phase | Hours to days |
| ML expertise | One developer learning as they go | Teams of ML researchers |
| Flywheel yield | 30-50 examples/month | Millions of API calls/day |

**The Devstral experiment proved the colleague's point:**

Phase 37/38 showed that a zero-shot Devstral model achieved **84% accuracy with zero training**. The only reason Punie chose Qwen3 over Devstral was **speed** (2.3s vs 95s), not capability. As foundation models get smaller and faster, this speed advantage erodes.

**The uncomfortable projection:**

- 2026: Fine-tuned Qwen3 is 40x faster than zero-shot Devstral. Fine-tuning wins.
- 2027: Smaller foundation models (7B-14B) get better at tool use. Gap narrows to maybe 5-10x.
- 2028: Purpose-built small tool-use models emerge. Gap narrows to 2-3x.
- Eventually: A good small model + system prompt matches fine-tuned speed and accuracy. Fine-tuning advantage disappears.

**What the colleague would say Punie should do instead:**

Invest in what you're uniquely good at:
- **Better tools** (domain validators, LibCST transformations, architectural rules)
- **Better tool descriptions** (system prompts that make zero-shot models effective)
- **Better architecture** (ACP protocol, PyCharm integration, typed results)
- **Wait for models to catch up** rather than fine-tuning to compensate

---

## Where the Colleague is Wrong (or Incomplete)

### 1. Speed matters NOW, not eventually

The 40x speed advantage (2.3s vs 95s) is not a rounding error. For an interactive coding assistant, 95 seconds per response is unusable. Fine-tuning buys a **production-quality experience today** that zero-shot can't deliver on local hardware.

The colleague's implicit assumption is that you can wait for foundation models to get fast enough. But if you're building a product, "eventually" doesn't ship.

### 2. Local inference has structural advantages

Fine-tuning a small local model provides:
- **Privacy**: Code never leaves the developer's machine
- **Zero marginal cost**: No API bills, no rate limits
- **Offline capability**: Works on a plane
- **Latency**: 2.3s round-trip vs network latency + queue time + inference

These aren't temporary advantages -- they're structural. A cloud-based foundation model can't match them even if its accuracy is higher.

### 3. Domain knowledge IS the training data

The colleague says "we have domain knowledge, not ML infrastructure." But domain knowledge is exactly what training data encodes. The 158 domain examples, the architectural validators, the tdom component rules -- these are things no industrial lab has or will produce. The question is whether encoding them as training examples is the best format, or whether encoding them as tool descriptions + system prompts is sufficient.

### 4. The flywheel's real value might not be retraining

The instrumentation design (PunieEvent, sys.monitoring, branch outcome tracking) has value independent of fine-tuning:
- **Debugging**: Understanding why the model made wrong choices
- **Metrics**: Tracking improvement over time
- **User experience**: Identifying pain points
- **Tool design**: Knowing which tools are actually useful

Even if you never retrain, the observation infrastructure is worth building.

---

## Counter-Analysis: What the Critique Misses

The critique frames the flywheel as "competing with industrial labs at ML." But that framing misidentifies what the retraining actually teaches.

### 5. The retraining target is tool orchestration, not general intelligence

Industrial labs train models to be good at *everything* -- code generation, reasoning, conversation, math. Punie's fine-tuning trains for something much narrower: **how to steer 14-26 specific tools in multi-turn sequences**.

Consider what the model actually learns from a trace:

```
User: "Add auth middleware and verify it's wired correctly"
→ Turn 1: workspace_symbols("AuthMiddleware")         # find it
→ Turn 2: read_file("src/middleware/auth.py")          # understand it
→ Turn 3: validate_middleware_chain("src/")             # check wiring
→ Turn 4: typecheck_direct("src/")                      # verify types
→ Turn 5: [synthesize results, report to user]
```

This is **tool orchestration** -- which tool, in what order, with what arguments, using what fields from the previous result to inform the next call. Industrial labs don't train on these specific tools. They can't. These tools don't exist outside Punie. No amount of pretraining data will teach a model that `validate_middleware_chain` exists, what it returns, or when to call it after `workspace_symbols`.

The colleague's comparison to "orders of magnitude more data" is accurate for general capabilities but irrelevant for domain-specific tool steering. The training data for "how to orchestrate Punie's domain validators in a multi-turn coding session" can only come from Punie usage.

### 6. LoRA retraining is genuinely lightweight

The colleague assumes "fine-tuning requires GPU infrastructure." But LoRA fine-tuning on Apple Silicon via MLX is a different beast:

| What the critique assumes | What Punie actually does |
|--------------------------|-------------------------|
| GPU cluster | Mac laptop (MLX on Apple Silicon) |
| Full model fine-tuning | LoRA: 8 layers out of 48 (17%) |
| Hours of hyperparameter search | Proven config, unchanged since Phase 7 |
| Large validation suite | 57-query automated benchmark |
| Weeks of iteration | **~2 hours training + 1 hour fuse/quantize** |

LoRA modifies a thin adapter layer on top of frozen base weights. The base model's general capabilities (code understanding, reasoning, conversation) are untouched. The adapter only learns the tool-calling patterns. This is:

- **Fast**: ~2 hours on a Mac, not days on a GPU cluster
- **Low-risk**: Base model untouched, easy to roll back
- **Incremental**: New tool examples can be added without retraining from scratch
- **Cheap**: Zero compute cost beyond electricity

The comparison to "industrial ML infrastructure" is misleading. LoRA fine-tuning on a local Mac is closer to "configuring an application" than "competing with OpenAI."

### 7. Monty + Pydantic as the insulation layer

The critique's strongest technical point is format fragility: "the moment the tool changes its output format, the fine-tuned model falls over." But Punie's architecture has a designed answer to this.

**The abstraction stack:**

```
Model sees:     Pydantic models (TypeCheckResult, RuffResult, etc.)
                    ↕  (stable contract)
Monty sandbox:  Python code calling typed functions
                    ↕  (Monty bridges)
Tool layer:     Raw tool output (ty JSON, ruff JSON, pytest output)
                    ↕  (parsers — only this layer changes)
External tools: ty, ruff, pytest, git, LSP server
```

When ty changes its output format:
1. **Parser changes** -- update `parse_ty_output()` to handle the new format
2. **Pydantic model stays the same** -- `TypeCheckResult` with `.errors`, `.severity`, `.message`
3. **Model's training data still valid** -- it was trained on Pydantic fields, not raw ty JSON
4. **No retraining needed** -- unless the Pydantic contract itself changes

Monty adds a further insulation layer: the model generates Python code that calls typed functions in a sandbox. If the function signature stays stable (same Pydantic input/output types), the model's generated code still works even if the implementation behind the function completely changes.

**This is the key architectural insight:** The model is trained against a **typed API**, not against raw tool output. Typed APIs change far less frequently than output formats. This directly addresses the format fragility critique.

Could this insulation be stronger? Yes -- if Monty enforced schema validation at the boundary, format changes in the underlying tool would be caught immediately at the parser layer, never reaching the model. This is achievable without retraining.

### 8. The real architectural bet: minimize model, maximize tools

This is the most important counter-argument and the one the critique completely misses.

**The colleague's mental model:**

```
[User Query] → [Big Smart Model] → [Answer]
                      ↑
              (must be very capable)
```

**Punie's mental model:**

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

**The strategic goal is to push as much work as possible from the left column to the right column.**

A domain validator that checks "does this component have @view, return Element, and use html(t'...')" runs in milliseconds, deterministically, with 100% accuracy. The model doesn't need to know those rules -- it just needs to know to call `validate_tdom_component()` and read the result.

This inverts the colleague's framing: **Punie isn't trying to make a smarter model. It's trying to make a dumber model sufficient by making the tools smarter.**

Each new domain tool reduces what the model needs to know. Each architectural validator encodes knowledge that the model doesn't need to learn. The fine-tuning teaches the model *routing* -- a thin, fast skill -- not *reasoning*.

In this frame:
- **The tools ARE the intelligence** (deterministic, fast, correct)
- **The model is just the router** (which tool, what args, in what order)
- **Fine-tuning teaches routing** (shallow correlations are the point, not a weakness)
- **The flywheel improves routing accuracy** (not general intelligence)

This is fundamentally different from "competing with industrial labs at ML." It's closer to building a better compiler with a thin ML-powered frontend.

### 9. What the flywheel actually costs at steady state

The critique prices the flywheel at "GPU infrastructure + hyperparameter tuning + evaluation + regression testing + human verification." But at steady state with proven infrastructure:

| Step | Actual cost |
|------|-------------|
| Collect traces | Zero (instrumentation runs automatically) |
| Filter/curate | Semi-automated (~1 hour/month review) |
| Train | 2 hours on Mac (unattended) |
| Fuse + quantize | 1 hour (scripted) |
| Validate | 30 min (57-query automated suite) |
| Deploy | Swap model file, restart server |

**Total: ~4-5 hours/month, mostly unattended.** Not "GPU infrastructure." Not "competing with industrial labs." More like "running a cron job and reviewing the output."

The colleague's cost estimate applies to the *first time* you build the pipeline (which was expensive: 27+ phases). It doesn't apply to the *steady state* of an established pipeline with proven hyperparameters.

---

## Synthesis: What Should Punie Actually Do?

### What the critique gets right:

The fully automated flywheel (monthly retraining, A/B testing, metrics dashboards) is over-engineered for the current situation. Building that infrastructure competes with industrial labs where Punie has no advantage. The critique is right that effort should flow toward tools and domain knowledge.

### What the critique gets wrong:

It frames fine-tuning as "competing with industrial labs at ML." But Punie's fine-tuning teaches tool orchestration for domain-specific tools that no industrial lab has. The LoRA training is lightweight (2 hours on a Mac, not GPU clusters), and the Monty/Pydantic abstraction stack insulates against format fragility. Most importantly, the architecture pushes intelligence into deterministic tools, making the model's job simpler over time -- the opposite of needing a bigger, smarter model.

### The balanced strategy:

| Invest heavily (70%) | Invest moderately (20%) | Monitor (10%) |
|----------------------|------------------------|----------------|
| Domain tools & validators | LoRA retraining when toolset changes | Zero-shot foundation model progress |
| LibCST transformations | Trace collection for debugging + training | MLX-LM improvements |
| Monty/Pydantic insulation | Automated validation suite | New small model releases |
| ACP architecture | Training data generation per tool batch | |

### The key insight: "minimize model, maximize tools"

The architecture should drive toward:
- **More deterministic tool time** -- every new domain validator is knowledge the model doesn't need to learn
- **Less model reasoning time** -- the model routes, the tools think
- **Thinner LoRA adapter** -- teach routing, not reasoning
- **Monty as stability layer** -- typed API contracts insulate model from tool changes

### The smaller model trajectory

Phase 33 consolidation is complete (1,282 examples, 26 tools, model trained 2026-02-18). This is a good moment to think about where the architecture leads.

**If "minimize model, maximize tools" succeeds, the model gets dumber over time -- on purpose.**

Each new domain tool encodes knowledge that the model no longer needs to reason about. Each LibCST validator replaces a judgment call with a deterministic check. Each Pydantic contract replaces ambiguous output parsing with typed field access. The model's job converges toward a small, well-defined task: **route queries to the right tool, in the right order, with the right arguments.**

Routing is a much simpler task than reasoning. Simpler tasks can be done by smaller models.

**The model size trajectory:**

| Phase | Model | Params (Active) | What the model does | What tools do |
|-------|-------|-----------------|--------------------|----|
| Phase 27 (current) | Qwen3-30B-A3B | 3B active / 30B total | Route + reason + parse | Run tools, return JSON |
| Phase 33 (just completed) | Qwen3-30B-A3B | 3B active / 30B total | Route + parse (domain tools reason for it) | Run tools, validate architecture, return typed results |
| Future: thin router | Qwen3-8B or similar? | 1-3B | Route only | All reasoning is in tools |

**What a smaller model needs to retain:**

1. **Python/HTML/CSS/JS literacy** -- Must understand the languages of the domain to route correctly. Doesn't need Go, Rust, Java, C++, COBOL, or the long tail.
2. **Tool vocabulary** -- The 26 tool names, their argument signatures, what each returns
3. **Multi-turn sequencing** -- Which tool to call next based on the previous tool's result
4. **Discrimination** -- When to answer directly vs call a tool

**What a smaller model can shed:**

1. **General knowledge** -- History, science, math (not needed for tool routing)
2. **Non-target languages** -- A model fine-tuned for Python/HTML/CSS/JS web development can be smaller than a model that also handles 50+ other languages
3. **Deep code generation** -- If Monty + domain tools handle validation, the model generates less code and routes more
4. **Long-form reasoning** -- The tools do the thinking; the model just orchestrates

**The smaller-model experiment:**

A 7B or 8B model fine-tuned with LoRA for Punie's specific tool routing could potentially:

- Load in ~4-5 GB instead of 20 GB (fits on 8GB machines)
- Respond in <1s instead of 2.3s (less computation per token)
- Run alongside IDE without memory pressure
- Still achieve 100% tool discrimination (it's a simpler task than the 30B model handles today)

Phase 25 tried a 7B experiment and found it lacked capacity for complex multi-step reasoning. But that was before the domain tools existed. With 26 tools handling the reasoning, the 7B model only needs to route -- a fundamentally easier job.

**The fine-tuning recipe for a smaller model:**

1. Start from a strong small base (Qwen3-8B, Phi-3, etc.) that's good at Python/JS/HTML/CSS
2. LoRA fine-tune on the same 1,282 examples (tool routing patterns)
3. Optionally: filter base model's pretraining to emphasize web-stack languages (if retraining from scratch becomes feasible with MLX)
4. Validate: does it still route correctly? Speed benchmark vs 30B.

**This is the flywheel's real payoff**, viewed differently: each iteration doesn't just improve the current model -- it makes a smaller model viable by moving more intelligence into tools. The flywheel shrinks the model, not just improves it.

### The tool-building and training-data distinction

"Build tools, not the flywheel" requires nuance. Building a new domain validator (`validate_tdom_component`) is only half the job. The model doesn't know the tool exists until it sees examples of calling it.

**Every new tool needs three things:**

1. **The tool itself** -- Python code, Pydantic models, integration with ACP
2. **Tool-calling training data** -- Examples showing the model when to call it, with what arguments, and how to use the result
3. **Multi-turn training data** -- Examples showing how the tool fits into sequences (e.g., `workspace_symbols` → `read_file` → `validate_tdom_component` → `typecheck_direct`)

The Phase 33 dataset already demonstrates this pattern: each tool category required dedicated training examples (100 for validation tools, 150 for domain tools, 100 for LSP). Adding 5 new LibCST transformation tools would require ~50-100 new tool-calling examples.

**This is where the flywheel has genuine value** -- not as an automated monthly pipeline, but as a systematic way to generate multi-turn tool-calling examples when the toolset changes:

| Trigger | Action | Volume |
|---------|--------|--------|
| New tool added | Generate 20-30 single-tool examples + 10-20 multi-turn sequences | ~40-50 examples |
| Tool signature changes | Update affected examples | ~10-20 examples |
| New multi-turn pattern discovered | Add cross-tool workflow examples | ~10-15 examples |
| Periodic consolidation | Retrain on expanded dataset | Every 3-6 months |

**The key distinction from the colleague's critique:** This training data is not about "learning to use a type checker" -- it's about teaching the model **when to call `validate_tdom_component` vs `typecheck_direct` vs `ruff_check_direct`**, and how to chain them in a meaningful order for architectural validation workflows. That routing knowledge is domain-specific and can only come from domain-specific training data.

**What this means for the "not the full flywheel" recommendation:** Don't build automated trace collection and monthly retraining. But DO build training data generation as part of the tool development process. Each new tool ships with its training examples, like tests ship with code.

### Concrete next steps:

1. **Build tools WITH their training data** -- Each new domain tool or LibCST transformation ships with 30-50 tool-calling examples including multi-turn sequences. Tool development and training data generation are one activity, not two.
2. **Keep the training pipeline simple** -- Proven config, 2-hour LoRA run, automated validation. No need for A/B testing, metrics dashboards, or monthly automation.
3. **Build observability** -- PunieEvent logging is valuable for debugging, metrics, AND occasional training data. Don't over-engineer, but don't skip it either.
4. **Benchmark Phase 33 model** -- Run standard protocol query benchmark against new model to verify no regression.
5. **Experiment with a smaller base model** -- Try Qwen3-8B or similar with the same LoRA training data. If tool routing accuracy holds, the tools-first strategy is validated and the model can shrink.
6. **Strengthen the insulation layer** -- Monty + Pydantic contracts between model and tools. This makes both fine-tuning AND zero-shot approaches more robust.
7. **Test zero-shot periodically** -- When a new small model drops (Qwen4, etc.), benchmark it. If zero-shot at 2-3s hits 90%+ accuracy on routing, the model size question answers itself.

---

## Final Assessment

| Critique Point | Validity | Counter-Argument | Net Impact |
|----------------|----------|-----------------|------------|
| Shallow learning | Partially valid | Shallow routing is the point, not a weakness | Low -- architecture is correct |
| Flywheel cost | Valid for full automation | LoRA steady-state is ~4 hours/month on Mac | Medium -- simplify, don't abandon |
| Wrong competitive turf | Valid for general ML | Tool orchestration IS the home turf | Medium -- reframe what's being trained |

### Bottom line:

**The colleague correctly identifies the risk of over-investing in ML infrastructure.** The flywheel-as-designed (fully automated monthly retraining) is too ambitious. But the counter-arguments are also strong: LoRA is cheap, the training target is domain-specific tool routing (not general intelligence), and the architecture pushes work into deterministic tools where the model needs to be less smart over time.

**The right response is not "abandon fine-tuning" but "simplify the flywheel and double down on tools."** Keep LoRA retraining as a lightweight, manual process triggered by toolset changes. Invest the saved effort in domain tools, LibCST validators, and the Monty insulation layer. These are the durable advantages no industrial lab can replicate.
