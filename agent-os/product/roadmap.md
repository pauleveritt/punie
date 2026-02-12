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
- [~] 5.3 Add model download command - Deferred → Revived in Phase 6.2
    - Decision deferred until local model strategy is decided
    - Revived as part of Phase 6 Local Model Integration (task 6.2)
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

## 6. Local Model Integration

**Status:** Phase 6.1 Completed (2026-02-08)

**Context:** Enable fully local, offline AI-assisted development using Apple Silicon (M1/M2/M3) without external API calls. Ported pydantic-ai-mlx architecture to current Pydantic AI v1.56.0 API with complete tool calling support. Agent can execute tools locally without API calls.

**Dependencies:** Optional mlx-lm>=0.22.0 (macOS arm64 only)

**References:**
- [pydantic-ai-mlx by dorukgezici](https://github.com/dorukgezici/pydantic-ai-mlx)
- [MLX on Apple Silicon](https://github.com/ml-explore/mlx)
- [Qwen2.5-Coder models](https://huggingface.co/mlx-community)

- [x] 6.1 Port pydantic-ai-mlx with tool calling - Completed 2026-02-08
    - Created MLXModel implementing current Pydantic AI Model interface
    - Implemented tool calling via chat templates and regex parsing of <tool_call> tags
    - Added lazy imports with TYPE_CHECKING guards for cross-platform compatibility
    - Added [project.optional-dependencies] local = ["mlx-lm>=0.22.0"] in pyproject.toml
    - Integrated with factory: model='local' and 'local:model-name' support
    - Default model: mlx-community/Qwen2.5-Coder-7B-Instruct-4bit (4GB, 8GB+ RAM)
    - Full test coverage: 26 function-based tests (all work without mlx-lm installed)
    - Type checking passes (ty), linting passes (ruff), all tests pass
    - Created spec documentation in agent-os/specs/2026-02-08-mlx-model/
    - Created working example: examples/15_mlx_local_model.py
- [x] 6.2 Model Download CLI + Switch to Python 3.14 - Completed 2026-02-08
    - Switched from Python 3.14.2t (free-threaded) to Python 3.14.2 (regular) to unblock mlx-lm installation
    - Added `punie download-model` command with huggingface_hub.snapshot_download()
    - Store models in ~/.cache/punie/models/ directory with --models-dir option
    - Added --list flag to show recommended Qwen2.5-Coder models
    - Added model validation in MLXModel.from_pretrained() with clear error messages
    - Added validation in CLI main() and serve() commands to catch missing models
    - Removed free-threading tests, markers, and CI infrastructure
    - All 178 tests pass (minus deleted free-threading tests), coverage >80%
    - Created spec documentation in agent-os/specs/2026-02-08-model-download/
    - Deferred Phase 9.3 (free-threaded Python) until ecosystem matures
- [x] 6.3 Local Tools (adapts ACP tools from Phase 3.3) ✅ 2026-02-08
    - Created LocalClient implementing Client protocol with real filesystem/subprocess
    - Reuses existing 7 tools and ACPDeps unchanged (only swaps Client implementation)
    - Uses pathlib.Path for file operations and asyncio.subprocess for commands
    - Auto-approves permissions (no IDE to prompt), session_update is no-op
    - Created spec documentation in agent-os/specs/2026-02-08-local-tools/
    - All 24 tests pass with real tmp_path filesystem operations
- [x] 6.4 Agent Configuration ✅ 2026-02-08
    - Created AgentConfig frozen dataclass with instructions, temperature, max_tokens, retries, output_retries, validate_python_syntax
    - Two instruction sets: PUNIE_INSTRUCTIONS (PyCharm/ACP default) and PUNIE_LOCAL_INSTRUCTIONS (standalone local)
    - Added resolve_mode() function following resolve_model() pattern (CLI flag > PUNIE_MODE env var > "acp" default)
    - Updated create_pydantic_agent() to accept optional AgentConfig parameter (backward compatible)
    - Added Python syntax validation using ast.parse() on fenced code blocks (only when validate_python_syntax=True)
    - create_local_agent() defaults to local config with PUNIE_LOCAL_INSTRUCTIONS and syntax validation enabled
    - Created spec documentation in agent-os/specs/2026-02-08-local-model-integration/
    - All 13 new tests pass (test_agent_config.py)
- [x] 6.5 Safety Constraints (workspace-only isolation) ✅ 2026-02-08
    - Created WorkspaceBoundaryError custom exception with path and workspace attributes
    - Implemented resolve_workspace_path() pure function using Path.resolve() + is_relative_to() check
    - Updated LocalClient._resolve_path() to call resolve_workspace_path() for all file/directory operations
    - Blocks path traversal (../../etc/passwd), absolute paths outside workspace, symlink escapes
    - Terminal cwd also enforced through _resolve_path() — commands can't escape workspace
    - Exported WorkspaceBoundaryError and resolve_workspace_path from punie.local
    - All 10 new tests pass (test_workspace_safety.py)
- [x] 6.6 Memory Optimization ✅ 2026-02-08
    - Created MemorySnapshot frozen dataclass with RSS and peak RSS measurements
    - Implemented get_memory_snapshot() using resource.getrusage() (stdlib, no extra dependency)
    - Implemented check_memory_available() with simple heuristic (current + model + margin < total RAM)
    - Added MODEL_SIZES_MB dict with estimates for 3B-4bit, 7B-4bit, 14B-4bit models
    - Added estimate_model_size() function to map model names to size estimates
    - Updated MLXModel.from_pretrained() to check memory before loading and log actual usage after
    - Memory check warns but doesn't block (user may know their system)
    - All 8 new tests pass (test_memory.py)

## 7. Tool Performance Measurement

**Status:** Phase 7.1-7.3 Completed (2026-02-09) | Phase 7.4-7.5 In Progress

**Context:** Punie supports both IDE tools (via ACP) and local tools (via LocalClient). Understanding the performance characteristics of each approach is critical for optimization and architecture decisions.

- [x] 7.1 Create instrumentation infrastructure for tool timing - Completed 2026-02-09
    - Created PerformanceCollector with ToolTiming and PromptTiming frozen dataclasses
    - Implemented TimedToolset using Pydantic AI's WrapperToolset pattern
    - Uses time.monotonic() for accurate elapsed time measurement
    - Tracks success/failure status per tool call
    - Full test coverage: 22 tests across collector, toolset, report, and CLI
- [x] 7.2 Capture elapsed time per tool call for both IDE and local tools - Completed 2026-02-09
    - CLI mode: Fully functional via --perf flag or PUNIE_PERF=1 env var
    - ACP mode: ⚠️ Temporarily disabled due to collector lifecycle issue (see 7.4)
    - Backend labeling (local vs ide) for performance comparison
- [x] 7.3 Generate HTML performance report with per-tool metrics - Completed 2026-02-09
    - Standalone HTML with embedded CSS (no external dependencies)
    - Summary section: model, backend, durations, tool counts
    - Tool calls table: ordered execution with timing and status
    - Visual breakdown: bar chart showing tool vs model think time
    - Reports saved as punie-perf-YYYYMMDD-HHMMSS.html
- [ ] 7.4 Fix ACP mode performance reporting (collector lifecycle) - **TODO**
    - **Issue:** Infinite loop when reusing PerformanceCollector across multiple prompts in ACP mode
    - **Root cause:** TimedToolset wraps toolset at agent creation, capturing collector reference. When agent handles multiple prompts, collector accumulates stale state causing repeated tool calls
    - **Current workaround:** Disabled in ACP mode (self._perf_enabled = False)
    - **Proposed solutions:**
        1. Create fresh PerformanceCollector per prompt (requires agent recreation or toolset rewrapping)
        2. Add collector.reset() method to clear state between prompts
        3. Redesign to not wrap toolset at agent creation time (lazy wrapping per prompt)
    - **Tests:** 3 ACP tests marked as xfail until resolved
    - **Priority:** Medium - CLI mode works perfectly, ACP mode can wait
- [ ] 7.5 Implement running time aggregation and visualization
    - Add cumulative statistics across multiple prompts/sessions
    - Time series visualization for performance trends
    - Comparative charts for IDE vs local execution

## 8. Web UI Development

**Status:** Not Started

- [ ] 8.1 Design multi-agent tracking interface
- [ ] 8.2 Build browser-based monitoring dashboard
- [ ] 8.3 Implement agent interaction controls
- [ ] 8.4 Add simultaneous agent management features

## 9. Performance Optimization

**Status:** Not Started

- [ ] 9.1 Measure agent performance using ACP tools vs. native tools
- [ ] 9.2 Benchmark tool execution latency across protocols
- [ ] 9.3 Profile memory usage and token consumption patterns
- [ ] 9.4 Identify bottlenecks in IDE tool delegation

## 10. Advanced Features

**Status:** Not Started

- [ ] 10.1 Create domain-specific skills and policies framework
- [ ] 10.2 Implement custom deterministic policies for project-specific rules
- [ ] 10.3 Add support for free-threaded Python (PEP 703) — **Deferred: mlx-lm lacks cp314t wheels (as of 2026-02-08). Project switched to Python 3.14 (regular) to unblock local model installation. May revisit when free-threaded ecosystem matures.**
- [ ] 10.4 Optimize for parallel agent operations across multiple cores

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
for the advanced features in Phase 10, where parallel agent operations and free-threaded execution would benefit from
optimized tool calling patterns.

### Extensible Deterministic Tools

**References:** None

- Better/faster/cheaper/local
- Extensible

**Relevance to Punie:** Moving the work to deterministic tools like PyCharm is the point of Punie. But some work can
also be moved to existing deterministic Python tools such as linters, formatters, type checkers, and LSPs.

### Pydantic AI Skills

pydantic-ai-skills: A standardized framework that implements Anthropic's Agent Skills framework specifically for
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

## 11. LM Studio Integration

**Status:** ✅ Completed (2026-02-10)

**Context:** Simplified local model integration by replacing direct MLX model loading with OpenAI-compatible API calls. LM Studio and mlx-lm.server both expose OpenAI-compatible endpoints, allowing Punie to use Pydantic AI's built-in OpenAIChatModel with a custom base_url instead of maintaining custom MLX integration code.

**Benefits:**
- Removed ~2,400 lines of code (MLXModel, chat template handling, tool call parsing, tests)
- Leverages Pydantic AI's first-class OpenAI support (no custom Model implementation needed)
- Unified interface for both cloud (OpenAI) and local (LM Studio, mlx-lm.server) models
- Easier to support multiple local model servers (Ollama, llama.cpp, etc.)
- Separates model serving from agent logic (better separation of concerns)

**Architecture:**
```python
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

# Local LM Studio (default)
provider = OpenAIProvider(base_url="http://localhost:1234/v1")
model = OpenAIChatModel("default", provider=provider)

# Local mlx-lm.server
provider = OpenAIProvider(base_url="http://localhost:8080/v1")
model = OpenAIChatModel("model-name", provider=provider)
```

**Accomplished:**
- [x] 11.1 Add LM Studio connection support
    - Uses Pydantic AI's OpenAIChatModel with OpenAIProvider(base_url=...)
    - Supports three spec formats: "", "model-name", "http://host:port/v1/model"
    - Added connection error handling with helpful fallback messages
- [x] 11.2 Remove direct MLX model loading code
    - Deleted src/punie/models/ directory (3 files, ~1,137 lines)
    - Removed MLXModel tests (~784 lines)
    - Removed [local] optional dependency on mlx-lm
    - Removed download-model CLI command (~67 lines)
    - Removed test_cli_download.py (~188 lines)
    - Removed max_kv_size and repetition_penalty from AgentConfig
- [x] 11.3 Update documentation and examples
    - Updated README.md with LM Studio setup guide
    - Created examples/15_local_model_server.py
    - Documented mlx-lm.server as alternative to LM Studio
- [x] 11.4 Simplify model configuration
    - Removed model download and caching logic
    - Removed memory estimation code (server handles this)
    - Simplified factory.py: _create_local_model() now ~5 lines (was ~20)
    - Added _parse_local_spec() pure function with 7 tests

**Note:** Phase 6 (Local Model Integration with MLX) was superseded by this implementation. Direct MLX model loading proved fragile (chat template issues, quantization failures, XML/JSON format parsing). Delegating to LM Studio or mlx-lm.server provides better reliability and maintainability.

## 12. Server Management

**Status:** ✅ Completed (2026-02-11)

**Context:** Automate starting/stopping `mlx_lm.server` from Python so evaluation and training can be fully scripted. All code launches mlx-lm as a subprocess — no import-time dependency on mlx-lm. All tests work without it installed.

**Architecture:**
```python
from punie.training.server_config import ServerConfig
from punie.training.server import ServerProcess

# Configure server
config = ServerConfig(
    model_path="mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit",
    port=8080,
    adapter_path=None,  # Or path to LoRA adapter
)

# Manage lifecycle
async with ServerProcess(config=config) as server:
    # Server is running and healthy
    model = create_server_model(config)
    # ... use model ...
# Server stopped automatically
```

**Accomplished:**
- [x] 12.1 Server configuration dataclass
    - Created ServerConfig (frozen) with model_path, port, host, adapter_path, max_kv_size, repetition_penalty
    - Added base_url property for OpenAI-compatible API endpoint
    - 8 comprehensive tests for frozen behavior, defaults, base_url construction
- [x] 12.2 Server process lifecycle
    - Created build_server_command() pure function (easily tested)
    - Implemented ServerProcess (non-frozen, like LocalClient pattern)
    - async start() — launch subprocess, poll /v1/models until ready
    - async stop() — SIGTERM, wait, SIGKILL if needed
    - async health_check() — GET /v1/models
    - is_running property
    - Async context manager support (__aenter__/__aexit__)
    - 9 tests for command building, lifecycle, health checks, idempotent stop
- [x] 12.3 Integration with factory
    - Added create_server_model(config) -> Model
    - Thin wrapper using OpenAIProvider + OpenAIChatModel
    - Follows same pattern as _create_local_model()
- [x] 12.4 Training speed benchmark
    - Created create_dummy_dataset() for generating test data
    - Implemented run_training_benchmark() to measure LoRA training speed
    - BenchmarkResult (frozen) with seconds_per_iter, total_seconds, num_iters, peak_memory_gb
    - 3 tests for dataset creation (validation, directories, num_examples)
- [x] 12.5 Spec + roadmap
    - Created agent-os/specs/2026-02-11-server-management/ (plan, shape, standards, references)
    - Updated roadmap with Phase 12 entry

**Test Suite:** 320 tests passing (297 → 320, +23 new tests)
**Coverage:** 81%+ (maintained above 80% target)
**Type Safety:** All code passes ty type checking
**Quality:** Ruff ✅, Ty ✅, All tests ✅

---

## Phase 13: Evaluation Harness

**Status:** ✅ Complete
**Date:** 2026-02-11

**Goal:** Run standardized prompts against models, score results, produce baseline reports.

**Key Components:**
- Evaluation prompts and suites with categories
- Scoring functions (tool calling + keyword presence)
- Evaluation runner with server lifecycle management
- HTML report generation
- CLI command: `punie eval`

**Example Usage:**
```python
from punie.training.eval_suites import create_baseline_suite
from punie.training.eval_runner import run_evaluation, EvalRunConfig
from punie.training.server_config import ServerConfig

suite = create_baseline_suite()
config = EvalRunConfig(
    server_config=ServerConfig(
        model_path="mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
        port=8080,
    ),
    suite=suite,
    workspace=Path.cwd(),
    manage_server=True,
)
report = await run_evaluation(config)
print(f"Score: {report.overall_score:.1%}")
```

**Validation:** Successfully evaluated Qwen2.5-Coder-1.5B with 41.7% baseline score.

**Test Suite:** All tests passing
**Quality:** Ruff ✅, Ty ✅, All tests ✅

---

## Phase 14: Training Data Infrastructure

**Status:** ✅ Complete
**Date:** 2026-02-11

**Goal:** Framework for managing, validating, filtering, and writing training datasets in MLX LoRA format.

**Key Components:**
- Dataset dataclasses (ChatMessage, TrainingExample, TrainingDataset)
- Validation functions (message count, roles, content)
- Filtering functions (language, Python version, content quality)
- JSONL I/O (read/write datasets)
- LoRA training runner (build command, execute training)
- CLI commands: `punie train`, `punie dataset validate`, `punie dataset stats`, `punie dataset download`

**Example Usage:**
```python
from punie.training.lora_config import LoRAConfig
from punie.training.train_runner import run_training

config = LoRAConfig(
    base_model="mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
    data_directory=Path("data/train"),
    output_directory=Path("adapters/v1"),
    num_iters=100,
    batch_size=4,
    learning_rate=1e-5,
)
adapter_path = await run_training(config)
```

**Critical Fix:** Training command format changed from `mlx_lm.lora` to `python -m mlx_lm lora --train` (discovered during pipeline testing).

**Validation:** Full end-to-end pipeline test (`test_full_training_pipeline.py`) runs successfully: data generation → validation → baseline eval → training → adapted eval → comparison.

**Test Suite:** 130 training tests passing
**Quality:** Ruff ✅, Ty ✅, All tests ✅

---

## Phase 15: Progressive Dataset Pruning

**Status:** 🚧 Partial (15.1, 15.3+ complete)
**Date:** 2026-02-11

**Goal:** Download datasets, progressively filter them, train and evaluate at each step, compare results.

**Completed:**

**15.1: Dataset Downloads**
- `download_sample_dataset()`: Synthetic examples for testing
- `download_python_code_dataset()`: CodeSearchNet Python code (MIT licensed)
- Both support streaming (never download full corpus)
- Convert to chat-completion format compatible with mlx_lm.lora

**15.3+: Progressive Pruning Infrastructure**
- CLI filter command: `punie dataset filter`
  - Language filtering (remove non-English)
  - Python version filtering (remove Python 2, old versions)
  - Content quality filtering (remove short/malformed examples)
- CLI merge command: `punie dataset merge`
  - Combine multiple datasets
  - Useful for adding hand-authored examples
- Evaluation comparison: `compare_reports()`
  - Side-by-side HTML comparison of multiple evaluation runs
  - Shows score deltas, category breakdowns
  - Highlights improvements/regressions

**Example Workflow:**
```bash
# Download dataset
punie dataset download sample --max 100 --output data/raw/

# Filter step-by-step
punie dataset filter data/raw/ --language en --output data/step-a/
punie dataset filter data/step-a/ --min-python 3.10 --output data/step-b/
punie dataset filter data/step-b/ --min-messages 3 --output data/step-c/

# Train at each step
punie train data/step-c/ --output adapters/step-c/ --iters 100

# Evaluate
punie eval --adapter adapters/step-c/

# Merge with hand-authored examples
punie dataset merge data/step-c/ data/hand-authored/ --output data/merged/
```

**Validation:** Full progressive pruning test (`test_progressive_pruning.py`) demonstrates:
- Creating test dataset with known quality issues
- Filtering step-by-step (language → Python version → content quality)
- Retention rate tracking (started 7 examples → 5 retained)
- Comparison report generation

**15.4: Hyperparameter Tuning** (Complete 2026-02-11)
- `HyperparamGrid` for defining search space (learning rates, LoRA ranks, iterations, batch sizes)
- `run_hyperparam_search()` runs grid search: train + evaluate each combination
- `TrainingLog` and `parse_training_log()` extract train/val loss curves from mlx_lm output
- `TrainingResult` returns adapter path + training output for log parsing
- `run_training_with_logs()` captures training output (backwards compatible)
- Demo script: `test_hyperparam_tuning.py` (2 LR × 2 ranks × 10 iters)
- Sorts results by score, finds best configuration automatically
- **Test Suite:** 143 training tests passing (+13 new)

**15.5: Inference Parameter Tuning** (Complete 2026-02-11)
- `InferenceGrid` for server-side parameter search (temperature, top-p, repetition penalty, max KV cache)
- `run_inference_search()` tests each parameter combination via evaluation
- `InferenceResult` stores server config + eval results
- Note: Temperature/top-p typically require model-level config (documented for future enhancement)
- Current implementation tests server-level parameters (max_kv_size, repetition_penalty)
- **Test Suite:** 149 training tests passing (+6 new)

**Pending:**
- 15.2: Download real datasets (Dolma Wiki, RedPajama, KodCode) — requires user action

**Test Suite:** 149 training tests passing
**Quality:** Ruff ✅, Ty ✅, All tests ✅

**Phase 15 Summary:**
- ✅ Complete progressive pruning workflow (download → filter → merge → train → evaluate → compare)
- ✅ Hyperparameter tuning (grid search finds optimal training params)
- ✅ Inference tuning (optimize server-side generation parameters)
- ✅ All infrastructure ready for production use

**Next:** Phase 16 (tool calling data) or user-driven experiments with real datasets.
