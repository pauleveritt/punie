# LoRA Layering as a Pre-Flywheel Improvement Mechanism

**Research notes from Phase 33b consolidation**
**Date: February 2026**

---

## Summary

Each fused model becomes the next phase's base for a new LoRA adapter. This **fuse-then-retrain cycle** is continual learning without catastrophic forgetting — and it gives us a structured path to improve the model before the Flywheel data-capture pipeline is mature enough to provide automated training signal.

---

## The Mechanism

MLX LoRA training always works on frozen weights + trainable adapters. After fusing:

```
Qwen3-Coder-30B (4-bit base, Qwen3 tokenizer)
  → Phase 33b LoRA (800 iters, 1,282 examples)
  → fused_model_qwen3_phase33b_5bit        ← new "base" with 33b knowledge baked in
      → Phase 34 LoRA (200–300 iters, ~80 targeted examples)
      → fused_model_qwen3_phase34_5bit     ← new "base"
          → Phase 35 LoRA ...
```

Each LoRA run adds behavior on top of all previously-fused knowledge. The model's tool-routing competence is preserved in the frozen weights; the new adapter refines specific weak spots.

**Key property:** This is exactly how QLoRA-style training compounds. The 5-bit fused model is a valid base for `mlx_lm.lora` — quantized frozen weights + floating-point adapters is the same setup as training on the original 4-bit Qwen3-Coder base.

---

## Phase 33b Weak Spots — The Targets

Phase 33b eval (27 prompts, corrected scoring):

| Category    | Score | Gap     |
|-------------|-------|---------|
| text_tools  | 100%  | —       |
| validation  | 100%  | —       |
| git         | 100%  | —       |
| cst         | 100%  | —       |
| lsp         | 90%   | -10 pts |
| **domain**  | **60%** | **-40 pts** |
| **multi_tool** | **35%** | **-65 pts** |

The two weak categories explain the gap from 82% to a hypothetical 95%+:

- **domain (60%):** Model partially generalizes the domain validator pattern but fails on unfamiliar project structures and tool combinations it hasn't seen verbatim.
- **multi_tool (35%):** Model struggles to chain 2–3 tools in a single `execute_code()` block, especially when the second tool depends on output from the first.

---

## What a Phase 34a Targeted Run Looks Like

### Data Strategy

Curate ~80 high-quality examples (no regeneration needed — write them by hand or from real usage):

| Category | Count | What to vary |
|----------|-------|-------------|
| domain | 30 | Different file paths, novel tdom/svcs patterns, multiple issues per file |
| multi_tool | 40 | 2-tool chains (typecheck→goto_def, ruff→hover), 3-tool chains, real error → fix sequences |
| lsp edge cases | 10 | Workspace-level queries, cross-file navigation |

### Training Parameters

Using `fused_model_qwen3_phase33b_5bit` as base:

```bash
uv run python -m mlx_lm lora \
    --train \
    --model fused_model_qwen3_phase33b_5bit \
    --data data/phase34_targeted \
    --adapter-path adapters_phase34 \
    --iters 300 \
    --batch-size 1 \
    --learning-rate 5e-5 \       # Lower LR — strong base, fine-grained adjustment
    --num-layers 8 \
    --grad-accumulation-steps 4 \
    --mask-prompt \
    --save-every 100
```

**Lower LR (5e-5 vs 1e-4):** Starting from a stronger base means less gradient signal is needed. High LR on a strong base risks overwriting previous learning.

**300 iters vs 800:** Targeted dataset (~80 examples × 3–4 passes) converges faster. No need for the full Phase 33b regime.

**Estimated time:** ~45 minutes total (train + fuse + quantize + eval).

---

## The Manual Flywheel Analogy

The difference between pre-Flywheel and post-Flywheel is only the **data capture method**:

| Source | Data capture | Training mechanism |
|--------|-------------|-------------------|
| Pre-Flywheel | Manual curation | LoRA on fused model |
| Post-Flywheel | `PunieEvent` + extractor | LoRA on fused model |

The training pipeline is **identical**. The Flywheel automates what we're currently doing by hand. This means:

1. Every LoRA run we do now is directly reusable knowledge when the Flywheel matures.
2. We can iterate on weak spots today without waiting for passive data collection to accumulate.
3. The fused model at each phase is the production model — no separate "training model" vs "serving model" distinction.

---

## Compounding Advantage

After 3–4 targeted phases, the model's accumulated knowledge looks like:

```
Phase 33b:  26-tool routing baseline (82.4%)
Phase 34a:  +domain generalization, +multi_tool chains
Phase 34b:  +real usage patterns (manual Flywheel)
Phase 35:   +Flywheel data when pipeline matures
```

Each phase is cheap (45 min) and incremental. Compare to Phase 33's 3.5-hour full retrain from scratch — targeted LoRA layering is roughly 8× faster per improvement cycle.

---

## Risks and Mitigations

**Risk: Overwriting previous learning.** Mitigated by lower LR (5e-5) and fewer iterations (300). If eval drops on previously-passing categories, discard the adapter and reduce LR further.

**Risk: 5-bit base introduces quantization noise.** This is the same tradeoff as training on the 4-bit Qwen3-Coder base — quantization error is small and the LoRA adapter compensates. No evidence this is a problem in practice (Phase 33 trained on 4-bit base successfully).

**Risk: Overfitting to small targeted dataset.** 80 examples × 300 iters at batch 1, grad_accum 4 = ~6,000 gradient steps / 80 = ~75 passes over the data. That's high. Use `--val-batches 10` and watch val loss. If diverging, stop early or add more data.

---

## Connection to Smaller Model Trajectory

This mechanism applies equally to Qwen3-8B (Phase 40 experiment). If the 8B model trains successfully on Phase 33b's 1,282 examples, targeted LoRA layering gives us the same improvement path — but at 8B scale (faster inference, smaller memory footprint, faster training cycles).

The smaller model has even more to gain from targeted LoRA since it starts with less pre-trained capacity and benefits proportionally more from domain-specific fine-tuning.

---

## Recommended Investigation (Phase 34a)

1. Curate 80 targeted examples (domain + multi_tool)
2. Train 300 iters on `fused_model_qwen3_phase33b_5bit` base, LR 5e-5
3. Fuse + quantize → `fused_model_qwen3_phase34a_5bit`
4. Run the 27-prompt eval (corrected scoring)
5. Compare category-by-category against Phase 33b baseline

**Success criterion:** domain ≥80% AND multi_tool ≥60%, with no regression on text_tools/validation/git/cst/lsp categories.

**Estimated effort:** ~3 hours total (1h data curation + 45min training pipeline + 30min eval analysis).
