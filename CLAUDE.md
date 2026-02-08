# Claude Instructions for Punie

Punie is an experimental AI coding agent that delegates tool execution to PyCharm via the Agent Communication Protocol (ACP).

## Project Standards

- Use Astral tools directly via skills (`astral:ruff`, `astral:ty`, `astral:uv`), not justfile recipes
- Write function-based tests, never classes
- Use Sybil for doctest integration in README.md and docstrings

## Agent OS Integration

This project uses Agent OS for standards, skills, and commands:
- Standards in `agent-os/standards/`
- Skills in `agent-os/skills/`
- Commands in `agent-os/commands/`
- Roadmap in `agent-os/product/roadmap.md`
- Specs in `agent-os/specs/`

## Development Workflow

- **No auto-commit**: Always ask before creating commits
- **Verification**: Use `astral:ruff` and `astral:ty` skills for quality checks
- **Testing**: Run `uv run pytest` directly, not `just test`
- **Documentation**: Markdown files (MyST) in `docs/`, built with Sphinx + Furo

## Python Version

This project uses Python 3.14 for modern language features.
