# Punie the tiny Python agent

Imagine a tiny Python coding agent:

- Runs with local models
- Integrates into PyCharm via ACP
- Shifts more of the work of tools to the IDE via ACP
- Integrate an HTTP loop into the agent making it easy to add custom UX to interact
    - Speed up the "human-in-the-loop" with a custom UI
    - Track multiple agents running at once
- Embrace domain-specific customization to speed up agent and human performance

## Installation

```bash
uv pip install punie
```

## Usage

### Quick Start with Trained Models

**Option 1: Phase 8 Qwen3-30B Model (Recommended) 🚀 NEW**

Best overall quality with MoE architecture (30B total, 3.3B active per token):

```bash
# Terminal 1: Start MLX server with Phase 8 5-bit fused model
uv run python -m mlx_lm.server \
  --model fused_model_qwen3_phase8_5bit \
  --port 8080

# Terminal 2: Run Punie
uv run punie serve --model local
```

**Benefits:**
- 8-10x faster than adapter-based models
- Better quality from 30B MoE architecture
- Domain-focused: Python + HTML + CSS + JS with Django/FastAPI/Flask/Sphinx
- Optimized 5-bit quantization: 20GB model, 100% accuracy (33% smaller than 8-bit!)
- Fits in 32GB memory (20GB model + inference overhead)
- Scientific breakthrough: Found minimum quantization threshold (32 levels)

**Option 2: Phase 7 Full-Stack Model**

Best for web development with Python + HTML support (smaller, 7B model):

```bash
# Terminal 1: Start MLX server with Phase 7 model
uv run python -m mlx_lm.server \
  --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
  --adapter-path adapters_phase7 \
  --port 8080

# Terminal 2: Run Punie
uv run punie serve --model local
```

**Option 3: Phase 6 Python-Only Model**

Best for Python-focused development:

```bash
# Terminal 1: Start MLX server with Phase 6 model
uv run python -m mlx_lm.server \
  --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
  --adapter-path adapters_phase6 \
  --port 8080

# Terminal 2: Run Punie
uv run punie serve --model local
```

**Model Capabilities:**
- **Phase 8:** Python + HTML + CSS + JS (Django, FastAPI, Flask, Sphinx) - 30B MoE, 5-bit fused ⚡
- **Phase 7:** Python (FastAPI, pytest, Flask, etc.) + HTML (forms, semantic HTML) - 7B dense
- **Phase 6:** Python only (FastAPI, pytest, Flask, typer, click, httpx, starlette, pydantic) - 7B dense
- **Phase 5:** Python (svcs-di, tdom-svcs) - domain-specific baseline - 7B dense

### Configuration Options

**Environment Variable:**
```bash
# Set default model
export PUNIE_MODEL=local
uv run punie serve

# Or inline
PUNIE_MODEL=local uv run punie serve
```

**Custom Server URL:**
```bash
# Use specific port/endpoint
uv run punie serve --model "local:http://localhost:8080/v1/default"
```

**Via Configuration File:**

Create `~/.jetbrains/acp.json`:
```json
{
  "model": "local:http://localhost:8080/v1/default"
}
```

Then simply run:
```bash
uv run punie serve
```

### Alternative: LM Studio

For users who prefer a GUI:

```bash
# 1. Start LM Studio (https://lmstudio.ai/)
#    - Download and install LM Studio
#    - Load a model in the UI
#    - Start the local server (default: http://localhost:1234)

# 2. Run Punie
uv run punie serve --model local
```

### Model Selection Guide

| Model | Use Case | Accuracy | Speed | Domains |
|-------|----------|----------|-------|---------|
| **Phase 7** | Full-stack web dev | 100% | ~12s | Python + HTML |
| **Phase 6** | Python projects | 100% | ~12s | Python (10+ frameworks) |
| **Phase 5** | Domain-specific | 100% | ~12s | svcs-di, tdom-svcs |
| Base (untrained) | Not recommended | 60% | ~8s | Generic (poor quality) |

**Recommendation:** Start with **Phase 7** for maximum flexibility. It handles both Python and HTML with no performance penalty compared to Phase 6.

**Training Data:**
- **Phase 7:** 824 examples (FastAPI, pytest, Flask, typer, click, httpx, starlette, pydantic, attrs, structlog + HTML)
- **Phase 6:** 794 examples (same Python frameworks, no HTML)
- **Phase 5:** 244 examples (svcs-di, tdom-svcs only)

**📊 For detailed performance metrics and training history, see [`MODEL_PERFORMANCE_TRACKER.md`](MODEL_PERFORMANCE_TRACKER.md)**

### Benefits of Local Models

- ✅ Zero API costs
- ✅ Privacy-sensitive codebases stay local
- ✅ No internet required (after initial model download)
- ✅ Fast response times (no API latency)
- ✅ Full tool calling support (read/write files, run commands)
- ✅ Works with any OpenAI-compatible server
- ✅ 100% discrimination accuracy (tool vs direct answer)

### Alternative Models (LM Studio)

If not using our trained models:
- Qwen2.5-Coder series (7B, 14B)
- DeepSeek-Coder series
- CodeLlama series
- Any GGUF model with tool calling support

### PyCharm Integration

**Step 1: Start the model server**

Choose your model:
```bash
# Full-stack (Python + HTML) - Recommended
uv run python -m mlx_lm.server \
  --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
  --adapter-path adapters_phase7 \
  --port 8080

# OR Python-only
uv run python -m mlx_lm.server \
  --model mlx-community/Qwen2.5-Coder-7B-Instruct-4bit \
  --adapter-path adapters_phase6 \
  --port 8080
```

