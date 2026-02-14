# Model Fusion Spec - Shape

## Architecture

```
fused_model_f16/                   # Float16 fused model (14.20 GB)
├── config.json
├── model.safetensors
├── tokenizer.json
└── tokenizer_config.json

fused_model_8bit/                  # 8-bit fused model (7.55 GB) ← PRODUCTION
├── config.json
├── model.safetensors              # Quantized to 8-bit (256 levels)
├── tokenizer.json
└── tokenizer_config.json

benchmark_phase5_vs_base.py        # Configuration-driven benchmark
benchmark_phase5c.log              # 4-model comparison results
```

## Key Design Decisions

### Root cause analysis

- 4-bit fusion destroys LoRA signal
- During `mlx_lm.fuse`: weights dequantized → LoRA added → re-quantized to 4-bit
- 4-bit has only 16 discrete values per group
- Small LoRA perturbations get rounded away
- Result: 13% of bytes changed but behavior = untrained base (60% accuracy)

### Two-step fusion process

1. **Dequantized fusion:** `mlx_lm.fuse --dequantize` → float16 without re-quantization
2. **8-bit quantization:** `mlx_lm.convert --quantize --q-bits 8` → 256 levels preserve deltas

### Why 8-bit is optimal

- **256 quantization levels** vs 16 for 4-bit (16x more precision)
- **Preserves LoRA deltas:** Small weight perturbations don't get rounded away
- **Memory efficient:** 7.55 GB vs 14.20 GB for float16 (half the size)
- **Speed:** Quantized ops faster than float16, eliminate adapter overhead
- **Single file:** No adapter loading, simpler deployment

### Configuration-driven benchmarking

- Model configs as dicts (zero code changes to add models)
- Argparse for selecting which configs to run
- Disk size tracking in tables
- N-model comparison (no hardcoded 2-vs-3 logic)

## Performance Results

| Model | Disk | Memory | Load | Avg Gen | Accuracy |
|-------|------|--------|------|---------|----------|
| Base (4-bit) | N/A | 3.99 GB | 1.36s | 38.60s | 60% |
| Adapter | 0.39 GB | 4.04 GB | 1.15s | 121.25s | 100% |
| Fused f16 | 14.20 GB | 14.19 GB | 6.24s | 44.62s | 100% |
| **Fused 8-bit** | **7.55 GB** | **7.54 GB** | **4.28s** | **14.27s** | **100%** |

**Speed improvements:**
- 8-bit vs base: 2.7x faster (63% speedup)
- 8-bit vs adapter: 8.5x faster
- 8-bit vs float16: 3.1x faster
