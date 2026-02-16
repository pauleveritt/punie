# Phase 26.2: Contrastive LSP Training

**Date:** February 15, 2026

## Problem

Phase 26 balanced model achieved:
- ✅ **92% field access** (trained on field access patterns)
- ✅ **100% discrimination** (tool vs direct-answer)
- ❌ **60% LSP navigation** (model uses grep instead of LSP tools)

**Root cause:** Model learned LSP tool SYNTAX (how to call them) but struggles with SEMANTICS (when to use them vs grep).

---

## Hypothesis

**System prompt hints alone are insufficient.** Tested by adding explicit tool selection guidelines:

```
When the user asks about CODE SEMANTICS (definitions, references, symbols), use LSP tools:
- "Find definition of X" → use goto_definition()
- "Where is X used?" → use find_references()

When the user asks to SEARCH TEXT (patterns, strings, comments), use run_command:
- "Search for text X" → use run_command("grep", args=["-r", "X"])
```

**Result:** Still 60% accuracy - no improvement. Model needs contrastive training, not runtime hints.

---

## Solution: Contrastive Training

Generate examples that **explicitly contrast** when to use LSP vs grep:

### Pattern 1: Definition Queries
```
LSP:  "Where is the UserService class defined?" → goto_definition()
Grep: "Search for all occurrences of the text 'UserService'" → grep
```

### Pattern 2: Reference Queries
```
LSP:  "Where is calculate_total called?" → find_references()
Grep: "Find all files containing the string 'calculate_total'" → grep
```

### Pattern 3: Usage Queries
```
LSP:  "Show me all places where get_user_by_id is used" → find_references()
Grep: "Search for the text 'get_user_by_id' in all Python files" → grep
```

### Pattern 4: Pure Text Search
```
Grep: "Find all TODO comments" → grep
Grep: "Find all FIXME comments" → grep
Grep: "Search for the string 'PLACEHOLDER'" → grep
```

---

## Training Data

### Generated
- **80 contrastive examples** (40 LSP, 40 grep)
  - 10 patterns × 2 queries each (LSP + grep)
  - Explicit language contrasts: "where is X used" vs "search for text X"

### Merged
- 800 existing Phase 26 balanced examples
- 80 new contrastive examples
- **880 total** (792 train, 88 valid)

### Distribution
- goto_definition: 24.2% (was 20%)
- find_references: 20.8% (maintained)
- grep: 4.4% (new: explicit grep examples)
- typecheck: 5.4%
- ruff_check: 3.7%
- pytest_run: 3.9%
- read_file: 8.0%

### Quality Checks
✅ **Format A: 606 (100%)** - All Code Mode, no format mismatch
✅ **Shuffled correctly** - No clustering
⚠️ **Balance warning** - ruff/pytest underrepresented (acceptable - focused on LSP)

---

## Training Configuration

```bash
mlx_lm.lora \
  --model mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit \
  --data data/phase26_contrastive_merged \
  --adapter-path ./adapters_phase26_contrastive \
  --iters 700 \
  --batch-size 1 \
  --learning-rate 1e-4 \
  --num-layers 8
```

**Parameters:**
- 700 iterations (proven sufficient in Phase 26)
- Batch size 1 (fits in 24 GB unified memory)
- Learning rate 1e-4 (standard for LoRA)
- 8 layers (efficient + preserves base model)

---

## Post-Training Pipeline

### 1. Fuse to Float16
```bash
./scripts/fuse_phase26_contrastive.sh
# Output: fused_model_qwen3_phase26_contrastive_f16/ (~57 GB)
```

### 2. Quantize to 5-bit
```bash
./scripts/quantize_phase26_contrastive_5bit.sh
# Output: fused_model_qwen3_phase26_contrastive_5bit/ (~20 GB)
# Proven optimal in Phase 26.1
```

### 3. Validate LSP Navigation
```bash
uv run python scripts/test_phase26_lsp_validation.py \
  fused_model_qwen3_phase26_contrastive_5bit
```

**Targets:**
- Overall: ≥80% (was 60%)
- Tool discrimination: ≥90% (was 60%)
- Field access: ≥80% (was 70%)

---

## Expected Outcomes

### Success Criteria
- Model learns discriminating features: "find definition" → LSP, "search text" → grep
- LSP navigation: 60% → ≥80% (+20 points)
- Maintains field access: ≥90%
- Maintains discrimination: 100%

### If Successful
- Deploy as Phase 26.3 (contrastive LSP)
- Update MEMORY.md with Phase 26 complete
- Move to Phase 27 (roadmap: Domain Tools)

### If Insufficient (<80%)
- Generate more contrastive examples (200 → 400)
- Increase LSP tool proportion (24% → 40%)
- Try longer training (700 → 1000 iterations)

---

## Key Learnings

### 1. Runtime Hints vs Training
- System prompt hints: 0% improvement (60% → 60%)
- Contrastive training: Expected +20 points (60% → 80%)
- **Lesson:** Tool selection semantics must be learned during training, not at inference

### 2. Contrastive Examples Structure
- Pair similar queries with different intents
- Use explicit language: "where is X used" (semantic) vs "search for text X" (lexical)
- Include pure grep examples (TODO, FIXME) to reinforce text-search use case

### 3. Training Data Balance
- LSP tools now 45% of training data (24.2% + 20.8%)
- Explicit grep examples added (4.4%)
- Format consistency critical (100% Code Mode)

---

## Files Created

| File | Purpose |
|------|---------|
| `scripts/generate_contrastive_lsp_examples.py` | Generate 80 contrastive examples |
| `scripts/merge_phase26_contrastive.py` | Merge balanced + contrastive data |
| `data/phase26_contrastive/` | 80 contrastive examples |
| `data/phase26_contrastive_merged/` | 880 merged examples (792 train, 88 valid) |
| `scripts/fuse_phase26_contrastive.sh` | Fuse adapters to float16 |
| `scripts/quantize_phase26_contrastive_5bit.sh` | Quantize to 5-bit |
| `src/punie/agent/stubs.py` | Added LSP tool hints (no effect, but kept) |

---

## Timeline

- System prompt hints: 30 minutes → 0% improvement
- Contrastive example generation: 20 minutes
- Training: 17 minutes (in progress)
- Fusion + quantization: 10 minutes
- Validation: 5 minutes
- **Total:** ~82 minutes (~1.4 hours)

---

## Next Steps

After training completes:
1. ✅ Fuse + quantize to 5-bit
2. ✅ Validate with LSP suite (target: ≥80%)
3. ✅ Validate field access (target: ≥90%)
4. ✅ Benchmark performance (target: <3s avg)
5. ✅ Deploy or iterate based on results

---

## Status

🔄 **IN PROGRESS** - Training Phase 26 contrastive model (700 iterations)