**Step 2: Generate ACP configuration**
```bash
uv run punie init
```

This creates `~/.jetbrains/acp.json` with the Punie agent configuration.

**Step 3: Start Punie**
```bash
# Uses model server running on localhost:8080
uv run punie serve --model local

# Or with explicit URL
uv run punie serve --model "local:http://localhost:8080/v1/default"

# Or via environment variable
export PUNIE_MODEL=local
uv run punie serve
```

**Step 4: Connect PyCharm**

In PyCharm:
1. Go to Settings → Tools → AI Assistant
2. Select "Punie" as your AI assistant
3. Start coding! The agent will use your local model.

### Programmatic Usage

```python
from punie.agent.factory import create_pydantic_agent

# Create agent with local model (assumes LM Studio running)
agent = create_pydantic_agent(model='local')

# Or with specific model name
agent = create_pydantic_agent(model='local:my-model')

# Or with custom server URL
agent = create_pydantic_agent(model='local:http://localhost:8080/v1/custom')
```

See `examples/15_local_model_server.py` for a complete example.

## Architecture

Punie bridges three technologies:

### 1. Pydantic AI (Internal Engine)
- Type-safe agent framework with structured output
- Tool definitions with JSON schemas
- Dependency injection for clean testing
- Multi-model support (OpenAI, Anthropic, local servers via OpenAI-compatible API)

### 2. Agent Communication Protocol (IDE Integration)
- JSON-RPC 2.0 over stdio for IDE communication
- Tool call lifecycle notifications (start, progress, complete)
- Permission requests for destructive operations
- Real-time progress updates to IDE

### 3. MLX Models (Local Inference)
- Fully offline AI on Apple Silicon
- Tool calling via chat templates
- Zero API costs, complete privacy
- 50-200 tokens/sec on M1/M2/M3

### How They Connect

```text
PyCharm IDE              Punie Agent                 AI Model
    │                         │                          │
    │  1. User types prompt   │                          │
    │─────────────────────────>│                          │
    │                         │  2. Pydantic AI run      │
    │                         │─────────────────────────>│
    │                         │                          │
    │                         │  3. Model needs tool     │
    │                         │<─────────────────────────│
    │                         │                          │
    │  4. Request permission  │                          │
    │<─────────────────────────│                          │
    │                         │                          │
    │  5. User approves       │                          │
    │─────────────────────────>│                          │
    │                         │                          │
    │  6. Execute tool (ACP)  │                          │
    │<─────────────────────────│                          │
    │                         │                          │
    │  7. Return result       │                          │
    │─────────────────────────>│                          │
    │                         │  8. Continue with result │
    │                         │─────────────────────────>│
    │                         │                          │
    │                         │  9. Final response       │
    │                         │<─────────────────────────│
    │  10. Show to user       │                          │
    │<─────────────────────────│                          │
```

**Key Benefits:**
- **Testability** — Dependency injection enables testing without IDE
- **Flexibility** — Swap models (local ↔ cloud) without changing tools
- **Safety** — User controls all file writes and command execution
- **Visibility** — IDE shows real-time progress for all operations

## Performance ideas

Punie aims to be fast even on lower-end hardware. How? We'd like to investigate:

- Very targeted, slim models (perhaps tuned even further, for special tasks in Python)
- Move more of the work to the "deterministic" side:
    - Use default IDE machinery as "tools" in the agent
    - Easy to add even more IDE functions via IDE plugins
    - Extensive use of Python linters, formatters, and type checkers
    - Perhaps extend *those* by making it easy to add custom policies as "skills" but on the deterministic side
    - Explore Pydantic Monty for tool-running

## Documentation

### Project Documentation

- **[Model Performance Tracker](MODEL_PERFORMANCE_TRACKER.md)** — Complete training history, benchmarks, and phase comparisons (Phases 0-7)
- **[Product Roadmap](agent-os/product/roadmap.md)** — Project roadmap with completed and planned phases
- **[Development Diary](docs/diary/)** — Phase results and development notes
- **[Research Notes](docs/research/)** — Training methodology, datasets, and tools research

### Architecture & Training Specs

- **[Knowledge Distillation (Phase 17)](agent-os/specs/2026-02-13-knowledge-distillation/)** — Tool-calling training pipeline
- **[Model Fusion (Phase 18)](agent-os/specs/2026-02-13-model-fusion/)** — 8-bit fusion for optimal speed/memory
- **[Training Data Scaling (Phase 19)](agent-os/specs/2026-02-14-training-data-scaling/)** — Multi-domain training (Python + HTML)

## Research

- The [Agent Client Protocol](https://agentclientprotocol.com/get-started/introduction) home page describes ACP
- The ACP Python SDK has been vendored into `src/punie/acp/` for modification and Pydantic AI integration
- [Pydantic AI](~/PycharmProjects/pydantic-ai) is a local checkout of the Pydantic AI project, including a docs
  directory

## Task plan

- Get a good project setup: examples, tests, docs that match existing projects (svcs-di, tdom-svcs) and skills
- Add docs with deep research on python-sdk and Pydantic AI, to let the agent refer to later
- Get a good pytest setup that proves the existing python-sdk works correctly
- Refactor into a test-driven project
    - Copy the existing python-sdk into this project
    - Make sure it works
    - Refactor the tests to be more granular and pluggable
    - Mock the model calls
- Introduce an HTTP server into the asyncio loop (aiohttp, Starlette, etc.)
- Minimal transition to a Pydantic AI project
- Gradually port the python-sdk "tools" into Pydantic AI tools
- Convert to a best-practices Pydantic AI project