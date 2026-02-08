# Punie

AI coding agent that delegates tool execution to PyCharm via the Agent Communication Protocol (ACP).

## About

Punie is an experimental agent that enables AI-assisted development with IDE-native tooling by delegating tool execution to PyCharm through ACP.

## Features

Punie bridges two complementary technologies:

- **Pydantic AI** — Type-safe agent framework with structured output and dependency injection
- **ACP** — Agent Communication Protocol for IDE integration (PyCharm, VS Code, etc.)

The bridge enables:
- IDE-native file operations (read, write, search)
- Terminal command execution with streaming output
- User permission controls for destructive operations
- Progress visibility for all agent actions
- Type-safe tool definitions and results

## Documentation

```{toctree}
:maxdepth: 2
:caption: Research

research/architecture
research/acp-sdk
research/pydantic-ai
```

## Indices and tables

* {ref}`genindex`
* {ref}`modindex`
* {ref}`search`
