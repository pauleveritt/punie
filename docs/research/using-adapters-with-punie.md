# Using LoRA Adapters with Punie

**Date:** 2026-02-11
**Status:** Documentation for Gap 4

## Overview

This guide explains how to use trained LoRA adapters with Punie's agent. After training an adapter, you can load it to enhance the model's performance.

---

## Three Usage Patterns

### 1. **Standalone Evaluation** (Already Working)

Use adapters in evaluation without running the full agent:

```python
from punie.training.eval_runner import run_evaluation, EvalRunConfig
from punie.training.server_config import ServerConfig
from punie.training.eval_suites import create_baseline_suite

# Evaluate with adapter
config = EvalRunConfig(
    server_config=ServerConfig(
        model_path="mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
        port=8080,
        adapter_path="adapters/my-adapter",  # ← Load adapter here
    ),
    suite=create_baseline_suite(),
    workspace=Path.cwd(),
    manage_server=True,
)

report = await run_evaluation(config)
print(f"Score with adapter: {report.overall_score:.1%}")
```

**Status:** ✅ Fully implemented and working

---

### 2. **Manual mlx_lm.server** (Works Now)

Start mlx_lm.server manually with adapter, then run Punie:

```bash
# Terminal 1: Start server with adapter
mlx_lm.server \
  --model mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit \
  --adapter-path adapters/my-adapter \
  --port 8080

# Terminal 2: Run Punie pointing to that server
punie serve --model local:http://localhost:8080/v1/default
```

**How it works:**
1. `mlx_lm.server` loads both base model + adapter
2. All API calls to that server use the adapted model
3. Punie connects via OpenAI-compatible API
4. **Adapter is already applied at server level**

**Status:** ✅ Works now, no code changes needed

---

### 3. **Integrated Punie Command** (Needs Implementation)

Ideal UX: Punie manages server + adapter automatically:

```bash
# Proposed command (not yet implemented)
punie serve \
  --model mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit \
  --adapter adapters/my-adapter \
  --port 8080
```

**How it would work:**
1. Parse `--adapter` flag in CLI
2. Pass adapter_path to ServerConfig
3. Start mlx_lm.server with both model + adapter
4. Create agent using that server

**Implementation needed:**

```python
# In src/punie/cli.py, modify serve command:

@app.command("serve")
def serve(
    model: str,
    adapter: str | None = typer.Option(None, "--adapter", help="Path to LoRA adapter"),
    port: int = 8080,
    # ... other args
):
    if adapter:
        # Use ServerProcess with adapter
        from punie.training.server import ServerProcess
        from punie.training.server_config import ServerConfig

        config = ServerConfig(
            model_path=model,
            port=port,
            adapter_path=adapter,
        )

        async def run_with_adapter():
            async with ServerProcess(config=config) as server:
                # Server now running with adapter
                # Create agent pointing to this server
                agent_config = AgentConfig(
                    model=f"local:http://localhost:{port}/v1/default",
                    # ... other config
                )
                await run_serve_agent(
                    model=agent_config.model,
                    name=agent_config.name,
                    # ... other args
                )

        asyncio.run(run_with_adapter())
    else:
        # Normal flow without adapter
        asyncio.run(run_serve_agent(...))
```

**Status:** ❌ Not yet implemented (but straightforward)

---

## Current Workaround (Use Pattern #2)

Until integrated command is implemented, use manual server:

### Step 1: Train an adapter

```bash
# Create or download training data
uv run python create_hand_authored_tool_examples.py

# Train adapter
uv run punie train data/hand-authored/tool-calling \
  --model mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit \
  --output adapters/tool-calling-v1 \
  --iters 100
```

### Step 2: Start server with adapter

```bash
mlx_lm.server \
  --model mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit \
  --adapter-path adapters/tool-calling-v1 \
  --port 8080
```

### Step 3: Run Punie

```bash
# In another terminal
punie serve --model local:http://localhost:8080/v1/default
```

### Step 4: Test tool calling

```
User: Read the file src/main.py
```

The agent should now use the trained adapter which has learned how to call tools properly.

---

## Implementation Roadmap

### Phase 1: Documentation (This Document) ✅
- Document three usage patterns
- Provide workaround instructions
- Explain how it all fits together

### Phase 2: Integrated Command (30 minutes)
- Add `--adapter` flag to `punie serve`
- Use `ServerProcess` to manage mlx_lm.server
- Update CLI help text

### Phase 3: Auto-Select Best Adapter (Future)
- Scan `adapters/` directory
- Find latest or best-scoring adapter
- Load automatically if available

