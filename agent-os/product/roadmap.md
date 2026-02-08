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

**Note:** Original task 2.4 (ModelResponder infrastructure) deferred to Phase 3 as enhancement. Replaced with general coverage/quality improvements which provide more immediate value.

## 3. Pydantic AI Migration
**Status:** In Progress (Phase 3.3 Complete)

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
  - Added 6 new Pydantic AI tools: write_file, run_command, get_terminal_output, release_terminal, wait_for_terminal_exit, kill_terminal
  - Implemented permission flow for write_file and run_command using Client.request_permission()
  - All tools use ToolCallTracker for lifecycle notifications (ToolCallStart → ToolCallProgress)
  - run_command is a compound tool (create_terminal → wait_for_exit → get_output → release)
  - Full test coverage: 12 Pydantic agent tests + 5 FakeClient terminal tests (83 tests total pass)
  - Type checking passes (ty), linting passes (ruff), all tests pass
  - Created spec documentation in agent-os/specs/2026-02-07-pydantic-ai-tools/
- [ ] 3.4 Convert to best-practices Pydantic AI project

## 4. ACP Integration
**Status:** Not Started

- [ ] 4.1 Implement dynamic tool discovery via ACP
- [ ] 4.2 Register IDE tools automatically
- [ ] 4.3 Enable agent awareness of PyCharm capabilities

## 5. Web UI Development
**Status:** Not Started

- [ ] 5.1 Design multi-agent tracking interface
- [ ] 5.2 Build browser-based monitoring dashboard
- [ ] 5.3 Implement agent interaction controls
- [ ] 5.4 Add simultaneous agent management features

## 6. Advanced Features
**Status:** Not Started

- [ ] 6.1 Create domain-specific skills and policies framework
- [ ] 6.2 Implement custom deterministic policies for project-specific rules
- [ ] 6.3 Add support for free-threaded Python (PEP 703)
- [ ] 6.4 Optimize for parallel agent operations across multiple cores

## Research

### Monty For Code Mode

**References:**
- [Pydantic Monty announcement](https://news.ycombinator.com/item?id=46920388)
- [Cloudflare Code Mode](https://blog.cloudflare.com/code-mode/)
- [Anthropic Programmatic Tool Calling](https://platform.claude.com/docs/en/agents-and-tools/tool-use/programmatic-tool-calling)

Pydantic introduced Monty as a radical improvement to agent tool execution performance. Similar work from Cloudflare and Anthropic shows this is a key area for optimization. Code mode allows agents to generate and execute tool calls programmatically rather than through traditional JSON-based tool use, resulting in:

- Faster tool invocation
- More efficient token usage
- Better agent reasoning about tool composition
- Reduced latency in multi-step workflows

**Relevance to Punie:** As Punie delegates tool execution to PyCharm via ACP, implementing code mode patterns could significantly improve performance, especially for complex multi-tool workflows. This could be particularly beneficial for the advanced features in Phase 6, where parallel agent operations and free-threaded execution would benefit from optimized tool calling patterns.
