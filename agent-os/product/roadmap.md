# Product Roadmap

## 1. Project Foundation

**Status:** ✅ Completed

- [x] 1.1 Set up project structure matching existing projects (svcs-di, tdom-svcs)
- [x] 1.2 Create comprehensive examples (10 examples: 01-09 + hello_world)
- [x] 1.3 Add documentation with deep research on python-sdk and Pydantic AI
- [x] 1.4 Configure pytest setup proving python-sdk works correctly

## 2. Test-Driven Refactoring

**Status:** ✅ Completed (2026-02-07)

**Accomplished:**

- [x] 2.1 Vendor ACP SDK from upstream into `src/punie/acp/` (29 files)
    - Fixed absolute import in router.py
    - Added @runtime_checkable to Agent and Client protocols
    - Excluded schema.py from ruff (auto-generated)
    - Documented vendoring in src/punie/acp/VENDORED.md

- [x] 2.2 Transition all imports from `acp` to `punie.acp` and remove pip dependency
    - Updated 12 files (~16 import lines)
    - Removed agent-client-protocol pip package
    - Added pydantic>=2.0 as direct dependency

- [x] 2.3 Refactor tests: split by concern, create `punie.testing` package with protocol satisfaction tests
    - Created src/punie/testing/ with FakeAgent, FakeClient, LoopbackServer
    - Split tests/test_acp_sdk.py into 5 focused modules by concern
    - Added tests/test_protocol_satisfaction.py with runtime isinstance() tests
    - Added tests/test_fakes.py with 39 comprehensive tests
    - Achieved 100% coverage on punie.testing package

- [x] 2.4 Test coverage and quality improvements
    - Improved overall coverage from 76% to 82% (exceeds 80% target)
    - Fixed all 7 type errors in examples
    - Cleaned 5 unused type: ignore directives in vendored SDK
    - Added public API exports to src/punie/__init__.py
    - Created comprehensive documentation (PROJECT_REVIEW.md, IMPROVEMENTS_SUMMARY.md)

**Test Suite:** 65 tests passing (26 → 65, +39 new tests)
**Coverage:** 82% (76% → 82%, +6%)
**Type Safety:** All examples pass ty type checking
**Quality:** Ruff ✅, Ty ✅ (new code), All tests ✅

**Note:** Original task 2.4 (ModelResponder infrastructure) deferred to Phase 3 as enhancement. Replaced with general
coverage/quality improvements which provide more immediate value.

## 3. Pydantic AI Migration

**Status:** ✅ Completed (2026-02-08)

- [x] 3.1 HTTP server alongside ACP (dual-protocol foundation) - Completed 2026-02-07
    - Added Starlette + uvicorn HTTP server running concurrently with ACP stdio
    - Created `run_dual()` function using asyncio.wait(FIRST_COMPLETED)
    - Implemented `/health` and `/echo` endpoints for architecture validation
    - Full test coverage: 6 unit tests (TestClient) + 2 integration tests (subprocess)
    - No changes to vendored ACP code - clean separation of concerns
    - Proven architecture: both protocols work simultaneously in same event loop
- [x] 3.2 Minimal transition to Pydantic AI project structure - Completed 2026-02-07
    - Added pydantic-ai-slim>=0.1.0 as dependency
    - Created `src/punie/agent/` package with ACPDeps, ACPToolset, PunieAgent, and factory
    - PunieAgent adapter bridges ACP Agent protocol to Pydantic AI Agent.run()
    - ACPToolset provides read_file tool (wraps Client.read_text_file)
    - Replaced MinimalAgent with PunieAgent in test fixtures
    - Full test coverage: 8 unit tests + all integration tests pass (84 tests total)
    - Type checking passes (ty), linting passes (ruff), coverage >80%
    - Session IDs changed from "test-session-N" to "punie-session-N"
- [x] 3.3 Port all ACP Client tools to Pydantic AI - Completed 2026-02-08
    - Implemented FakeClient terminal methods with in-memory state (FakeTerminal dataclass)
    - Added 6 new Pydantic AI tools: write_file, run_command, get_terminal_output, release_terminal,
      wait_for_terminal_exit, kill_terminal
    - Implemented permission flow for write_file and run_command using Client.request_permission()
    - All tools use ToolCallTracker for lifecycle notifications (ToolCallStart → ToolCallProgress)
    - run_command is a compound tool (create_terminal → wait_for_exit → get_output → release)
    - Full test coverage: 12 Pydantic agent tests + 5 FakeClient terminal tests (83 tests total pass)
    - Type checking passes (ty), linting passes (ruff), all tests pass
    - Created spec documentation in agent-os/specs/2026-02-07-pydantic-ai-tools/