### Phase 4: Adapter Composition (Future)
- Support multiple adapters (general + tool-calling)
- Layer adapters for combined benefits
- Requires MLX support for adapter stacking

---

## Technical Details

### How mlx_lm.server Loads Adapters

```bash
mlx_lm.server \
  --model <base-model> \
  --adapter-path <adapter-dir>
```

What happens:
1. Load base model weights
2. Load LoRA weights from adapter directory
3. **Apply adapter to model** (not separate inference step)
4. Serve via OpenAI-compatible API
5. All `/v1/chat/completions` calls use adapted model

### Adapter File Structure

```
adapters/my-adapter/
├── adapter_config.json   # LoRA configuration (rank, layers, etc.)
└── adapters.safetensors  # LoRA weights (~20MB for rank 8)
```

### Multiple Adapters

To use different adapters:

```bash
# General-purpose adapter
mlx_lm.server --model <base> --adapter-path adapters/general-v1 --port 8080

# Tool-calling adapter
mlx_lm.server --model <base> --adapter-path adapters/tool-calling-v1 --port 8081

# Connect Punie to either one
punie serve --model local:http://localhost:8080/v1/default  # General
punie serve --model local:http://localhost:8081/v1/default  # Tool-calling
```

---

## Testing Adapter Effectiveness

### 1. Evaluation Suite

```python
# Evaluate baseline
baseline_config = EvalRunConfig(
    server_config=ServerConfig(model_path="model", port=8080),
    suite=create_baseline_suite(),
    workspace=Path.cwd(),
    manage_server=True,
)
baseline_report = await run_evaluation(baseline_config)

# Evaluate with adapter
adapted_config = EvalRunConfig(
    server_config=ServerConfig(
        model_path="model",
        port=8080,
        adapter_path="adapters/my-adapter",
    ),
    suite=create_baseline_suite(),
    workspace=Path.cwd(),
    manage_server=True,
)
adapted_report = await run_evaluation(adapted_config)

# Compare
improvement = adapted_report.overall_score - baseline_report.overall_score
print(f"Improvement: {improvement:+.1%}")
```

### 2. Real-World Testing

```bash
# Start server with adapter
mlx_lm.server --model <base> --adapter-path adapters/my-adapter --port 8080

# Run Punie
punie serve --model local:http://localhost:8080/v1/default

# Test with real tasks
# - Ask it to read files
# - Ask it to write code
# - Ask it to run commands
# - Observe if tool calling improved
```

---

## Common Issues

### Adapter Not Loading

**Symptom:** Server starts but adapter has no effect

**Check:**
1. Adapter path is correct: `ls -la adapters/my-adapter/`
2. Files exist: `adapter_config.json` and `adapters.safetensors`
3. Server logs show adapter loading (check stderr)

### Wrong Model

**Symptom:** Server fails to start with adapter

**Cause:** Adapter was trained for different base model

**Fix:** Use same model for training and inference:
```bash
# Training
punie train data/ --model mlx-community/Qwen2.5-Coder-1.5B --output adapters/v1

# Inference (must match)
mlx_lm.server --model mlx-community/Qwen2.5-Coder-1.5B --adapter-path adapters/v1
```

### Performance Regression

**Symptom:** Adapter makes performance worse

**Causes:**
1. Not enough training iterations
2. Too few training examples
3. Learning rate too high (model forgot baseline knowledge)
4. Dataset quality issues

**Fix:** Retrain with:
- More iterations (100-200 instead of 10-20)
- More examples (100+ instead of 10)
- Lower learning rate (1e-5 instead of 5e-5)
- Better dataset (validate and filter)

---

## Recommendations

### For Immediate Use
1. **Use Pattern #2** (manual server) - works perfectly now
2. Train adapters using documented process
3. Test with evaluation suite first
4. Then test with real agent workflows

### For Production
1. **Implement Pattern #3** (integrated command) - 30 min work
2. Add to CLI help and documentation
3. Test thoroughly with both patterns

### For Future
1. Auto-select best adapter
2. Support adapter composition
3. Adapter versioning and management
4. A/B testing infrastructure

---

## Summary

✅ **Adapters work now** via manual server (Pattern #2)
✅ **Evaluation infrastructure** fully supports adapters
❌ **Integrated CLI** not yet implemented (but easy to add)

**Immediate action:** Document this approach, use manual server
**Next step:** Implement `--adapter` flag for `punie serve`
**Future:** Advanced adapter management features
