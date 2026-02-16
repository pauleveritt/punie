# Phase 27 Punie Validation - References

## Core Implementation Files

### CLI Entry Point
**File:** `src/punie/cli.py`
**Lines:** 528-629
**Key functions:**
- `ask_command()` - CLI command entry point
- `_run_ask()` - Async execution wrapper

**Pattern:**
```python
@app.command()
def ask(
    prompt: str,
    model: str = "local",
    workspace: Path = Path.cwd(),
    debug: bool = False,
    perf: bool = False,
):
    """Ask Punie a question in local mode."""
    asyncio.run(_run_ask(prompt, model, workspace, debug, perf))

async def _run_ask(prompt: str, model: str, workspace: Path, debug: bool, perf: bool):
    agent, client = create_local_agent(model, workspace)
    deps = ACPDeps(client_conn=client, session_id="cli")
    result = await agent.run(prompt, deps=deps)
    # Display result
```

### Agent Factory
**File:** `src/punie/agent/factory.py`
**Lines:** 267-307
**Key functions:**
- `create_local_agent(model: str, workspace: Path)` → (Agent, LocalClient)

**Pattern:**
```python
def create_local_agent(model: str, workspace: Path) -> tuple[Agent, LocalClient]:
    """Create agent with local tools (5 tools)."""

    # Model selection
    if model == "test":
        agent_model = TestModel()
    elif model == "local":
        agent_model = MLXModel("fused_model_qwen3_phase27_5bit")

    # Tools: read_file, write_file, run_command, terminal, execute_code
    local_client = LocalClient(workspace)

    return (
        Agent(
            model=agent_model,
            system_prompt=PUNIE_LOCAL_INSTRUCTIONS,
        ),
        local_client,
    )
```

### Prompt Formatting (CRITICAL!)
**File:** `src/punie/agent/prompt_utils.py`
**Key function:** `format_prompt(query: str, model_path: str) -> str`

**Why critical:** Phase 26.1 showed 60-point accuracy drop when using manual string formatting instead of tokenizer's ChatML template.

**Pattern:**
```python
from punie.agent.prompt_utils import format_prompt

# ✅ CORRECT: Always use this
prompt = format_prompt("Find all classes", model_path)

# ❌ WRONG: Never do this!
# prompt = f"User: {query}\nAssistant:"
```

**Reference:** `docs/research/prompt-format-consistency.md`

## Validation Patterns

### Comprehensive Validation (40-query suite)
**File:** `scripts/validate_model.py`
**Lines:** 1773 total
**Key features:**
- 6-layer validation engine
- 8 categories (direct answers, LSP, git, cross-tool, etc.)
- Soft (structural) vs strict (compliance) validation
- Performance metrics tracking

**Pattern:**
```python
from punie.agent.prompt_utils import format_prompt

async def validate_category(category: dict, model_path: str):
    for query in category["queries"]:
        prompt = format_prompt(query["query"], model_path)
        # Run validation layers
        results = await run_validation_layers(prompt)
        # Score results
```

### Simple Validation (string matching)
**File:** `scripts/test_phase27_validation_fixed.py`
**Lines:** 403 total
**Key features:**
- String matching for tool detection
- Category-based scoring
- Fixed prompt formatting bug

**Pattern:**
```python
def detect_tool_calls(response: str) -> list[str]:
    """Detect which tools were called."""
    tools = []
    if "goto_definition(" in response:
        tools.append("goto_definition")
    if "find_references(" in response:
        tools.append("find_references")
    # ... more tools
    return tools

def validate_query(query: dict, response: str) -> bool:
    expected_tools = query["expected_tools"]
    detected_tools = detect_tool_calls(response)
    return all(tool in detected_tools for tool in expected_tools)
```

### Real Tool Integration Tests
**Files:**
- `scripts/test_real_lsp_tools.py` - LSP server integration
- `scripts/test_real_git_tools.py` - Git integration

**Pattern:**
```python
async def test_hover_tool():
    """Test hover tool with real LSP server."""
    async with LSPClient(workspace) as lsp:
        result = await lsp.hover("src/main.py", line=10, col=5)
        assert result.hover_text
        assert "def main" in result.hover_text
```

## Model Architecture

### Phase 27 Model
**Path:** `fused_model_qwen3_phase27_5bit/`
**Size:** 19.55 GB (5-bit quantized)
**Base:** Qwen3-30B-A3B-Instruct
**Training:** 1104 examples, 800 iterations
**Performance:**
- Load time: ~8s (cold start)
- Generation: 2.33s average (Phase 27 benchmark)
- Memory: 19.55 GB

### Tool Configuration

**Local mode (CLI):** 5 tools
1. `read_file(path)` - Read file contents
2. `write_file(path, content)` - Write file
3. `run_command(command)` - Execute shell command
4. `terminal(command)` - Create terminal session
5. `execute_code(code)` - Execute Python code

**ACP mode (PyCharm):** 14 tools (adds LSP + git + code quality)
- LSP: goto_definition, find_references, hover, document_symbols, workspace_symbols
- Git: git_status, git_diff, git_log
- Code quality: typecheck, ruff_check, pytest_run

## Testing Infrastructure

### Test Model
**File:** `src/punie/agent/models.py`
**Class:** `TestModel`
**Purpose:** Fast, predictable responses for testing without LLM

**Usage:**
```python
# For fast initialization tests
agent, client = create_local_agent("test", workspace)

# For real behavior tests
agent, client = create_local_agent("local", workspace)  # Uses Phase 27 model
```

### ACPDeps
**File:** `src/punie/agent/deps.py`
**Class:** `ACPDeps`
**Purpose:** Dependency injection for client connection and session

**Usage:**
```python
deps = ACPDeps(
    client_conn=local_client,
    session_id="test-session",
)
result = await agent.run("query", deps=deps)
```

## Related Documentation

### Phase 27 Documentation
- `docs/phase27-complete-implementation.md` - Full implementation guide
- `docs/phase27-deployment-summary.md` - Deployment reference
- `MEMORY.md` - Phase 27 section (lines 1-200)

### Research Notes
- `docs/research/prompt-format-consistency.md` - Critical: format_prompt() usage
- `docs/diary/2026-02-15-phase26-field-access-training.md` - Field access patterns
- `docs/diary/2026-02-15-phase27-complete-implementation.md` - Phase 27 details

### Training Data
- `data/phase27_merged/` - 1104 examples (993 train, 111 valid)
- `scripts/generate_phase27_*.py` - Data generation scripts
- `scripts/merge_phase27_data.py` - Data merger

## Performance Benchmarks

### Phase 27 Benchmark Results
**File:** `scripts/test_phase27_validation_fixed.py`
**Results:**
- Overall accuracy: 100% (40/40 queries)
- Average generation time: 2.33s
- Categories:
  - Direct answers: 5/5 (100%)
  - Existing LSP: 5/5 (100%)
  - New LSP: 5/5 (100%)
  - Git tools: 5/5 (100%)
  - Existing tools: 5/5 (100%)
  - Field access: 5/5 (100%)
  - Cross-tool workflows: 5/5 (100%)
  - Discrimination: 5/5 (100%)

### Expected Smoke Test Performance
- Load time: <10s (cold start)
- Response time: 2-5s (steady-state)
- Memory: <20 GB
- Pass rate: 10/10 (100%)

## Standards Applied

- `agent-os/standards/agent-verification.md` - Validation methodology
- `agent-os/standards/function-based-tests.md` - Test patterns
- `CLAUDE.md` - Prompt formatting rule (always use format_prompt!)