- [x] 3.4 Convert to best-practices Pydantic AI project - Completed 2026-02-08
    - Migrated from `system_prompt=` to `instructions=` (v1 idiom) with rich PUNIE_INSTRUCTIONS constant
    - Added ModelSettings(temperature=0.0, max_tokens=4096) for deterministic coding behavior
    - Configured retry policies: retries=3 (tools), output_retries=2 (validation)
    - Registered output validator to reject empty/whitespace-only responses via ModelRetry
    - Implemented ModelRetry error handling in all 7 tools (tracked + simple patterns)
    - Added error handling in adapter: catches UsageLimitExceeded and general exceptions
    - Added usage_limits parameter to PunieAgent for token/request control
    - Moved tracker.forget() to finally blocks to prevent leaked tool calls
    - Full test coverage: 8 new tests (factory config, output validation, adapter errors) - 20 total agent tests
    - Type checking passes (ty), linting passes (ruff), formatting passes (ruff format)
    - All 91 tests pass, coverage 81.12% (exceeds 80% requirement)
    - Created spec documentation in agent-os/specs/2026-02-08-pydantic-ai-best-practices/

## 4. Dynamic Tool Discovery

**Status:** ✅ Phase 4.1-4.2 Completed (2026-02-08)

- [x] 4.1 Implement dynamic tool discovery via ACP - Completed 2026-02-08
    - Extended Client protocol with `discover_tools()` method (Punie extension, not upstream)
    - Created discovery schema: ToolDescriptor and ToolCatalog (frozen dataclasses with query methods)
    - Implemented three-tier toolset fallback system:
        - Tier 1: Catalog-based (discover_tools returns tool descriptors from IDE)
        - Tier 2: Capability-based (client_capabilities flags when discovery unavailable)
        - Tier 3: Default (all 7 static tools for backward compatibility)
    - Added dynamic toolset factories: create_toolset_from_catalog(), create_toolset_from_capabilities()
    - Generic bridge for unknown IDE tools (forwards to ext_method)
    - Per-session Pydantic AI agent construction with session-specific toolset
    - Updated PunieAgent to store client_capabilities and wire discovery into prompt()
    - Extended FakeClient with discover_tools() support for testing
    - Cleaned up dead code: removed unused _sessions set from adapter
    - Full test coverage: 16 new discovery tests (frozen dataclass verification, catalog queries, toolset factories, adapter integration, fallback chain)
    - Updated example 09 from aspirational Tier 3 to working Tier 1 demonstration
    - Type checking passes (ty), linting passes (ruff), all 143 tests pass
    - Created spec documentation in agent-os/specs/2026-02-08-1030-dynamic-tool-discovery/
    - Updated docs/research/evolution.md with Phase 4.1 details
- [x] 4.2 Register IDE tools automatically - Completed 2026-02-08
    - Created SessionState frozen dataclass for immutable session-scoped caching
    - Moved tool discovery from per-prompt to session lifecycle (new_session())
    - Extracted _discover_and_build_toolset() helper from prompt()
    - Added _sessions dict mapping session_id → SessionState
    - Simplified prompt() to use cached agent from _sessions (no re-discovery)
    - Implemented lazy fallback for unknown session IDs (backward compatibility)
    - Extended FakeClient with discover_tools_calls tracking for tests
    - Legacy agent mode skips registration (preserves existing behavior)
    - Full test coverage: 16 new session registration tests (frozen dataclass, registration in new_session, cached state usage, lazy fallback, legacy compatibility)
    - Created working example: examples/10_session_registration.py
    - Type checking passes (ty), linting passes (ruff), all 123 tests pass
    - Created spec documentation in agent-os/specs/2026-02-08-1400-session-registration/
    - Updated docs/research/evolution.md with Phase 4.2 details
- [ ] 4.3 Enable agent awareness of PyCharm capabilities

## 5. CLI Development

**Status:** Phase 5.1, 5.2, 5.4 Completed (2026-02-08) | Phase 5.3 Deferred

