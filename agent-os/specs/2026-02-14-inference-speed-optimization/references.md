# References: Phase 21 — Inference Speed Optimization

## MLX-LM Documentation

### Speculative Decoding
- **Main docs:** https://github.com/ml-explore/mlx-examples/tree/main/llms#speculative-decoding
- **Server flags:** https://github.com/ml-explore/mlx-examples/blob/main/llms/mlx_lm/server.py
- **CLI usage:** `python -m mlx_lm.server --help`

**Key flags:**
```bash
--draft-model MODEL        # Path or HF model ID for draft model
--num-draft-tokens N       # Number of tokens to draft per step (default: 10)
```

**Example usage:**
```bash
python -m mlx_lm.server \
  --model mlx-community/Qwen3-30B-A3B-Instruct-5bit \
  --draft-model mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit \
  --num-draft-tokens 5
```

### MLX-LM v0.30.6 Server API
- **Base URL:** `http://localhost:8080`
- **Chat completions:** `POST /v1/chat/completions`
- **OpenAI-compatible API**
- **Streaming support:** `stream=true`

## Project Implementation Patterns

### Server Lifecycle Management
**File:** `src/punie/training/eval_runner.py`
```python
from punie.training.server import ServerProcess

with ServerProcess(server_config) as server:
    # Server automatically starts/stops
    agent = create_agent(model_url=server.url, ...)
    result = await agent.run(query)
```

### Agent Construction
**File:** `src/punie/agent/factory.py`
```python
from punie.agent.factory import create_agent

agent = create_agent(
    model_url="http://localhost:8080",
    agent_config=agent_config,
    tools=tools,
)
```

### Direct MLX Benchmarking
**File:** `scripts/test_single_model.py`
```python
import mlx_lm
import time

model, tokenizer = mlx_lm.load(model_path)

start = time.time()
response = mlx_lm.generate(
    model=model,
    tokenizer=tokenizer,
    prompt=prompt,
    max_tokens=512,
)
elapsed = time.time() - start
```

## Existing Test Patterns

### ServerConfig Tests
**File:** `tests/test_training_server_config.py`

**Pattern 1: Individual field test**
```python
def test_server_config_with_temp() -> None:
    config = ServerConfig(model_path="/path/to/model", temp=0.5)
    assert config.temp == 0.5
```

**Pattern 2: Defaults test**
```python
def test_server_config_defaults() -> None:
    config = ServerConfig(model_path="/path/to/model")
    assert config.temp is None
    assert config.top_p is None
    # Add: assert config.draft_model is None
    # Add: assert config.num_draft_tokens is None
```

**Pattern 3: All parameters test**
```python
def test_server_config_all_parameters() -> None:
    config = ServerConfig(
        model_path="/path/to/model",
        temp=0.7,
        top_p=0.9,
        # Add: draft_model="path/to/draft",
        # Add: num_draft_tokens=5,
    )
    # Add assertions for new fields
```

### Server Command Tests
**File:** `tests/test_training_server.py`

**Pattern 1: Individual flag test**
```python
def test_build_server_command_with_temp() -> None:
    config = ServerConfig(model_path="/path/to/model", temp=0.5)
    cmd = build_server_command(config)
    assert "--temp" in cmd
    idx = cmd.index("--temp")
    assert cmd[idx + 1] == "0.5"
```

**Pattern 2: All parameters test**
```python
def test_build_server_command_all_parameters() -> None:
    config = ServerConfig(
        model_path="/path/to/model",
        temp=0.7,
        top_p=0.9,
        # Add: draft_model="path/to/draft",
        # Add: num_draft_tokens=5,
    )
    cmd = build_server_command(config)
    # Add assertions for --draft-model and --num-draft-tokens
```

## Draft Model Options

### Qwen2.5-Coder Series
- **0.5B-Instruct-4bit:** ~300MB (smallest, fastest)
- **1.5B-Instruct-4bit:** ~1GB (recommended balance)
- **7B-Instruct-4bit:** ~4GB (larger, slower draft)

**Recommendation:** Start with 1.5B (good balance of speed vs accuracy)

### Memory Estimates
| Configuration | Model Size | Draft Size | Total Memory |
|---------------|------------|------------|--------------|
| Baseline | 20GB (5-bit) | N/A | ~20GB |
| + 0.5B draft | 20GB | ~0.3GB | ~21GB |
| + 1.5B draft | 20GB | ~1GB | ~21GB |
| + 7B draft | 20GB | ~4GB | ~24GB |

All configurations fit comfortably in 32GB unified memory.

## Speculative Decoding Theory

### How It Works
1. **Draft phase:** Small fast model generates N tokens
2. **Verify phase:** Large main model scores draft tokens
3. **Accept/reject:** Keep matching tokens, regenerate mismatches
4. **Benefit:** Parallel verification faster than sequential generation

### Optimal Settings
- **num_draft_tokens:** 2-10 (sweet spot around 5)
- **Draft model size:** 10-20% of main model (1.5B vs 30B ≈ 5%)
- **Quality:** Should match main model's training domain

### Expected Speedup
- **Best case:** 2-3x speedup (high acceptance rate)
- **Typical:** 1.5-2x speedup (realistic for different model sizes)
- **Worst case:** 1.1x speedup (low acceptance rate, verification overhead)

## PydanticAI Integration

### Model Configuration
**File:** `src/punie/agent/factory.py`

```python
model_settings_dict = {
    "temperature": config.temperature,
    "max_tokens": config.max_tokens,
    "stop_sequences": list(config.stop_sequences),
    # Speculative decoding configured at server level, not here
}
```

**Note:** Speculative decoding is transparent to PydanticAI — configured at mlx_lm.server level.

## Standard 5-Query Discrimination Test

1. **Tool call:** "Find all Django views in the codebase"
2. **Tool call:** "Show me the UserSerializer implementation"
3. **Direct answer:** "What is dependency injection?"
4. **Tool call:** "Find all uses of async/await"
5. **Direct answer:** "What's the difference between ORM and raw SQL?"

**Target:** 5/5 correct discrimination (100% accuracy)

## Related Phases

- **Phase 20:** Qwen3-30B-A3B migration + 5-bit quantization (current model)
- **Phase 5c:** 8-bit → 6-bit optimization (quantization research)
- **Phase 8:** 6-bit as optimal quantization level (established best practice)

## External Resources

- **MLX-LM GitHub:** https://github.com/ml-explore/mlx-examples/tree/main/llms
- **MLX-LM PyPI:** https://pypi.org/project/mlx-lm/
- **Qwen3 models:** https://huggingface.co/collections/Qwen/qwen3-676698e7ddcd0cc97a93bec3
- **Speculative decoding paper:** https://arxiv.org/abs/2211.17192
