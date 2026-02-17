# Devstral Small 2 Evaluation - Implementation Plan

## Context

**Goal:** Evaluate if Devstral Small 2 (Mistral-based) can replace Qwen3-30B-A3B as Punie's inference model while maintaining Phase 27's 100% accuracy.

**Approach:** Gated evaluation with 5 sequential gates ordered by cost (cheapest first). Each gate has clear pass/fail criteria. Stop immediately on any failure per decision matrix.

**Pre-commitment cost:** 4-7 hours across Gates 0-4
**Full conversion (Gate 5):** 6-9 days if all gates pass

**Baseline to match:**
- Model: Qwen3-30B-A3B (Phase 27)
- Accuracy: 100% (40/40 queries)
- Speed: 2.90s average generation
- Size: 20 GB (5-bit quantized)

---

## Gate 0: Tokenizer Verification (~5 min)

**Purpose:** Verify Devstral tokenizer has single-token delimiters for tool calls. Multi-token delimiters corrupt training data (Phase 25 lesson).

**Steps:**

1. Download Devstral tokenizer only (no model weights):
   ```bash
   uv run python -c "
   from transformers import AutoTokenizer
   tokenizer = AutoTokenizer.from_pretrained('mistralai/Devstral-Small-2')
   print(f'[TOOL_CALLS]: {tokenizer.encode(\"[TOOL_CALLS]\", add_special_tokens=False)}')
   print(f'[/TOOL_CALLS]: {tokenizer.encode(\"[/TOOL_CALLS]\", add_special_tokens=False)}')
   print(f'[TOOL_RESULTS]: {tokenizer.encode(\"[TOOL_RESULTS]\", add_special_tokens=False)}')
   print(f'[/TOOL_RESULTS]: {tokenizer.encode(\"[/TOOL_RESULTS]\", add_special_tokens=False)}')
   "
   ```

2. Check outputs:
   - Each delimiter should be single token: `[123456]`
   - Multi-token: `[12, 34, 56]` → FAIL

**Pass Criteria:**
- ✅ All 4 delimiters are single tokens → Proceed to Gate 1

**Fail Criteria:**
- ❌ Any delimiter is multi-token → STOP (training infeasible)

**Documentation:**
- Create `logs/gate0-tokenizer.txt` with results

**Time estimate:** 5 minutes

---

## Gate 1: MLX Smoke Test (~30 min)

**Purpose:** Verify Devstral loads in MLX, generates code, and fits in memory.

**Steps:**

1. Download 5-bit quantized model:
   ```bash
   uv run python -m mlx_lm.convert \
     --hf-path mistralai/Devstral-Small-2 \
     --mlx-path devstral_small2_5bit \
     --quantize \
     --q-bits 5
   ```

2. Create smoke test script `scripts/gate1_smoke_test.py`:
   ```python
   from mlx_lm import load, generate
   import time

   print("Loading model...")
   start = time.time()
   model, tokenizer = load("devstral_small2_5bit")
   load_time = time.time() - start

   prompt = "Write a Python function to check if a number is prime:"
   print(f"Generating...\n{prompt}")

   start = time.time()
   output = generate(model, tokenizer, prompt=prompt, max_tokens=100)
   gen_time = time.time() - start

   print(f"\nOutput:\n{output}")
   print(f"\nLoad time: {load_time:.2f}s")
   print(f"Generation time: {gen_time:.2f}s")
   ```

3. Run and measure:
   ```bash
   uv run python scripts/gate1_smoke_test.py
   ```

**Pass Criteria:**
- ✅ Model loads without error
- ✅ Generates valid Python code
- ✅ Memory usage ≤20 GB
- ✅ Load time <60s

