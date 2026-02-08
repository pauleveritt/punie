# References

## ACP Python SDK

**Local Checkout:** `~/PycharmProjects/python-acp-sdk/`

**Version:** v0.7.1

**PyPI Package:** `agent-client-protocol`

**Key Files:**
- `acp/schema.py` — Auto-generated Pydantic models from schema.json
- `acp/interfaces.py` — Agent and Client Protocol classes
- `acp/helpers.py` — Tool call builder functions
- `acp/contrib/tool_call_tracker.py` — Server-side tool call state management
- `acp/contrib/permission_broker.py` — Permission request coordination
- `acp/contrib/session_accumulator.py` — Client-side state merging
- `tests/test_rpc.py` — _ExampleAgent showing tool call lifecycle
- `tests/golden/` — JSON wire format examples

**Critical Sections for Punie:**
- Tool call lifecycle (ToolCallStart, ToolCallProgress, request_permission)
- ToolCallTracker for managing concurrent tool calls
- Helper functions for building tool call notifications

## Pydantic AI

**Local Checkout:** `~/PycharmProjects/pydantic-ai/`

**Key Files:**
- `pydantic_ai/agent.py` — Agent class and run modes
- `pydantic_ai/tools.py` — Tool and Toolset abstractions
- `pydantic_ai/dependencies.py` — RunContext and dependency injection
- `docs/` — Comprehensive documentation and examples

**Critical Sections for Punie:**
- AbstractToolset API (the ACP bridge point)
- RunContext dependency injection pattern
- Multi-agent patterns (delegation, hand-off)

**Related Issues:**
- Issue #1742 — ACP support declined (not a standard protocol yet)

## Punie Codebase

**Current State:**
- Phase 1 (Baseline) complete
- Phase 2 (Agent OS) in progress (documentation)
- Phases 3-4 pending (Pydantic AI migration, ACP integration)

**Relevant Files:**
- `agent-os/product/roadmap.md` — Full roadmap with phases
- `docs/conftest.py` — Sybil configuration (collects Python code blocks)
- `CLAUDE.md` — Project standards and workflow

## External Resources

**ACP Specification:**
- Protocol specification at Zed Industries repo (not referenced in local SDK)

**Pydantic AI Documentation:**
- Official docs at pydantic.ai
- FastAPI-style developer experience
- Model-agnostic (OpenAI, Anthropic, Gemini, Ollama, etc.)
