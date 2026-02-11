# Goals and Constraints

Make some notes that I can refer to in research.

## Constraints

- Apple M1
- 32 GB RAM
- Modern Python 3.12+
- Including 3.13/3.14 features
- Especially: PEP 750 template strings, tdom library
- Plus: HTML, CSS
- Minus: Most Python libraries and frameworks
- Agentic coding with tool loops

**Hardware:**
- Apple Silicon unified memory architecture
- All layers must fit in 32 GB (model + agent + tools)

**Language:**
- Python 3.14 specifically (project converged from "3.12+" to 3.14)
- Astral toolchain: ruff (lint/format), ty (type checking), uv (packages)

**Architecture:**
- Pydantic AI as internal agent engine
- ACP (Agent Communication Protocol) over stdio JSON-RPC for IDE communication
- PyCharm as primary IDE target
- stdout reserved for ACP JSON-RPC — no logging/output to stdout
- OpenAI-compatible API for local model servers — no custom Model implementation
- Model serving separated from agent logic

**Testing & Code Standards:**
- Frozen dataclasses for services and immutable state
- Fakes over mocks
- Function-based tests, never classes
- Protocol-first design
- Pure functions first, separate logic from I/O

## Goals

- Very small Python agentic coding environment
- Focused on a very limited kind of Python development (web components)
- Easy extensibility

**From mission:**
- Current coding agents don't leverage IDE capabilities — they reinvent the wheel
- Target: Python developers on modest hardware who want useful AI coding assistance without expensive cloud API costs
- Shift tool execution to the IDE via ACP — PyCharm's existing machinery becomes the agent's tool runtime

**From README:**
- Runs with local models
- Integrates into PyCharm via ACP
- Shifts more of the work of tools to the IDE via ACP
- HTTP loop for custom UX interaction
- Speed up "human-in-the-loop" with custom UI
- Track multiple agents running at once
- Embrace domain-specific customization to speed up agent and human performance

**From architecture:**
- Bridge PyCharm's IDE machinery with Pydantic AI via ACP
- Fully local, offline AI development on Apple Silicon
- Zero API cost for development/experimentation
- Privacy: sensitive codebases never leave the machine
- Support both cloud and local model backends seamlessly

## Ideas

- Gain performance by moving some work to the deterministic side with tools like Python linters, formatters, type
  checkers, LSPs
- Train a new model around agentic coding with new ideas on tool calling and structure

**Performance ideas from README:**
- Very targeted, slim models (perhaps tuned for special tasks in Python)
- Use default IDE machinery as "tools" in the agent
- Easy to add more IDE functions via IDE plugins
- Custom policies as "skills" on the deterministic side
- Explore Pydantic Monty for tool-running

**From research docs:**
- LSP as grounding mechanism: diagnostics, definitions, references provide ground-truth compiler feedback
- Compiler-in-the-loop: auto-run diagnostics after every edit
- Context engineering over fine-tuning: dynamic instruction assembly, scoped rules, prefix caching
- Memory and personalization layer: preferences, playbooks, graph-based recall
- Recursive language models for multi-file exploration beyond context window
- Multi-agent workflows: specialist agents for testing, refactoring, debugging
- Dynamic tool discovery from IDE capabilities
- Tree-sitter for structural code understanding and repo maps
- No open-source project yet integrates LSP actions + RL training + coding agent frameworks — research opportunity
- Ethical data sourcing for any future model training