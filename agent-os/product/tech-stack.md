# Tech Stack

## Language

- Python 3.14+

## Agent Framework

- Pydantic AI (pydantic-ai-slim>=0.1.0)
  - Used for internal agent engine (as of Phase 3.2)
  - Provides type-safe agent framework with tool support
  - TestModel for testing without LLM calls

## Protocol

- ACP (Agent Client Protocol) for IDE integration

## IDE

- PyCharm

## Local Models

- LM Studio (https://lmstudio.ai/) - Primary recommendation for user-friendly local model hosting
- mlx-lm.server - Alternative for Apple Silicon users who prefer command-line tools
- OpenAI-compatible API protocol (supports any compatible server: Ollama, llama.cpp, etc.)
- Pydantic AI's OpenAIChatModel + OpenAIProvider for unified cloud/local interface

## HTTP Server

- Starlette (ASGI framework, chosen for seamless Pydantic AI integration)
- uvicorn (ASGI server)

## Testing

- pytest

## Development Tools

- uv (package and project management)
- ruff (linting and formatting)
- ty (type checking)
