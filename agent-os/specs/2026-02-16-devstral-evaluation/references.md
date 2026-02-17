# References for Devstral Small 2 Evaluation

## Phase 27 Baseline (Current Production Model)

**Location:** `fused_model_qwen3_phase27_5bit/`

**Performance:**
- Accuracy: 100% (40/40 queries)
- Speed: 2.90s average generation
- Size: 20 GB (5-bit quantized)
- Memory: 19.55 GB

**Training Data:**
- 1104 examples (993 train, 111 valid)
- 500 iterations, batch size 1, learning rate 1e-4
- 8 LoRA layers
- Val loss: 3.270 → 0.395 (88% reduction)

**Documentation:**
- `docs/phase27-complete-implementation.md` - Full implementation guide
- `docs/phase27-deployment-summary.md` - Deployment reference
- `scripts/test_phase27_validation.py` - 40-query validation suite

**Validation Categories (all 5/5):**
1. Direct answers - Concept questions
2. Existing LSP - goto_definition, find_references
3. New LSP - hover, document_symbols, workspace_symbols
4. Git tools - status, diff, log
5. Existing tools - ruff_check, pytest_run, typecheck
6. Field access - Accessing structured result fields
7. Cross-tool workflows - Multi-step reasoning
8. Discrimination - Tool vs direct answer

**Relevance:** This is the baseline Devstral must match or exceed. Gate 5 requires ≥85% (34/40) on the same validation suite.

---

## Phase 25 Learnings (7B Experiment Failure)

**Location:** `docs/diary/2026-02-15-phase25-7b-experiment-failed.md`

**Result:** 7B Qwen2.5-Coder scored 35% (7/20), 0% on tool calling (0/13)

**Critical Finding:** Multi-token tool delimiters corrupt training data
- Qwen3 has `<tool_response>` as single token (ID 151665)
- Qwen2.5 tokenizes as ~5 subword pieces
- **Impact:** 58% of training data (398/685 examples) corrupted

**5 Setup Flaws Identified:**
1. **CRITICAL:** `<tool_response>` token doesn't exist in Qwen2.5
2. **CRITICAL:** Tool call format mismatch (XML vs JSON)
3. **MODERATE:** Two conflicting formats in training data
4. **MODERATE:** Test script missing tool instructions
5. **MINOR:** eos_token_id mismatch

**Key Lesson:** Tokenizer verification is THE most critical first step. Multi-token delimiters make training infeasible.

**Why This Matters for Devstral:**
- **Gate 0 addresses this risk first** by checking if `[TOOL_CALLS]`, `[/TOOL_CALLS]`, `[TOOL_RESULTS]`, `[/TOOL_RESULTS]` are single tokens
- Mistral tokenizer may be different from Qwen
- Must verify before any training investment

**Quote:**
> "4-bit has only 16 discrete values per group → rounds away small LoRA perturbations"

**Relevance:** Gate 0 prevents repeating this expensive mistake.

---

## Phase 26 Field Access Training

**Location:** `docs/diary/2026-02-15-phase26-field-access-training.md`

**Result:** 92% accuracy (5-bit) → +68% improvement from Phase 23 baseline (24%)

**Key Finding:** 5-bit quantization sufficient for LoRA fine-tuning
- 32 quantization levels preserve LoRA signal
- 6-bit is superior but 5-bit is faster and smaller
- 5-bit: 19.55 GB, 2.53s avg generation
- 6-bit: 23.11 GB, 5.76s avg generation

**Quantization Thresholds Discovered:**
- 4-bit (16 levels): ❌ Destroys LoRA signal
- **5-bit (32 levels): ✅ Preserves LoRA signal**
- 6-bit (64 levels): ✅ Preserves but slower
- 8-bit (256 levels): ✅ Preserves but larger

**Why This Matters for Devstral:**
- Gate 1 should target 5-bit quantization (proven optimal)
- Gate 4 can use 5-bit for small-scale LoRA test
- Gate 5 should quantize final model to 5-bit

**Relevance:** Guides quantization choice for all gates. 5-bit is the proven sweet spot.

---

## Phase 26.1: Prompt Format Consistency

**Location:** `docs/research/prompt-format-consistency.md` (referenced in CLAUDE.md)

**Critical Discovery:** Train/test format mismatch caused 60-point accuracy drop (28% → 88%)

**Problem:**
- Training data uses `tokenizer.apply_chat_template()` (ChatML format)
- Validation script used plain text: `f"User: {query}\nAssistant:"`
- Format mismatch → model couldn't apply learned patterns

**Solution:** Always use `punie.agent.prompt_utils.format_prompt()`

**Why This Matters for Devstral:**
- Must use Mistral's chat template consistently
- Validation scripts must match training format exactly
- All gates should use proper chat template formatting

**Relevance:** Critical for Gates 3-5. Consistent prompt formatting is non-negotiable.

---

## Minimum Model Requirements Analysis

