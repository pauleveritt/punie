# Minimum Model Requirements for Punie

**Research findings from 27 phases of development**
**Updated: February 2026**

## Executive Summary

Punie requires specific model capabilities beyond just parameter count. Through 27 phases of fine-tuning experiments, we've identified a tiered set of requirements:

- **4 Must-Have requirements** - Model is unusable without these
- **3 Should-Have requirements** - Significant effort to work around
- **4 Nice-to-Have requirements** - Helpful but can work without

**Our production model:** Qwen3-Coder-30B-A3B (MoE) satisfies all 11 requirements.

**Failed experiments:**
- 7B dense (Phase 25b) - **Conclusively failed** even with perfect setup
- 8B dense (Phase 40) - **Failed** — learned intent routing (18.5%) but not execute_code format
- 1.5B dense (never attempted) - Would be catastrophic

**Production model confirmed:** Qwen3-Coder-30B-A3B (MoE) — Phase 33b scripts confirm this has
always been the Coder variant, not a general Qwen3 base. Code-biased pretraining already active.

**Phase 43 candidates under evaluation:**
- Qwen3-14B Dense (Experiment B) — See Phase 43b analysis below (MoE hypothesis test)
- Qwen3-Coder-30B-A3B re-run (Experiment A) — Baseline confirmation, domain/multi_tool focus

**Devstral Small 2 (24B dense):** Evaluation below. Not yet tested. Speed concern (8x slower).

---

## Must-Have Requirements

*Model is unusable without these - do not attempt training without all 4*

### M1. Native Tool Calling Tokens ⭐ CRITICAL

#### What It Means

The model's tokenizer has **single-token representations** for tool calling delimiters, not multi-token spans.

**Examples:**
- **Qwen3:** `<tool_call>` as token ID 151657 (single token) ✅
- **Mistral 3:** `[TOOL_CALLS]` as single token ✅
- **Qwen2.5:** `<tool_call>` tokenizes as 5 subwords (`<`, `tool`, `_`, `call`, `>`) ❌

#### Why It's Critical

**Single tokens create atomic patterns:**
```python
# Model learns: "When I see token 151657, enter tool mode"
# vs
# Model learns: "When I see this 5-token sequence..."
```

