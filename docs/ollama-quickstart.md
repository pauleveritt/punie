# Ollama Integration - Quick Start

## Prerequisites

1. Install Ollama: https://ollama.ai/
2. Ensure `punie` is installed: `uv sync`

## Setup (One-Time)

```bash
# Start ollama server
ollama serve

# Pull a code model (first time only)
ollama pull devstral  # 24B code model, ~14GB download
# or
ollama pull qwen3:30b-a3b  # 30B active tokens model
```

## Usage

### Option 1: Punie Server Mode (Recommended)

```bash
# Terminal 1: Start punie server with ollama model
punie serve --model ollama:devstral

# Terminal 2: Ask questions via CLI
punie ask "Check for type errors in src/"
punie ask "Find all Python files and count imports"
punie ask "What's the difference between git merge and rebase?"

# Or connect from PyCharm (uses stdio bridge)
punie init --model ollama:devstral
# Then use "Chat with Punie" in PyCharm
```

### Option 2: Direct Python Usage

```python
from pathlib import Path
from punie.agent.factory import create_local_agent
from punie.agent.deps import ACPDeps
from punie.acp.contrib.tool_calls import ToolCallTracker

# Create agent with ollama model
agent, client = create_local_agent(
    model="ollama:devstral",
    workspace=Path.cwd()
)

# Create dependencies
deps = ACPDeps(
    client_conn=client,
    session_id="test-session",
    tracker=ToolCallTracker(),
)

# Run query
async def main():
    result = await agent.run(
        "Check for type errors in src/punie/agent/",
        deps=deps
    )
    print(result.output)

# Run with asyncio
import asyncio
asyncio.run(main())
```

### Option 3: Validation Testing

```bash
# Test zero-shot Code Mode performance
python scripts/validate_zero_shot_code_mode.py --model devstral

# Expected output:
# Category 1: Direct Answers (expect NO tool calls)
# ✓ direct_answers        : 4/5 (80%)
#
# Category 2: Single Tool Calls (expect tool calls)
# ✓ single_tool          : 4/5 (80%)
#
# Overall: 16/20 (80%)
# Zero-shot target: ≥50% (10/20)
# Status: ✓ PASS
```

## Available Models

### Recommended Code Models

| Model | Size | Speed | Best For |
|-------|------|-------|----------|
| `devstral` | 24B | Fast | Code completion, Python/JS |
| `qwen3:30b-a3b` | 30B | Medium | Multi-language, reasoning |
| `codellama:34b` | 34B | Slower | Long context, complex tasks |

### Pull Models

```bash
ollama pull devstral
ollama pull qwen3:30b-a3b
ollama pull codellama:34b
```

## Troubleshooting

### "Cannot connect to ollama"

```bash
# Check if ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve
```

### "Model not found"

```bash
# Pull the model first
ollama pull devstral

# List available models
ollama list
```

### "Port 11434 already in use"

```bash
# Check what's using port 11434
lsof -i :11434

# Kill existing ollama processes
pkill ollama

# Restart ollama
ollama serve
```

### Slow Performance

```bash
# Use a smaller/quantized model
ollama pull devstral:7b-q4_0  # 4-bit quantization, ~4GB

# Or check system resources
top  # Look for high CPU/memory usage
```

## Comparison: Ollama vs MLX vs Cloud

| Feature | Ollama | MLX (local) | Cloud (Claude/GPT) |
|---------|--------|-------------|-------------------|
| **Setup** | `ollama serve` | Start mlx_lm.server | API key |
| **Models** | GGUF (any model) | MLX format only | Fixed models |
| **Speed** | Medium (CPU/GPU) | Fast (Apple Silicon) | Network latency |
| **Cost** | Free (local) | Free (local) | Pay per token |
| **Fine-tuning** | Yes (GGUF) | Yes (LoRA) | Limited |
| **Privacy** | Local | Local | Cloud |
| **Best for** | Cross-platform, easy setup | M1/M2 Macs, speed | No local GPU |

## Next Steps

1. **Try zero-shot first:**
   ```bash
   python scripts/validate_zero_shot_code_mode.py --model devstral
   ```

2. **If accuracy is good (≥70%):**
   - Use as-is (no fine-tuning needed!)
   - Deploy: `punie serve --model ollama:devstral`

3. **If accuracy is low (<50%):**
   - Try larger model: `ollama pull qwen3:30b-a3b`
   - Or add fine-tuning (see Phase 27 docs)

4. **Integrate with PyCharm:**
   ```bash
   punie init --model ollama:devstral
   # Restart PyCharm
   # Use "Chat with Punie" panel
   ```

## Examples

### Example 1: Type Checking

```bash
punie ask "Check for type errors in src/punie/agent/"

# Expected response:
# I'll run type checking on src/punie/agent/...
# [Calls typecheck() tool]
# Found 3 errors:
# - src/punie/agent/factory.py:42: Incompatible type...
# - src/punie/agent/config.py:15: Missing type annotation...
```

### Example 2: Multi-Step Workflow

```bash
punie ask "Run full quality check: ruff, pytest, and typecheck"

# Expected response:
# I'll run all three quality checks...
# [Calls execute_code() with multi-step Python]
# Results:
# - Ruff: 5 violations (3 fixable)
# - Pytest: 582 passed, 2 skipped
# - Typecheck: 108 errors
```

### Example 3: Direct Answer

```bash
punie ask "What's the difference between git merge and git rebase?"

# Expected response:
# Git merge creates a merge commit that combines two branches...
# [No tool calls - direct answer]
```

## Advanced Usage

### Custom Port

```bash
# Start ollama on custom port
OLLAMA_HOST=127.0.0.1:8888 ollama serve

# Use with punie (modify factory.py to accept custom port)
punie serve --model ollama:devstral --ollama-port 8888
```

### Multiple Models

```bash
# Terminal 1: devstral for code
punie serve --model ollama:devstral --port 8000

# Terminal 2: qwen3 for reasoning
punie serve --model ollama:qwen3:30b-a3b --port 8001

# Connect to different servers
punie ask --server ws://localhost:8000/ws "Fix syntax errors"
punie ask --server ws://localhost:8001/ws "Explain this architecture"
```

### Batch Testing

```bash
# Test multiple models in parallel
for model in devstral qwen3:30b-a3b codellama:34b; do
    echo "Testing $model..."
    python scripts/validate_zero_shot_code_mode.py --model "$model" > "results_$model.txt" &
done
wait

# Compare results
grep "Overall:" results_*.txt
```

## Resources

- [Ollama Models Library](https://ollama.ai/library)
- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Punie Documentation](../README.md)
- [Phase 27 Fine-Tuning Guide](./phase27-complete-implementation.md)