**Fail Criteria:**
- ❌ Load fails
- ❌ Memory >20 GB → STOP (won't fit on M1/M2 machines)

**Documentation:**
- Create `logs/gate1-smoke-test.txt` with metrics

**Time estimate:** 30 minutes (including download)

---

## Gate 2: Latency Benchmark (~30 min)

**Purpose:** Measure generation speed on representative queries. Qwen3 averages 2.90s.

**Steps:**

1. Create benchmark script `scripts/gate2_latency.py`:
   ```python
   from mlx_lm import load, generate
   import time

   model, tokenizer = load("devstral_small2_5bit")

   queries = [
       "Find all classes in src/punie/agent/",
       "Show me the TypeCheckResult model",
       "What is dependency injection?",
       "Check types in src/punie/agent/factory.py",
       "List modified files",
   ]

   times = []
   for query in queries:
       start = time.time()
       _ = generate(model, tokenizer, prompt=query, max_tokens=200)
       elapsed = time.time() - start
       times.append(elapsed)
       print(f"{elapsed:.2f}s - {query}")

   avg = sum(times) / len(times)
   print(f"\nAverage: {avg:.2f}s")
   print(f"Target: ≤15s")
   print(f"Qwen3 baseline: 2.90s")
   ```

2. Run benchmark:
   ```bash
   uv run python scripts/gate2_latency.py
   ```

**Pass Criteria:**
- ✅ Average generation time ≤15s → Proceed to Gate 3

**Soft Fail Criteria:**
- ⚠️ Average >15s → Soft NO-GO (too slow for production)
- Note: Can proceed to Gate 3 to check quality, but speed is a concern

**Documentation:**
- Create `logs/gate2-latency.txt` with per-query times

**Time estimate:** 30 minutes

---

## Gate 3: Zero-Shot Tool Calling (~2 hours)

**Purpose:** Test if base Devstral model can generate tool calls in Mistral format without fine-tuning.

**Steps:**

1. Create test script `scripts/gate3_zero_shot.py`:
   ```python
   from mlx_lm import load, generate

   model, tokenizer = load("devstral_small2_5bit")

   # Format using Mistral's tool-calling convention
   system = """You are Punie, an AI coding assistant. You have these tools:

   - read_text_file(path: str) -> str
   - write_text_file(path: str, content: str) -> str
   - terminal(command: str) -> str

   Use [TOOL_CALLS] and [/TOOL_CALLS] to call tools."""

   queries = [
       "Read the file src/punie/agent/factory.py",
       "Find all Python files in src/",
       "Show me the TypeCheckResult model",
       "What is dependency injection?",  # Should answer directly
       "Check types in src/punie/agent/",
   ]

   for query in queries:
       prompt = f"{system}\n\nUser: {query}\nAssistant:"
       output = generate(model, tokenizer, prompt=prompt, max_tokens=200)
       print(f"\n{'='*60}")
       print(f"Query: {query}")
       print(f"Output:\n{output}")

       has_tool_call = "[TOOL_CALLS]" in output
       print(f"Tool call: {'YES' if has_tool_call else 'NO'}")
   ```

2. Run and analyze:
   ```bash
   uv run python scripts/gate3_zero_shot.py
   ```

**Pass Criteria:**
- ✅ ≥1 correct tool call out of 5 queries → Proceed to Gate 4
- Correct = uses `[TOOL_CALLS]` format + valid tool name

**Fail Criteria:**
- ❌ 0 tool calls → PROCEED WITH CAUTION
- Note: Can still train, but zero-shot failure suggests weaker base capability

**Documentation:**
- Create `logs/gate3-zero-shot.txt` with all outputs
- Note which queries produced tool calls

**Time estimate:** 2 hours (including analysis)

---

## Gate 4: Small-Scale LoRA (~3-4 hours)

**Purpose:** Test if LoRA fine-tuning works before committing to full conversion. Train on 10% of data (100 examples, 50 iterations).

**Steps:**

1. Convert 100 Phase 27 examples to Mistral format:
   ```bash
   uv run python scripts/convert_to_mistral_format.py \
     --input data/phase27_merged/train.jsonl \
     --output data/devstral_gate4/train.jsonl \
     --limit 100
   ```

   Key changes:
   - `<tool_call>` → `[TOOL_CALLS]`
   - XML format → JSON format
   - `<|im_start|>` / `<|im_end|>` → Mistral chat tokens

2. Create 10 validation examples:
   ```bash
   uv run python scripts/convert_to_mistral_format.py \
     --input data/phase27_merged/valid.jsonl \
     --output data/devstral_gate4/valid.jsonl \
     --limit 10
   ```

3. Train small LoRA:
   ```bash
   uv run python -m mlx_lm.lora \
     --model devstral_small2_5bit \
     --data data/devstral_gate4 \
     --train \
     --iters 50 \
     --batch-size 1 \
     --learning-rate 1e-4 \
     --lora-layers 8 \
     --adapter-path adapters_devstral_gate4
   ```

4. Fuse and quantize:
   ```bash
   uv run python -m mlx_lm.fuse \
     --model devstral_small2_5bit \
     --adapter-path adapters_devstral_gate4 \
     --save-path fused_devstral_gate4_f16 \
     --dequantize

   uv run python -m mlx_lm.convert \
     --hf-path fused_devstral_gate4_f16 \
     --mlx-path fused_devstral_gate4_5bit \
     --quantize \
     --q-bits 5
   ```

5. Test on 10 validation queries:
   ```bash
   uv run python scripts/test_gate4_model.py
   ```

**Pass Criteria:**
- ✅ ≥60% accuracy (6/10) → GREEN LIGHT for Gate 5
- Model generates tool calls in correct format
- At least some field access (if applicable)

**Fail Criteria:**
- ❌ <60% accuracy → STOP (LoRA ineffective on this architecture)
- ❌ Training diverges (val loss increases)

**Documentation:**
- Create `logs/gate4-training.txt` with loss curves
- Create `logs/gate4-validation.txt` with results

**Time estimate:** 3-4 hours (including conversion, training, testing)

---

## Gate 5: Full Conversion (SEPARATE PHASE, 6-9 days)

**Purpose:** Full training run if Gates 0-4 all pass. This is a SEPARATE commitment phase.

**Steps:**

### Day 1-2: Data Conversion
1. Convert all 1104 Phase 27 examples to Mistral format:
   - 993 training examples
   - 111 validation examples

2. Format verification:
   - Check all `<tool_call>` → `[TOOL_CALLS]`
   - Validate JSON structure in tool calls
   - Verify chat template tokens

### Day 3-5: Training
1. Full LoRA training:
   ```bash
   uv run python -m mlx_lm.lora \
     --model devstral_small2_5bit \
     --data data/devstral_full \
     --train \
     --iters 500 \
     --batch-size 1 \
     --learning-rate 1e-4 \
     --lora-layers 8 \
     --adapter-path adapters_devstral_full
   ```

2. Monitor training:
   - Track train/valid loss
   - Check for convergence
   - Target: ≥79% reduction in validation loss (Phase 27 baseline)

### Day 6-7: Model Preparation
1. Fuse adapters to float16
2. Quantize to 5-bit
3. Verify model size (~14-20 GB)

### Day 8-9: Validation
1. Run Phase 27 validation suite (40 queries):
   ```bash
   uv run python scripts/test_phase27_validation.py \
     --model fused_devstral_full_5bit
   ```

2. Check 8 categories:
   - Direct answers: 5/5 (100%)
   - Existing LSP: ≥4/5 (≥80%)
   - New LSP: ≥4/5 (≥80%)
   - Git tools: ≥4/5 (≥80%)
   - Existing tools: ≥4/5 (≥80%)
   - Field access: ≥4/5 (≥80%)
   - Cross-tool: ≥3/5 (≥60%)
   - Discrimination: ≥4/5 (≥80%)

**Pass Criteria:**
- ✅ Overall accuracy ≥85% (34/40) → DEPLOY
- ✅ No category below minimum threshold

**Fail Criteria:**
- ❌ Overall accuracy <85% → Stick with Qwen3
- ❌ Any critical category fails completely

**Documentation:**
- Create `docs/devstral-evaluation-results.md`
- Update `MEMORY.md` with decision

**Time estimate:** 6-9 days total

---

## Decision Matrix

```
Gate 0 FAIL → STOP (tokenizer incompatible)
Gate 1 FAIL → STOP (won't load or fit in memory)
Gate 2 FAIL → Soft NO-GO (too slow, but continue to Gate 3)
Gate 3 FAIL → PROCEED WITH CAUTION (zero-shot weak)
Gate 4 FAIL → STOP (LoRA ineffective)
Gate 4 PASS → Decision point: commit to Gate 5?

Gate 5 FAIL → Stick with Qwen3
Gate 5 PASS → Deploy Devstral
```

---

## Critical Files

**Documentation:**
- `docs/research/minimum-model-requirements.md` - 9 identified risks
- `agent-os/specs/2026-02-16-devstral-evaluation/shape.md` - Detailed gate descriptions
- `docs/phase27-complete-implementation.md` - Phase 27 baseline

**Training Data:**
- `data/phase27_merged/` - 1104 examples (Qwen3 format)
- `scripts/convert_to_mistral_format.py` - Format converter (to be created)

**Validation:**
- `scripts/test_phase27_validation.py` - 40-query test suite
- Phase 27 model: `fused_model_qwen3_phase27_5bit/`

---

## Verification

For each gate:

1. **Code verification:**
   - Use `astral:ruff` skill to check and fix linting
   - Use `astral:ty` skill to check types
   - Run `uv run pytest` for any test modifications

2. **Documentation:**
   - Log all results in `logs/gateN-*.txt`
   - Document pass/fail decision
   - Note any unexpected findings

3. **Decision:**
   - Evaluate against pass/fail criteria
   - Stop immediately on hard failures
   - Document rationale for proceeding or stopping

---

## Success Criteria

**Gate 0-4 (Pre-commitment):**
- ✅ All gates pass with clear results
- ✅ Gate 4 shows ≥60% accuracy
- ✅ Total time ≤7 hours
- ✅ Decision documented: proceed to Gate 5 or stop

**Gate 5 (Full conversion):**
- ✅ Training converges (≥79% val loss reduction)
- ✅ Validation suite ≥85% accuracy (34/40)
- ✅ No critical category failures
- ✅ Model size ≤20 GB
- ✅ Generation speed competitive with Qwen3

---

## Rollback Plan

If Gate 5 fails:
- Keep Qwen3-30B-A3B as production model
- Archive Devstral work in `research/devstral-evaluation/`
- Document learnings in `docs/research/devstral-lessons-learned.md`
- Consider alternative models or approaches