**Impact on training:**
- Single tokens consume 1 context position vs 5
- Model attention focuses on tool call as a unit
- Easier pattern recognition during fine-tuning
- Cleaner generation (can't partial-generate delimiters)

#### Evidence from Phase 25

**Phase 25 Critical Flaw #1:**
> **`<tool_response>` token doesn't exist in Qwen2.5**
> - 58% of training data (398/685 examples) uses `<tool_response>` / `</tool_response>`
> - Qwen3 has these as single tokens (ID 151665/151666)
> - Qwen2.5 tokenizes as ~5 subword pieces
> - **Impact:** Multi-turn tool-calling pattern corrupted during training

**Result:** Training fought against base model tokenization → 0% tool calling accuracy

#### Important Note

Different model families use different tool calling tokens:
- **Qwen3:** `<tool_call>`, `<tool_response>`, `</tool_call>`, `</tool_response>`
- **Mistral 3:** `[TOOL_CALLS]`, `[TOOL_RESULTS]`, `[/TOOL_CALLS]`, `[/TOOL_RESULTS]`
- **DeepSeek V3:** Custom tokens (verify before use)

**Verification before any work:**
```python
# Check tokenizer vocabulary for tool calling tokens
tokenizer = AutoTokenizer.from_pretrained("model-name")
vocab = tokenizer.get_vocab()

# Must find these as SINGLE tokens:
assert "<tool_call>" in vocab or "[TOOL_CALLS]" in vocab
assert "<tool_response>" in vocab or "[TOOL_RESULTS]" in vocab
```

---

### M2. Sufficient Model Capacity for Tool Calling

#### What It Means

The model has enough parameters to:
- Maintain context across multiple tool invocations
- Learn structured code generation patterns
- Handle multi-step reasoning workflows
- Specialize in different aspects of tool calling

#### Evidence-Based Thresholds

**Confirmed failures:**
- **7B dense:** ❌ Failed conclusively (Phase 25b with perfect setup)
- **8B dense:** ❌ Failed (Phase 40, 18.5%) — learned tool names but not execute_code format
- **1.5B dense:** ❌ Would be catastrophic (never tested, extrapolated)

**Confirmed successes:**
- **30B MoE (3B active):** ✅ Production model (Qwen3-Coder-30B-A3B, Phase 33b: 82.4%)

**Open questions (Phase 43 experiments):**
- **14B dense:** Testing in Phase 43b — cleanest test of MoE vs total-params hypothesis
- **24B dense:** Untested - Devstral Small 2 would answer this
- **14B MoE:** Untested - Could work if experts specialized enough
- **20B dense:** Untested - Likely minimum for dense architectures

#### Why 7B Dense Failed (Phase 25b Conclusive)

**Phase 25b fixed ALL 5 setup flaws from Phase 25:**
1. ✅ Converted training data to Qwen2.5 JSON format
2. ✅ Replaced `<tool_response>` with Qwen2.5 convention
3. ✅ Unified to single format (no XML/Python mix)
4. ✅ Added tool definitions to system prompt
5. ✅ Fixed eos_token_id in fused config

**Result:** Identical failure - 0% tool calling accuracy

**Conclusion:** Insufficient capacity is the most likely explanation, though architecture mismatch (dense vs MoE) remains a possible contributing factor. The 30B MoE baseline in Phase 25b achieved 95% (19/20), not 100%, suggesting even larger models have limits.

**Why 7B is insufficient:**
```
Tool calling requires multiple specialized capabilities:
1. Tool discrimination (choose tool vs direct answer)
2. Code generation (syntactically correct Python)
3. Field access (navigate Pydantic structures)
4. Result synthesis (integrate tool outputs)
5. Error handling (recognize failures, retry)

7B parameters must handle ALL 5 with same weights.
MoE can dedicate different experts to each capability.
```

#### The MoE Advantage

**MoE architecture:**
- Total parameters >> Active parameters per forward pass
- Different experts specialize in different tasks
- Example: Qwen3-30B-A3B = 30B total, ~3B active

**Dense models:**
- All parameters active every forward pass
- No specialization - single weight matrix for everything
- Requires more total parameters for same capability

**From Phase 27.5 honest audit:**
> "Cross-tool workflows: 0% accuracy (0/5 queries) on realistic evaluation"
> "Even 30B MoE struggles with complex multi-step reasoning"

This suggests that **dense models likely need 20B+ parameters** to match 30B MoE performance.

---

### M3. Training Data Format Compatibility ⭐ MOST IMPACTFUL FINDING

#### What It Means

Training data format **MUST** match the model's native chat template. This is **not negotiable** - format mismatches cause catastrophic accuracy drops.

#### Evidence: Phase 26.1 Discovery

**Most impactful single finding across all 27 phases:**

| Format | Accuracy | Impact |
|--------|----------|--------|
| Wrong format (plain text) | 28% | Baseline |
| **Correct format (ChatML)** | **88%** | **+60 points!** |

**Root cause:** Validation script used plain text prompts instead of `tokenizer.apply_chat_template()`

**Result:** 60-point accuracy drop from a single formatting mistake

#### Why Format Matters So Much

**Training pipeline:**
```python
# During training (what model learns on)
messages = [{"role": "system", "content": "..."}, ...]
prompt = tokenizer.apply_chat_template(messages)  # ChatML format
→ <|im_start|>system\n...<|im_end|>\n<|im_start|>user\n...<|im_end|>

# Validation script (what we test on)
# WRONG: prompt = f"User: {query}\nAssistant:"  # Plain text ❌
# RIGHT: prompt = format_prompt(query, model_path)  # ChatML ✅
```

**When formats mismatch:**
- Token sequences don't match training distribution
- Model sees unfamiliar patterns
- Attention mechanisms optimized for different structure
- Generation quality collapses

#### Phase 25 Format Mismatch

**Phase 25 had both setup AND format issues:**
- Training data: Qwen3 XML format (`<function=...>`)
- Base model: Qwen2.5 expects JSON format (`{"name": "...", "arguments": {...}}`)
- Multi-token spans instead of single tokens
- Result: 0% tool calling accuracy

#### Critical Standard: CLAUDE.md Requirement

**From project standards:**
> **CRITICAL**: When writing test scripts or validation tools that format prompts for model inference, **always use `punie.agent.prompt_utils.format_prompt()`**. Never use manual string formatting.

```python
# ✅ CORRECT: Always use this
from punie.agent.prompt_utils import format_prompt
prompt = format_prompt("Check types in src/", model_path)

# ❌ WRONG: Never do this!
# prompt = f"User: {query}\nAssistant:"
# This causes train/test format mismatch and 60+ point accuracy drop!
```

#### Implication for New Models

**Switching to a different model family requires:**
1. Identify native chat template (ChatML, Llama, Mistral, etc.)
2. Reformat ALL training data (1104 examples for Phase 27)
3. Update `format_prompt()` utility
4. Verify format match before any training

**Estimate:** 2-3 days minimum for training data reformatting alone, plus 4-6 days for runtime infrastructure updates (see M3 assessment in Devstral evaluation for full scope)

---

### M4. Code-Specific Pretraining

#### What It Means

The base model was pretrained on:
- Massive code corpora (100B+ tokens of GitHub, Stack Overflow)
- Programming documentation and API references
- Code-focused instruction datasets
- Common patterns: APIs, error messages, test frameworks

#### Why It's Critical

**Phase 27 toolset requires deep code understanding:**

**14 typed tools across 4 domains:**
1. **LSP Navigation (5 tools):** goto_definition, find_references, hover, document_symbols, workspace_symbols
2. **Code Quality (3 tools):** typecheck, ruff_check, pytest_run
3. **Git Operations (3 tools):** git_status, git_diff, git_log
4. **File I/O (3 tools):** read_text_file, write_text_file, list_directory

**Each tool returns structured Pydantic models:**
```python
class TypeCheckError(BaseModel):
    file: str
    line: int
    column: int
    message: str
    severity: Literal["error", "warning"]

class HoverResult(BaseModel):
    contents: str
    range: Range | None

class GitDiffResult(BaseModel):
    files_changed: int
    additions: int
    deletions: int
    hunks: list[DiffHunk]
```

**Model must understand:**
- Type systems and type checking (ty server LSP diagnostics)
- Linting rules (ruff violations)
- Test frameworks (pytest outcomes, fixtures, assertions)
- Git workflows (staging, commits, diffs, hunks)
- LSP protocol (locations, ranges, symbols, hierarchies)
- File paths and line/column positions
- Diagnostic severity levels

#### Evidence from Phases

**Phase 23 (ty integration):** Model parses LSP diagnostics with type errors
**Phase 24 (ruff + pytest):** Model understands linting violations and test failures
**Phase 27 (LSP + git):** Model navigates symbol hierarchies and git history

**Phase 27 validation:** 100% accuracy (40/40 queries) on comprehensive suite

**Key insight:** General-purpose language models lack this domain knowledge. Code-specific pretraining is not optional.

---

## Should-Have Requirements

*Significant effort to work around if missing - prefer models with all 3*

### S1. Multi-Turn Tool Calling Capacity

#### What It Means

The model must:
- Generate tool call → Receive result → Continue reasoning → Make next decision
- Maintain coherent state across multiple tool invocations
- Handle tool response tokens and integrate responses into ongoing reasoning
- Not "forget" previous tool results when making subsequent calls

#### Why It Matters

**Phase 22 Code Mode:**
```python
# Model must maintain context across 4 operations:
result = goto_definition("src/app.py", 15, 10, "UserService")  # 1. Call tool
if result.success:                                              # 2. Remember result
    loc = result.locations[0]                                   # 3. Access field
    print(f"Found at {loc.file}:{loc.line}")                   # 4. Use data
```

**Complex workflows require chaining:**
- Query: "Where is UserService defined and what references it?"
- Requires: `goto_definition()` → access result → `find_references()` → synthesize answer

#### Evidence from Testing

**Phase 27 validation (100% on 40-query suite):**
- Single-tool queries: 100% (5/5)
- Multi-step workflows: 100% (5/5) on curated test set

**Phase 27.5 honest audit (72% overall):**
- Cross-tool workflows: **0% accuracy (0/5)** on realistic queries
- Example failure: "Find all TODO comments and group by priority"
  - Model called grep correctly but failed to synthesize results

**Key insight:** Even 30B MoE struggles with complex multi-step reasoning. This capability requires BOTH model capacity AND explicit training.

**Why this is "Should-Have" not "Must-Have":**
- Single-turn tool calling works without this
- Can partially work around with better prompting
- But complex agent behaviors impossible without it

---

### S2. Structured Code Generation with Field Access

#### What It Means

The model must:
- Generate syntactically correct Python (not pseudocode or natural language)
- Follow calling conventions and type signatures precisely
- Access nested fields on Pydantic models (`result.errors[0].line`)
- Understand Python semantics (loops, conditionals, variable scope)

#### Why It Matters

**Typed tools return Pydantic models:**
```python
class TypeCheckResult(BaseModel):
    success: bool
    errors: list[TypeCheckError]
    error_count: int

# Model must generate this (Python code):
if result.error_count > 0:
    for error in result.errors:
        print(f"{error.file}:{error.line}: {error.message}")

# NOT this (natural language):
"The result shows 3 errors in the errors field"
```

#### Critical Discovery: This is TRAINED, not Innate

**Phase 23 baseline:**
- 0% field access rate
- Model calls tools but ignores results
- Returns generic answers without using structured data

**Phase 26 with 120 field access examples:**
- 90% field access rate
- 4 trained patterns: conditional, access, iteration, multi-step

**Phase 26.1 (5-bit vs 6-bit):**
- 5-bit: 92% overall accuracy, 90% field access
- 6-bit: 88% overall accuracy, 85% field access
- **5-bit superior despite lower precision** (32 quantization levels sufficient)

**Key insight:** Model must have capacity to LEARN these patterns through fine-tuning. Even 30B MoE needed explicit training.

**Why this is "Should-Have" not "Must-Have":**
- Can fall back to unstructured text responses
- Loses major benefit of typed tools but agent still functional
- But structured data is core value proposition

---

### S3. Hardware-Compatible Quantization

#### What It Means

**Target hardware:** Apple Silicon M1/M2/M3, 32 GB unified memory

**Requirements:**
- 5-bit quantized model must fit under ~20 GB (leaving 12 GB headroom for inference)
- Quantization must preserve LoRA fine-tuning signal
- Model must load and run efficiently on MLX framework

#### Quantization Threshold Discovery

**Critical finding:** Sharp threshold at 5-bit quantization

| Quantization | Levels | Accuracy | Disk Size | Status |
|--------------|--------|----------|-----------|--------|
| Float16 | N/A | 100% | 57 GB | Intermediate only |
| 8-bit | 256 | 100% | 30 GB | ✅ Preserves signal |
| 6-bit | 64 | 100% | 23 GB | ✅ Preserves signal |
| **5-bit** | **32** | **100%** | **19.5 GB** | ✅ **OPTIMAL** |
| 4-bit | 16 | 60% | 15 GB | ❌ **DESTROYS signal** |

**Phase 5c discovery:**
- 4-bit re-quantization during fusion destroyed LoRA deltas
- 13% of bytes changed but behavioral signal was erased
- Must dequantize to float16 → fuse → re-quantize to 5-bit+

**Phase 26.1 discovery:**
- **5-bit is SUPERIOR to 6-bit** in accuracy, speed, and size
- 5-bit: 92% accuracy, 2.53s avg generation, 19.5 GB
- 6-bit: 88% accuracy, 5.76s avg generation, 23.1 GB
- 6-bit triggers MLX memory warnings → 2.3x slower

**Why 5-bit works:**
- 32 quantization levels sufficient to represent LoRA perturbations
- Small weight deltas (±0.01) preserved through quantization
- 4-bit (16 levels) rounds away these deltas

#### Production Standard

**All Phase 26+ models use 5-bit quantization:**
- Phase 26: `fused_model_qwen3_phase26_5bit/` (19.5 GB, 92% accuracy)
- Phase 27: `fused_model_qwen3_phase27_5bit/` (20 GB, 100% accuracy)

**Commands:**
```bash
# Fuse to float16 first (preserves full precision)
uv run python -m mlx_lm.fuse \
  --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
  --adapter-path ./adapters_phase27 \
  --save-path ./fused_model_f16 \
  --dequantize

# Quantize to 5-bit (optimal balance)
uv run python -m mlx_lm.convert \
  --hf-path ./fused_model_f16 \
  --mlx-path ./fused_model_qwen3_phase27_5bit \
  --quantize \
  --q-bits 5
```

**Why this is "Should-Have" not "Must-Have":**
- Can use float16 or 8-bit if more memory available
- Can use cloud GPU if local hardware insufficient
- But local Apple Silicon deployment is core use case

---

## Nice-to-Have Requirements

*Helpful but can work without - evaluate trade-offs*

### N1. MoE Architecture (Speed Trade-off)

#### What It Means

**MoE advantage:**
- Fast inference (3B active vs 24B active)
- Specialized experts for different tasks
- Better parameter efficiency

**Dense disadvantage:**
- All parameters active every token
- 8x slower per token (estimated)
- No task specialization

#### Why It Matters for Interactive Agent

**Phase 27 production speed:**
- Qwen3-30B-A3B (MoE, 3B active): 2.90s average generation
- User experience: Nearly instant responses
- Enables iterative workflows

**Dense 24B estimate:**
- 8x more active parameters per token
- Estimated: 20-30s average generation
- User experience: Noticeable lag, breaks flow

#### Key Insight

**MoE is not required if dense model is large enough:**
- Dense 24B has sufficient capacity (likely)
- But speed difference is significant for UX
- For interactive coding agent, speed matters enormously

**Reframing:** This is about user experience, not capability.

---

### N2. Long Context (16K+ Usable)

#### What It Means

**Context window requirements:**
- System prompt: ~500 tokens (Code Mode instructions + tool stubs)
- User query: ~100-500 tokens
- Tool results: ~200-1000 tokens per tool
- Multi-turn: 3-5 exchanges = ~5K-10K tokens total

**Must be "usable" context:**
- Not just theoretical limit (many models degrade at long contexts)
- Strong attention mechanisms across full window
- Maintains coherence from beginning to end

#### Current State

**Most models now have this:**
- Qwen3-30B-A3B: 32K context window (actually usable)
- Devstral Small 2: 256K context window
- DeepSeek V3: 128K context window

**Phase 26 validation:**
- No degradation observed at 5K-10K token contexts
- Multi-step workflows work reliably
- System prompt (500) + 3 workflows (3,950) = 4,450 tokens typical

**Why this is "Nice-to-Have":**
- Most modern models exceed 16K requirement
- Can work with shorter context using summarization
- But longer context simplifies implementation

---

### N3. Multi-Step Reasoning (Can Be Trained)

#### What It Means

The model must:
- **Plan:** "User wants X → I need tools A, B, C in sequence"
- **Discriminate:** "This query needs a tool" vs "I can answer directly"
- **Synthesize:** "Result from tool A informs arguments to tool B"
- **Recover:** "Tool failed → try alternative approach"

#### Evidence: Trainable Capability

**Phase 5 discrimination training:**
- Before: Model called tools 97.5% of the time
- Added 50 direct-answer examples (32.8% of dataset)
- After: 100% accuracy (5/5) distinguishing tool vs direct

**Phase 26 field access training:**
- Before: 0% field access rate
- Added 120 field access examples (22% of dataset)
- After: 90% field access rate

**Key insight:** Base model needs capacity, but explicit training is what makes it work.

**Why this is "Nice-to-Have":**
- Can be trained if base model has capacity (M2)
- Phase 27 achieved 100% on curated test set
- But Phase 27.5 showed gaps remain in realistic scenarios

---

### N4. Proven MLX Ecosystem Support

#### What It Means

Model must work with:
- `mlx_lm.lora` - LoRA fine-tuning
- `mlx_lm.fuse` - Adapter fusion
- `mlx_lm.convert` - Quantization
- `mlx_lm.generate` - Inference

#### Known Issues

**mlx-vlm vs mlx-lm compatibility:**
- Some models require mlx-vlm for conversion
- mlx-vlm has different API and known bugs
- Qwen3 tokenizer issues in some contexts

**Devstral Small 2 risk:**
- Tekken tokenizer (131K vocab) - untested with MLX
- Multimodal model - may require mlx-vlm
- Known "G/C byte bug" in tokenization

**Verification before training:**
```bash
# Test basic inference
uv run mlx_lm.generate \
  --model mlx-community/Devstral-Small-2-5bit \
  --prompt "def factorial(n):" \
  --max-tokens 100

# Check for tokenization artifacts
# Look for: broken unicode, repeated tokens, garbage output
```

**Why this is "Nice-to-Have":**
- Most popular models work with MLX
- Can investigate and fix issues if needed
- But proven support saves 1-2 weeks debugging

---

## Evaluation: Devstral Small 2 (24B Dense)

### Profile

**Architecture:**
- 24B parameters (all active, dense model)
- Mistral 3 architecture family
- Tekken tokenizer (131K vocabulary)
- 256K context window
- Multimodal (text + vision)

**Performance:**
- SWE-bench Verified: **68%** (best open-weight model at this size)
- Code-specific pretraining
- Apache 2.0 license

**Deployment:**
- 5-bit MLX quantization: ~17 GB
- Fits in 32 GB unified memory (15 GB headroom)

### Must-Have Assessment

| Req | Status | Evidence | Notes |
|-----|--------|----------|-------|
| **M1: Tool tokens** | ✅ PASS | [TOOL_CALLS], [TOOL_RESULTS] etc. are single control tokens in vocabulary | Mistral 3 native format |
| **M2: Capacity** | 🟡 LIKELY PASS | 24B dense >> 7B dense (3.4x larger) | Untested but promising |
| **M3: Format compatibility** | ⚠️ NEEDS WORK | JSON format, not XML. All 1104 examples need reformatting | 2-3 days work |
| **M4: Code pretraining** | ✅ PASS | Code-specialized, SWE-bench 68% | Proven capability |

**M2 Analysis:**
- 7B dense failed conclusively (Phase 25b)
- 24B dense is 3.4x larger
- Open question: Is 3.4x enough to cross capability threshold?
- Extrapolation suggests "yes" but requires validation

**M3 Analysis:**
- Training data uses Qwen3 XML format with ChatML template (actually 3 mixed formats in the 1104 examples: Code Mode XML, JSON-in-tags from Phase 8, and direct XML from domain examples)
- Devstral expects Mistral JSON format with different template
- Must reformat all 1104 examples + update format_prompt()
- Runtime infrastructure also hardcodes Qwen3 format: `prompt_utils.py` (tool call extraction), `stubs.py` (system prompt examples), `factory.py` (stop sequences), `tool_call_parser.py` (4 Qwen3-specific parsers), `tool_calling_templates.py` (training data generator)
- Estimate: 2-3 days minimum for data reformatting, 6-9 days total including runtime code changes

### Should-Have Assessment

| Req | Status | Evidence | Notes |
|-----|--------|----------|-------|
| **S1: Multi-turn** | 🟡 LIKELY | Base model designed for agentic workflows | Needs validation |
| **S2: Field access** | ❓ UNKNOWN | Requires training, but capacity likely sufficient | Phase 26 approach should work |
| **S3: Quantization** | ✅ PASS | 17 GB at 5-bit, fits in 32 GB with 15 GB headroom | Meets requirement |

**S1 Analysis:**
- Mistral 3 marketed for agentic use cases
- 24B parameters should handle multi-turn state
- But Phase 27.5 showed even 30B MoE struggles with complex workflows

**S2 Analysis:**
- Phase 26 proved this is trainable (0% → 90%)
- 24B likely has capacity to learn patterns
- Would use same 120-example training approach

### Nice-to-Have Assessment

| Req | Status | Evidence | Notes |
|-----|--------|----------|-------|
| **N1: MoE** | ❌ FAIL | Dense 24B, all parameters active | Inference ~8x slower |
| **N2: Long context** | ✅ PASS | 256K (far exceeds 16K requirement) | Luxury feature |
| **N3: Multi-step** | 🟡 LIKELY | Needs training but capacity likely sufficient | Proven trainable in Phase 26 |
| **N4: MLX ecosystem** | ⚠️ RISK | Known tokenizer bugs, mlx-vlm conversion issues | Needs testing |

**N1 Critical Analysis - Speed Impact:**
```
Current: Qwen3-30B-A3B (MoE, 3B active)
→ 2.90s average generation time
→ User experience: Nearly instant

Devstral: 24B dense (24B active)
→ 8x more active parameters
→ Estimated: 20-30s average generation time
→ User experience: Noticeable lag, breaks iterative flow
```

**For interactive coding agent, this is a significant downgrade.**

**N4 Risk Analysis:**
- Tekken tokenizer (131K vocab) - untested with MLX
- Known "G/C byte bug" in Mistral tokenization (unresolved)
- Multimodal model may require mlx-vlm (compatibility unclear)
- llama.cpp reports tool call reliability issues with Mistral 3

### Positive Finding: Model-Agnostic Runtime

**Pydantic AI handles format translation:**
- Core agent runtime (`toolset.py`, `monty_runner.py`, `adapter.py`) is model-agnostic
- Pydantic AI abstracts tool-calling format differences
- ACP/server mode would work unchanged with Devstral
- Only local mode and training pipeline require format changes

**Impact:** Reduces risk for server-mode deployment. The 6-9 day estimate applies primarily to local model inference and training data reformatting.

### Key Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **1. Inference speed** | HIGH | 8x slower = 20-30s vs 2.9s. Major UX downgrade for interactive agent. |
| **2. MLX tokenization** | MEDIUM | Known "G/C byte bug". Test thoroughly before committing. |
| **3. Training data + runtime reformatting** | HIGH | Data: 3 mixed formats in 1104 examples (2-3 days). Runtime: prompt_utils, stubs, factory, stop sequences, parsers all hardcode Qwen3 format (4-6 days). Total: 6-9 days minimum. |
| **4. mlx-vlm compatibility** | MEDIUM | Multimodal model may require mlx-vlm (different API, known bugs). |
| **5. Tool call reliability** | MEDIUM | llama.cpp reports issues with Mistral 3 tool calling. Needs validation. |
| **6. Capacity unknown** | HIGH | 24B dense untested. Could still fail like 7B. No guarantee. |
| **7. Code Mode is Punie-specific** | HIGH | Punie's "Code Mode" (Python wrapped in execute_code) is custom, not a standard. Devstral has no base model priors to build on. Either Devstral must learn it from scratch OR Punie abandons Code Mode for Mistral's native function-calling. |
| **8. Multi-turn tool-result format** | MEDIUM | Multi-turn examples using `<tool_response>` face same single-token issue as Phase 25 Flaw #1. Need Mistral-native tool-result convention. |
| **9. Runtime infrastructure complexity** | MEDIUM | See `scripts/convert_to_qwen25_format.py` (340 lines) as template - but this only covers data, not all runtime code changes. |

### Recommended Testing Protocol

**Before any training investment:**

```bash
# 1. Download 5-bit MLX model
uv run huggingface-cli download \
  mlx-community/Devstral-Small-2-5bit \
  --local-dir ./devstral_5bit

# 2. Test with mlx_lm.generate (not mlx-vlm)
uv run python -m mlx_lm.generate \
  --model ./devstral_5bit \
  --prompt "def factorial(n):" \
  --max-tokens 100

# Does it work? Any errors? Tokenization artifacts?

# 3. Measure actual inference latency
uv run python scripts/benchmark_devstral.py
# Target: <10s per generation (anything slower is UX problem)

# 4. Test zero-shot tool calling with Mistral format
uv run python scripts/test_devstral_tool_calling.py
# Use [TOOL_CALLS] format, no fine-tuning

# 5. Small-scale LoRA fine-tuning (100 examples)
# Convert 100 examples to Mistral format
# Note: scripts/convert_to_qwen25_format.py (340 lines) can serve as template
# for building Mistral format converter (handles XML→JSON conversion)
# Train 50 iterations
# Test accuracy on 10-query suite
# If <80% accuracy → abandon, capacity insufficient
```

**If steps 1-5 pass:**
- Proceed with full dataset reformatting (1104 examples)
- Train Phase 28 with Devstral base model
- Compare: 24B dense vs 30B MoE accuracy and speed

**If any step fails:**
- Stay with Qwen3-30B-A3B production model
- Document learnings for future model selection

### Should We Try Devstral?

**Pros:**
- ✅ Best open-weight SWE-bench score at this size (68%)
- ✅ Apache 2.0 license (fully permissive)
- ✅ Fits in 32 GB (17 GB quantized)
- ✅ 3.4x larger than failed 7B (likely crosses threshold)
- ✅ Native tool calling tokens (Mistral format)

**Cons:**
- ❌ 8x slower inference (20-30s vs 2.9s) - **major UX downgrade**
- ❌ Untested capacity (could fail like 7B)
- ⚠️ Known tokenization issues
- ⚠️ mlx-vlm compatibility unclear
- ⚠️ 2-3 days reformatting work
- ⚠️ llama.cpp tool calling issues reported

**Verdict:** **Worth testing if speed impact is acceptable**

**Recommended approach:**
1. Run 5-step testing protocol (1-2 days)
2. If latency <10s AND zero-shot tool calling works → proceed to small-scale fine-tuning
3. If latency >15s OR tokenization issues → abandon, speed unacceptable
4. If small-scale accuracy <80% → abandon, capacity insufficient

**Alternative:** Wait for Qwen3-Coder-20B-MoE (if released) or DeepSeek-V3-Code with verified MLX support.

---

## Phase 43 Evaluation: Qwen3-14B Dense

### Profile

**Architecture:**
- 14B parameters (all active, dense model)
- Qwen3 model family (same tokenizer, same tool tokens)
- No Coder variant exists at 14B — general Qwen3 weights
- Standard Qwen3 context window (32K)

**Why this matters:**
- Phase 40 proved 8B dense (8B active) fails vs 30B MoE (3B active)
- 14B is the cleanest test: same family, more params, still dense
- Either confirms MoE routing is structurally required, or shows total params matter more

### Must-Have Assessment

| Req | Status | Evidence | Notes |
|-----|--------|----------|-------|
| **M1: Tool tokens** | ✅ PASS | Qwen3 family — same `<tool_call>`/`<tool_response>` single tokens | No reformatting needed |
| **M2: Capacity** | ❓ UNKNOWN | 14B > 8B (failed) but < 30B MoE (succeeded). Phase 43b answers this. | The key experiment |
| **M3: Format compat** | ✅ PASS | Same Qwen3 ChatML template. Zero reformatting. | Direct drop-in |
| **M4: Code pretraining** | 🟡 PARTIAL | General Qwen3-14B, not Coder variant (no 14B Coder exists) | Weaker code priors than production |

### Phase 43b Success Criteria

| Outcome | Score | Interpretation |
|---------|-------|---------------|
| Clear success | ≥80% | Hypothesis A wins: total params cross threshold at 14B |
| Ambiguous | 50-79% | Mixed: capacity and routing both contribute |
| Likely MoE required | <50% | Hypothesis B: MoE routing structurally necessary |
| Strong MoE confirmed | ~18% | Same failure mode as Phase 40; 14B == 8B behavior |

---

## Updated Comparison Table

| Requirement | Qwen3-30B-A3B (Production) | Qwen3-8B (Failed Ph40) | Qwen3-14B (Ph43b) | Devstral-24B (Candidate) |
|-------------|----------------------------|-----------------------|-------------------|--------------------------|
| **M1: Tool tokens** | ✅ Single tokens | ✅ Single tokens | ✅ Single tokens | ✅ Single tokens |
| **M2: Capacity** | ✅ 30B MoE (3B active) | ❌ 8B dense (failed) | ❓ 14B dense (testing) | 🟡 24B dense (untested) |
| **M3: Format compat** | ✅ Qwen3 ChatML | ✅ Qwen3 ChatML | ✅ Qwen3 ChatML | ⚠️ Mistral JSON (needs work) |
| **M4: Code pretraining** | ✅ Qwen3-Coder | 🟡 Qwen3 (general) | 🟡 Qwen3 (no Coder) | ✅ Code-specialized |
| **S1: Multi-turn** | ✅ Strong (but gaps in 27.5) | ❌ 18.5% total | ❓ Untested | 🟡 Likely (needs validation) |
| **S2: Field access** | ✅ 90% (trained) | ❌ 0% | ❓ Unknown (trainable) | ❓ Unknown (trainable) |
| **S3: Quantization** | ✅ 20 GB (5-bit) | ✅ 5.3 GB (5-bit) | ✅ ~9 GB (5-bit, est.) | ✅ 17 GB (5-bit) |
| **N1: MoE** | ✅ ~2-5s gen time | ❌ Dense (~2s est.) | ❌ Dense (~1-2s est.) | ❌ Dense (est. 20-30s) |
| **N2: Long context** | ✅ 32K usable | ✅ 32K | ✅ 32K | ✅ 256K |
| **N3: Multi-step** | ✅ 82.4% (trained) | ❌ 18.5% | ❓ Unknown | 🟡 Likely (trainable) |
| **N4: MLX ecosystem** | ✅ Proven | ✅ Proven | ✅ Qwen3 family | ⚠️ Known issues |
| **Score** | **11/11 ✅** | **4/11 ❌** | **~7-8/11 ❓** | **~6-7/11 🟡** |
| **Phase 33b accuracy** | **82.4%** | **18.5% (Ph40)** | **Pending Ph43b** | **Untested** |
| **Phase 27.5 honest** | **72% (29/40)** | **N/A** | **N/A** | **Untested** |

---

## What Future Models Would Work?

*Updated with real candidates, not hypotheticals*

### Tier 1: Would Definitely Work (If They Existed)

**1. Qwen3-Coder-20B-MoE**
- ✅ MoE architecture (fast inference)
- ✅ Same tool tokens as current model
- ✅ No training data reformatting needed
- ✅ Code pretraining
- **Status:** Doesn't exist yet
- **Estimate:** 15 GB quantized, 85-90% accuracy, 2-3s generation
- **If released:** Immediate upgrade candidate

**2. Qwen4-Coder-14B-MoE** (hypothetical future)
- ✅ If MoE architecture
- ✅ If has tool calling tokens
- ✅ Updated code pretraining
- **Status:** Doesn't exist
- **Unknown:** Whether 14B MoE crosses capability threshold
- **Would need:** Zero-shot validation before training

### Tier 2: Worth Testing (Real Models)

**1. Devstral Small 2 (24B dense)** - See full evaluation above
- **Status:** Available now
- **Pros:** SWE-bench 68%, Apache 2.0, fits in 32 GB
- **Cons:** 8x slower, known tokenization issues, capacity unproven
- **Recommendation:** Test if speed impact acceptable

**2. DeepSeek-V3-Code** (hypothetical variant)
- **Status:** DeepSeek-V3 exists (671B MoE), no code variant announced
- ✅ MoE architecture (fast inference)
- ❓ Need to verify: Tool calling tokens, code specialization
- ❓ Need to verify: MLX support, quantization
- **If code variant released:** Promising candidate but large (likely 40+ GB quantized)

**3. Qwen3-Coder-14B-Dense** (if exists)
- ✅ Same tool tokens (no reformatting)
- ✅ Code pretraining
- ❓ Unknown: 14B dense sufficient?
- **Status:** Not announced
- **Would need:** Validation that 14B crosses threshold

### Tier 3: Probably Wouldn't Work

**1. Any dense model <14B**
- Phase 25b proved 7B fails conclusively
- Extrapolation: ~14-20B minimum for dense architecture
- **Avoid:** 7B, 8B, 10B dense models

**2. Code models without tool calling tokens**
- Phase 25 showed format conversion breaks training
- Phase 26.1 showed wrong format = 60-point accuracy drop
- **Could work but:** Requires reformatting + high risk

**3. General-purpose models** (not code-specialized)
- Lack domain knowledge for: type checking, linting, testing, LSP, git
- Would need extensive fine-tuning on code patterns
- **Avoid:** Llama 3, Claude Code base, GPT-4 base

### Testing Protocol for Any New Model

**Before committing to training:**

1. **Tokenizer check** (5 minutes)
   ```python
   vocab = tokenizer.get_vocab()
   assert "<tool_call>" in vocab or "[TOOL_CALLS]" in vocab
   ```

2. **MLX compatibility check** (30 minutes)
   - Download model
   - Test inference with mlx_lm.generate
   - Check for tokenization artifacts

3. **Latency benchmark** (1 hour)
   - Measure generation time on 10 queries
   - Target: <10s per generation
   - If >15s: Consider unacceptable for UX

4. **Zero-shot tool calling** (2 hours)
   - Test base model with tool calling prompt (no fine-tuning)
   - If 0% accuracy: Likely lacks capacity
   - If >20%: Promising, proceed to step 5

5. **Small-scale fine-tuning** (1 day)
   - Convert 100 examples to model's format
   - Train 50 iterations
   - Test on 10-query validation set
   - Target: >80% accuracy
   - If <60%: Abandon, capacity insufficient

6. **If steps 1-5 pass:** Proceed with full training

**Total time before commitment:** 2-3 days

---

## Recommendations for Model Selection

### Must-Have Checklist (All 4 Required)

✅ **M1: Native tool calling tokens** - Verify in tokenizer vocabulary FIRST
✅ **M2: Sufficient capacity** - MoE OR 14-20B+ dense minimum
✅ **M3: Format compatibility** - Must match or reformat all 1104 examples
✅ **M4: Code pretraining** - 100B+ tokens of code corpus

**If ANY of these are missing → Do not attempt**

### Should-Have Checklist (Prefer 2+)

🟢 **S1: Multi-turn capacity** - Test with zero-shot multi-step query
🟢 **S2: Field access trainability** - 24B+ likely sufficient
🟢 **S3: Hardware compatibility** - 5-bit quantized <20 GB target

**Can work without these but requires significant effort**

### Nice-to-Have Checklist (Evaluate Trade-offs)

⭐ **N1: MoE architecture** - 8x speed difference for UX
⭐ **N2: Long context** - Most models have 32K+ now
⭐ **N3: Multi-step reasoning** - Can be trained if capacity sufficient
⭐ **N4: MLX ecosystem** - Saves 1-2 weeks debugging

**Helpful but can work without - evaluate on case-by-case basis**

---

## Conclusion

**It's not just about size** - Punie requires a specific combination of:
- **Architecture:** MoE specialization OR 14-20B+ dense parameters
- **Tokenization:** Native tool calling tokens (single tokens, not spans)
- **Pretraining:** Deep code understanding (100B+ tokens)
- **Format:** Training data must match model's native template
- **Quantization:** 5-bit minimum for LoRA preservation (32 levels)

**Qwen3-Coder-30B-A3B is the proven production model:**
- 100% accuracy on Phase 27 validation (40/40 queries)
- 72% accuracy on Phase 27.5 honest audit (29/40 queries)
- 2.90s average generation time (excellent UX)
- 19.5 GB quantized (fits in 32 GB unified memory)
- 11/11 requirements met

**Dense models <14B lack capacity:** Phase 25b conclusively proved 7B fails with perfect setup.

**Format consistency is most impactful:** Phase 26.1 showed 60-point accuracy drop from wrong format.

**Quantization threshold is sharp:** 5-bit (32 levels) preserves LoRA signal, 4-bit (16 levels) destroys it.

**Future model selection:**
- Look for MoE code models with native tool calling support
- Avoid dense models <14B
- Avoid general-purpose models without code specialization
- Test with 5-step protocol before committing to training (2-3 days)

**Devstral Small 2:** Worth testing if speed impact acceptable, but 8x slower inference is major UX concern.

---

## References

### Phases

- **Phase 5:** Tool discrimination (100% accuracy with 244 examples)
- **Phase 22:** Code Mode introduction (perplexity 1.826)
- **Phase 23:** ty integration (first typed tool, 0% field access baseline)
- **Phase 25:** 7B experiment (failed, 35% accuracy, 5 setup flaws identified)
- **Phase 25b:** 7B conclusive retest (all flaws fixed, identical failure, 0% tool calling)
- **Phase 26:** Field access training (92% accuracy with 953 examples, 90% field access)
- **Phase 26.1:** 5-bit vs 6-bit quantization (5-bit superior: 92% vs 88%, 2.53s vs 5.76s)
- **Phase 27:** LSP + git tools (1104 examples, 14 tools, 100% on original validation script - later audited to 72% honest accuracy in Phase 27.5)
- **Phase 27.5:** Honest audit (72% overall on 40 queries, 0/5 cross-tool workflows on realistic queries)

### Key Documents

- `docs/flywheel.md` - "30B MoE minimum for tool calling"
- `docs/research/prompt-format-consistency.md` - Phase 26.1 format analysis
- `CLAUDE.md` - Project standards including prompt formatting requirement
- `MEMORY.md` - Phase summaries and critical learnings

### External References

- **Devstral Small 2:** https://huggingface.co/mistralai/Devstral-Small-2-2503
- **Qwen3-Coder:** https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct
- **MLX Framework:** https://github.com/ml-explore/mlx
- **SWE-bench Verified:** https://www.swebench.com/
