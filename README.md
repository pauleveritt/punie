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
# Basic installation
uv pip install punie

# With local model support (macOS Apple Silicon only)
uv pip install 'punie[local]'
```

## Usage

### Local MLX Models (Offline Development)

Run Punie completely offline using local MLX models on Apple Silicon:

```bash
# Use default local model (Qwen2.5-Coder-7B-Instruct-4bit)
punie serve --model local

# Or set via environment variable
PUNIE_MODEL=local punie serve

# Use a specific model
punie serve --model local:mlx-community/Qwen2.5-Coder-3B-Instruct-4bit
```

**Recommended models:**
- `mlx-community/Qwen2.5-Coder-7B-Instruct-4bit` (default) - ~4GB, best balance
- `mlx-community/Qwen2.5-Coder-3B-Instruct-4bit` - ~2GB, faster for simple tasks
- `mlx-community/Qwen2.5-Coder-14B-Instruct-4bit` - ~8GB, highest quality

**Benefits:**
- Zero API costs
- Privacy-sensitive codebases stay local
- No internet required (after initial model download)
- Fast response times (no API latency)
- Full tool calling support (read/write files, run commands)

**Requirements:**
- macOS with Apple Silicon (M1/M2/M3/M4)
- 8GB+ unified memory (16GB+ for 14B model)

### PyCharm Integration

1. Generate ACP configuration:
   ```bash
   punie init
   ```

2. Start the agent:
   ```bash
   punie serve --model local
   ```

3. In PyCharm, select Punie as your AI assistant

### Programmatic Usage

```python
from punie.agent.factory import create_pydantic_agent

# Create agent with local model
agent = create_pydantic_agent(model='local')

# Or with custom model
agent = create_pydantic_agent(model='local:mlx-community/Qwen2.5-Coder-3B-Instruct-4bit')
```

See `examples/15_mlx_local_model.py` for a complete example.

## Architecture

Punie bridges three technologies:

### 1. Pydantic AI (Internal Engine)
- Type-safe agent framework with structured output
- Tool definitions with JSON schemas
- Dependency injection for clean testing
- Multi-model support (OpenAI, Anthropic, local MLX)

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
- Use free-threaded Python (if possible) to tap into more cores

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