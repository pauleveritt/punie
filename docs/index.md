# Punie

AI coding agent that delegates tool execution to PyCharm via the Agent Communication Protocol (ACP).

## About

Punie is an experimental agent that enables AI-assisted development with IDE-native tooling by delegating tool execution
to PyCharm through ACP.

## Features

Punie bridges complementary technologies:

- **Pydantic AI** — Type-safe agent framework with structured output and dependency injection
- **ACP** — Agent Communication Protocol for IDE integration (PyCharm, VS Code, etc.)
- **MLX** — Local model support for offline development on Apple Silicon

The bridge enables:

- **IDE Integration:** Native file operations, terminal execution, permission controls
- **Local Models:** Fully offline AI using MLX on Apple Silicon (zero API costs)
- **Tool Calling:** Complete tool execution support for both cloud and local models
- **Type Safety:** End-to-end type checking with Pydantic
- **Progress Visibility:** Real-time updates for all agent actions

### Local Model Support

Run Punie completely offline with local MLX models:

- **Zero costs** — No API charges
- **Privacy** — Sensitive code never leaves your machine
- **Offline** — No internet required after model download
- **Fast** — No API latency, instant responses
- **Full tool calling** — Read/write files, run commands locally

Supports Qwen2.5-Coder models (3B, 7B, 14B) with 4-bit quantization for Apple Silicon.

```bash
# Install with local support (macOS arm64)
uv pip install 'punie[local]'

# Run with local model
punie serve --model local
```

## Documentation

```{toctree}
:maxdepth: 2
:caption: Research

flywheel

research/evolution
research/architecture
research/acp-sdk
research/pydantic-ai
diary/index
```

## Indices and tables

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
