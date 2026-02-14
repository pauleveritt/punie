# Model Fusion Spec - Standards

## Fusion Standards

- **Always dequantize first:** Use `--dequantize` flag to prevent 4-bit re-quantization
- **Test before re-quantizing:** Validate float16 model has 100% accuracy
- **8-bit for production:** Sweet spot for quality/speed/memory
- **Single file deployment:** Fused models don't need adapter files

## Benchmarking Standards

- **Configuration-driven:** Models defined as dicts, not hardcoded
- **5-query suite:** Standard discrimination test (3 direct, 2 tool)
- **Track all metrics:** Disk, memory, load time, gen time, accuracy
- **N-model comparison:** Tables support any number of models

## Testing Standards

- **Discrimination accuracy:** Must match adapter (100%)
- **Per-query validation:** Test all 5 queries individually
- **Memory tracking:** Monitor peak RSS during inference
- **Speed consistency:** Verify performance across all query types

## Documentation Standards

- **Root cause analysis:** Document why original fusion failed
- **Speed comparison:** Show speedups vs all baselines
- **Production recommendation:** Clear guidance on which model to use

## Project Standards

- Use Astral tools via skills (`astral:ruff`, `astral:ty`)
- Python 3.14 modern syntax
- No auto-commit — always ask before creating commits
- Delete broken models to reclaim disk space
