# Phase 22 Code Mode — References

## Punie Codebase

### Core toolset
- `src/punie/agent/toolset.py` — Existing 3 tools (read_file, write_file, run_command)
- `src/punie/agent/config.py` — PUNIE_INSTRUCTIONS system prompt (will be updated)
- `src/punie/agent/factory.py` — Creates PydanticAI agent with toolset

### Training infrastructure
- `scripts/convert_to_xml_format.py` — Phase 21 converter (pattern to follow)
- `scripts/generate_domain_examples.py` — Phase 8 example generator (pattern to follow)
- `data/phase8_xml_format/` — 683 Phase 21 training examples (source for conversion)

### Testing
- `scripts/test_server_pipeline.py` — End-to-end pipeline test (will be updated for Phase 22)
- `scripts/test_single_model.py` — Single model tester (Phase 8 pattern)

## External Resources

### Monty (Pydantic sandbox)
- [Monty repository](https://github.com/pydantic/monty)
- [Monty PR #4153](https://github.com/pydantic/pydantic/pull/4153) — Original design discussion
- Version: v0.0.3 (experimental, API may change)

**Key Monty APIs:**
```python
from monty import start, resume, ExternalCall

# Start execution
result = start(code, external_functions={"read_file": ...})

# Handle external calls
if isinstance(result, ExternalCall):
    output = my_read_file(result.args[0])
    result = resume(result, output)
```

### mlx_lm (Apple MLX)
- [mlx-examples repository](https://github.com/ml-explore/mlx-examples)
- [mlx_lm.server XML parser](https://github.com/ml-explore/mlx-examples/blob/main/llms/mlx_lm/server.py#L150) — Token 151657 triggers `<tool_call>` parsing
- [mlx_lm.fuse](https://github.com/ml-explore/mlx-examples/blob/main/llms/mlx_lm/fuse.py) — LoRA fusion
- [mlx_lm.convert](https://github.com/ml-explore/mlx-examples/blob/main/llms/mlx_lm/convert.py) — Quantization

### Qwen3 Coder
- [Model card](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct)
- [Tool calling format](https://github.com/QwenLM/Qwen/blob/main/examples/tool_calling.md) — Native XML format
- Base model: `mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit`

### ACP (Agent Communication Protocol)
- `agent-os/standards/pydantic-agent-communication-protocol.md` — Protocol definition
- Tool lifecycle: request → started → progress → result
- Tool types: `file-system/read`, `file-system/write`, `shell/command`

## Prior Art

### Phase 21 (XML Format Fix)
- **Problem:** JSON format mismatch → 40% accuracy
- **Solution:** Convert to XML → 100% accuracy
- **Files:**
  - `docs/diary/2026-02-14-phase21-xml-format-fix.md` — Session diary
  - `fused_model_qwen3_phase21_xml_5bit/` — Production model (20GB)
  - `data/phase8_xml_format/` — 683 training examples

### Phase 8 (Qwen3-30B-A3B)
- **Problem:** Phase 5 model was too small (7B)
- **Solution:** Upgrade to 30B model
- **Key learning:** 6-bit quantization preserves LoRA signal (100% accuracy)
- **Files:**
  - `docs/diary/2026-02-14-phase8-qwen3-upgrade.md` — Session diary
  - `fused_model_qwen3_phase8_6bit/` — 6-bit model (23GB)

### Phase 5c (Dequantized Fusion)
- **Problem:** 4-bit re-quantization destroyed LoRA signal
- **Solution:** Dequantize → fuse → 8-bit quantize
- **Key learning:** 256 quantization levels (8-bit) preserve deltas, 16 levels (4-bit) do not
- **Files:**
  - `docs/diary/2026-02-13-phase5c-dequantized-fusion.md` — Session diary
  - `benchmark_phase5_vs_base.py` — Benchmark script

## Performance Baselines

### Phase 21 (current)
- Single-tool query: ~6.6s
- Direct answer: ~1.8s
- Multi-step (5 tools): ~20s (5 turns × ~4s)
- Accuracy: 100% (5/5)

### Phase 22 (target)
- Single-tool query: ~6.6s (no regression)
- Direct answer: ~1.8s (no regression)
- Multi-step (5 tools): ~8s (2 turns × ~4s) — **60% reduction**
- Accuracy: 80%+ (4/5) on multi-step queries

## Related Work

### CodeAct (Wang et al., 2024)
- [Paper](https://arxiv.org/abs/2402.01030) — "Executable Code Actions Elicit Better LLM Agents"
- Key idea: Generate Python instead of structured tool calls
- Benchmark: CodeAct outperforms ReAct on multi-step tasks

### Gorilla (Patil et al., 2023)
- [Paper](https://arxiv.org/abs/2305.15334) — "Large Language Models Connected with Massive APIs"
- Key idea: Fine-tune models to call APIs via code
- Benchmark: Gorilla achieves 94% accuracy on API-bench

### Toolformer (Schick et al., 2023)
- [Paper](https://arxiv.org/abs/2302.04761) — "Language Models Can Teach Themselves to Use Tools"
- Key idea: Self-supervised training on tool call examples
- Difference: Toolformer uses special tokens, we use XML wrapper