**References:**
- [JetBrains acp.json documentation](https://www.jetbrains.com/help/ai-assistant/acp.html#add-custom-agent)

- [x] 5.1 Implement Typer-based CLI with uvx support - Completed 2026-02-08
    - Created `punie` command (default stdio/ACP mode) via `[project.scripts]` entry point
    - Enabled `uvx punie` invocation without package installation
    - Added CLI flags: `--model` (overrides PUNIE_MODEL env var), `--name`, `--log-dir`, `--log-level`, `--version`
    - Implemented file-only logging with RotatingFileHandler (~10MB, 3 backups) to `~/.punie/logs/punie.log`
    - Critical constraint respected: stdout reserved for ACP JSON-RPC, all logging goes to files
    - Version flag writes to stderr (not stdout) for protocol compatibility
    - Added `python -m punie` support via `__main__.py`
    - Modern agent construction: `PunieAgent(model=model, name=name)` with `run_agent()` from `punie.acp`
    - Full test coverage: 10 function-based tests (resolve_model, setup_logging, CLI flags)
    - Type checking passes (ty), linting passes (ruff), all 144 tests pass (134 existing + 10 new)
    - Created spec documentation in agent-os/specs/2026-02-08-cli-development/
    - Created working example: examples/11_cli_usage.py
    - Updated docs/research/evolution.md with Phase 5.1 details
- [x] 5.2 Add config generation command - Completed 2026-02-08
    - Implemented `punie init` subcommand
    - Generates acp.json at ~/.jetbrains/acp.json (configurable via --output)
    - Auto-detects Punie executable (system PATH or uvx fallback)
    - Merges with existing config to preserve other agents
    - Optional --model flag to pre-configure PUNIE_MODEL in env
    - Pure functions for testability: resolve_punie_command(), generate_acp_config(), merge_acp_config()
    - Full test coverage: 13 tests (9 pure function + 4 CLI integration)
    - Type checking passes (ty), linting passes (ruff), all tests pass
    - Created spec documentation in agent-os/specs/2026-02-08-init-command/
    - Created working example: examples/12_init_config.py
- [~] 5.3 Add model download command - Deferred
    - Decision deferred until local model strategy is decided
    - Will implement when there's clarity on recommended models and storage patterns
- [x] 5.4 Add HTTP/WebSocket server mode - Completed 2026-02-08
    - Implemented `punie serve` subcommand
    - Runs dual-protocol mode: ACP stdio + HTTP server concurrently
    - Reuses existing infrastructure: PunieAgent, create_app(), run_dual()
    - Added HTTP-specific flags: --host (default 127.0.0.1), --port (default 8000)
    - Supports all standard flags: --model, --name, --log-dir, --log-level
    - Async helper function: run_serve_agent() for clean separation of concerns
    - Full test coverage: 6 tests (1 async helper + 5 CLI integration)
    - Type checking passes (ty), linting passes (ruff), all tests pass
    - Created spec documentation in agent-os/specs/2026-02-08-serve-command/
    - Created working example: examples/13_serve_dual.py

## 6. Web UI Development

**Status:** Not Started

- [ ] 6.1 Design multi-agent tracking interface
- [ ] 6.2 Build browser-based monitoring dashboard
- [ ] 6.3 Implement agent interaction controls
- [ ] 6.4 Add simultaneous agent management features

## 7. Performance

**Status:** Not Started

- [ ] 7.1 Measure agent performance using ACP tools vs. native tools
- [ ] 7.2 Benchmark tool execution latency across protocols
- [ ] 7.3 Profile memory usage and token consumption patterns
- [ ] 7.4 Identify bottlenecks in IDE tool delegation

## 8. Advanced Features

**Status:** Not Started

- [ ] 8.1 Create domain-specific skills and policies framework
- [ ] 8.2 Implement custom deterministic policies for project-specific rules
- [ ] 8.3 Add support for free-threaded Python (PEP 703)
- [ ] 8.4 Optimize for parallel agent operations across multiple cores

## Research

### Monty For Code Mode

**References:**

- [Pydantic Monty announcement](https://news.ycombinator.com/item?id=46920388)
- [Cloudflare Code Mode](https://blog.cloudflare.com/code-mode/)
- [Anthropic Programmatic Tool Calling](https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling)

Pydantic introduced Monty as a radical improvement to agent tool execution performance. Similar work from Cloudflare and
Anthropic shows this is a key area for optimization. Code mode allows agents to generate and execute tool calls
programmatically rather than through traditional JSON-based tool use, resulting in:

- Faster tool invocation
- More efficient token usage
- Better agent reasoning about tool composition
- Reduced latency in multi-step workflows

**Relevance to Punie:** As Punie delegates tool execution to PyCharm via ACP, implementing code mode patterns could
significantly improve performance, especially for complex multi-tool workflows. This could be particularly beneficial
for the advanced features in Phase 6, where parallel agent operations and free-threaded execution would benefit from
optimized tool calling patterns.

### Extensible Deterministic Tools

**References:** None

- Better/faster/cheaper/local
- Extensible

**Relevance to Punie:** Moving the work to deterministic tools like PyCharm is the point of Punie. But some work can
also be moved to existing deterministic Python tools such as linters, formatters, type checkers, and LSPs.

### Pydantic AI Skills

pydantic-ai-skills: A standardized framework that implements Anthropic’s Agent Skills framework specifically for
Pydantic AI.

Pydantic-DeepAgents: An extension of the core library that introduces a SkillsToolset. This allows agents to load
domain-specific markdown prompts and executable code on demand.

In the core framework, the "Skills" philosophy—packaging expertise and tools into reusable modules—is handled by three
features:

- Dynamic Toolsets: You can register collections of tools (toolsets) with an agent in one go. This allows you to "equip"
  an agent with a "Coding Skill" or a "Research Skill" by swapping toolsets.
- Progressive Disclosure via MCP: By connecting to Model Context Protocol (MCP) servers, Pydantic AI can dynamically
  discover and load only the tools it needs for a specific task, mimicking the efficiency of "Skills" without bloating
  the
  initial context window.
- Dynamic Instructions: Using the @agent.instructions decorator, you can inject complex behavioral patterns and domain
  knowledge into the agent's prompt based on the runtime context, which effectively acts as a "soft skill".