**Location:** `docs/research/minimum-model-requirements.md`

**9 Identified Risks:**
1. Tokenizer differences (addressed by Gate 0)
2. Tool-calling format - Mistral JSON vs Qwen XML (Gates 3-4)
3. Speed differences (Gate 2)
4. LoRA compatibility (Gate 4)
5. Tool-calling capability (Gate 3)
6. Training convergence (Gate 5)
7. Accuracy (Gate 5)
8. Code quality (Gate 5)
9. MLX compatibility (Gate 1)

**Analysis Framework:**
- Each risk has impact (Critical/High/Medium/Low)
- Each risk has likelihood (High/Medium/Low)
- Prioritized for gated evaluation

**Relevance:** This analysis shaped the 5-gate structure. Each gate addresses specific risks in order of cost.

---

## Mistral Tool-Calling Format

**Official Documentation:** Mistral 3 uses `[TOOL_CALLS]` + JSON format

**Format Example:**
```json
[TOOL_CALLS]
[{"name": "read_text_file", "arguments": {"path": "src/foo.py"}}]
[/TOOL_CALLS]
```

**Contrast with Qwen3:**
Qwen3 uses `<tool_call>` + XML format:
```xml
<tool_call>
<function=read_text_file>
<parameter=path>src/foo.py</parameter>
</function>
</tool_call>
```

**Conversion Requirements:**
- Tag format: `<tool_call>` → `[TOOL_CALLS]`
- Structure: XML → JSON
- Array: Single tool → Array of tools (even if only 1)
- Parameter names: May need to match Mistral conventions

**Why This Matters:**
- Gate 4 requires converting 100 examples to Mistral format
- Gate 5 requires converting all 1104 examples
- Format converter must be thoroughly tested

**Relevance:** Critical for Gates 4-5. Incorrect conversion = training on corrupted data.

---

## Phase 23 Typed Tools Infrastructure

**Location:** `docs/diary/2026-02-15-phase23-task11-validation.md`

**Result:** 73.3% (11/15) with **0% field access (0/4)** → Led to Phase 26

**Gap Identified:** Model called tools but never accessed result fields
- Example: Called `typecheck()` but never checked `result.error_count`
- Root cause: Never trained on field access patterns

**Why This Matters for Devstral:**
- Phase 27 training data includes field access examples
- Gate 5 must validate field access (category 6 in validation suite)
- Mistral format must preserve field access patterns

**Relevance:** Ensures Devstral learns the full typed tools workflow, not just tool calling.

---

## MLX Quantization and Fusion Patterns

**Phase 5c Documentation:** `MODEL_PERFORMANCE_TRACKER.md` - Phase 5c section

**Proven Fusion Pattern:**
1. Fuse to float16 first (preserves full precision):
   ```bash
   uv run python -m mlx_lm.fuse \
     --model base_model \
     --adapter-path adapters \
     --save-path fused_f16 \
     --dequantize
   ```

2. Then quantize to target bit depth:
   ```bash
   uv run python -m mlx_lm.convert \
     --hf-path fused_f16 \
     --mlx-path fused_5bit \
     --quantize \
     --q-bits 5
   ```

**Why Float16 First:**
- Prevents re-quantization during fusion
- Preserves LoRA delta signal
- Allows clean quantization to target bit depth

**Why This Matters for Devstral:**
- Gate 4 and Gate 5 must use this pattern
- Direct 4-bit → 4-bit fusion destroys LoRA signal (Phase 5c lesson)

**Relevance:** Critical for Gates 4-5. Use proven fusion pattern.

---

## Training Data Statistics (Phase 27)

**Location:** `data/phase27_merged/`

**Distribution:**
- 1104 total examples (993 train, 111 valid)
- 100% have system messages
- ~37% are multi-turn dialogues
- ~33% have preambles
- Tool coverage:
  - LSP tools: ~30%
  - Git tools: ~18%
  - Typed tools (ruff, pytest, typecheck): ~24%
  - Field access: ~22%
  - Direct answers: ~18%

**Format (Qwen3):**
```python
{
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."},
    {"role": "tool", "content": "...", "name": "tool_name"}
  ]
}
```

**Why This Matters for Devstral:**
- Gate 4: Convert 100 examples (maintain distribution)
- Gate 5: Convert all 1104 examples (preserve balance)
- Must map Qwen roles to Mistral roles
- Must preserve multi-turn structure

**Relevance:** Guides conversion strategy for Gates 4-5.

---

## Summary

This evaluation builds on:
- **Phase 27** - The baseline to match (100% accuracy)
- **Phase 25** - Lessons on tokenizer verification (Gate 0)
- **Phase 26** - Quantization best practices (5-bit optimal)
- **Phase 26.1** - Prompt format consistency (critical)
- **Typed tools** - Field access patterns (must preserve)
- **MLX patterns** - Proven fusion workflow (use always)

All references inform the gated evaluation approach, ordered by cost and risk.
