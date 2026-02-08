# Tech Stack

## Language

- Python (targeting modern Python, with an eye toward free-threaded Python in the future)

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

- To be determined (exploring options like Ollama)

## HTTP Server

- Starlette (ASGI framework, chosen for seamless Pydantic AI integration)
- uvicorn (ASGI server)

## Testing

- pytest

## Development Tools

- uv (package and project management)
- ruff (linting and formatting)
- ty (type checking)
