"""Pre-defined evaluation suites."""

from punie.training.eval_prompts import EvalPrompt, EvalSuite


def create_baseline_suite() -> EvalSuite:
    """Create the baseline evaluation suite.

    This suite tests fundamental capabilities across tool calling,
    code generation, and reasoning. Used to establish baseline
    performance before training.

    Returns:
        EvalSuite with 5-10 prompts across categories
    """
    prompts = (
        # Tool calling prompts
        EvalPrompt(
            id="tool-01",
            category="tool_calling",
            prompt_text="Read the file at /etc/hosts and tell me what's in it.",
            expected_tool_calls=("read_file",),
            expected_keywords=("localhost", "127.0.0.1"),
        ),
        EvalPrompt(
            id="tool-02",
            category="tool_calling",
            prompt_text="Create a file called test.txt with the content 'Hello World'.",
            expected_tool_calls=("write_file",),
            expected_keywords=("test.txt", "Hello World"),
        ),
        EvalPrompt(
            id="tool-03",
            category="tool_calling",
            prompt_text="Run the command 'echo hello' and show me the output.",
            expected_tool_calls=("run_command",),
            expected_keywords=("hello", "echo"),
        ),
        # Code generation prompts
        EvalPrompt(
            id="code-01",
            category="code_generation",
            prompt_text="Write a Python function that checks if a number is prime.",
            expected_tool_calls=(),
            expected_keywords=("def", "prime", "return"),
        ),
        EvalPrompt(
            id="code-02",
            category="code_generation",
            prompt_text="Write a Python function to calculate factorial recursively.",
            expected_tool_calls=(),
            expected_keywords=("def", "factorial", "return", "recursive"),
        ),
        # Reasoning prompts
        EvalPrompt(
            id="reason-01",
            category="reasoning",
            prompt_text="Explain the difference between a list and a tuple in Python.",
            expected_tool_calls=(),
            expected_keywords=("list", "tuple", "mutable", "immutable"),
        ),
        EvalPrompt(
            id="reason-02",
            category="reasoning",
            prompt_text="What is the time complexity of binary search and why?",
            expected_tool_calls=(),
            expected_keywords=("O(log n)", "binary search", "complexity"),
        ),
    )

    return EvalSuite(name="baseline", prompts=prompts)


def create_phase33_suite() -> EvalSuite:
    """Create the Phase 33 evaluation suite covering all 26 tools.

    Tests all tool categories after full retrain:
    - Text tools (3): read_file, write_file, run_command
    - Validation tools (3): typecheck, ruff_check, pytest_run
    - LSP tools (5): goto_definition, find_references, hover, document_symbols, workspace_symbols
    - Git tools (3): git_status, git_diff, git_log
    - CST code tools (3): cst_find_pattern, cst_rename, cst_add_import
    - Domain validators (6): validate_component, validate_service_registration,
      validate_middleware_chain, check_dependency_graph, validate_escape_context,
      validate_route_pattern
    - Multi-tool workflow (1): LSP → read → domain validate → write → test

    Returns:
        EvalSuite with ~26 prompts across all tool categories
    """
    prompts = (
        # --- Text tools ---
        EvalPrompt(
            id="text-01",
            category="text_tools",
            prompt_text="Read the file src/punie/agent/config.py and summarize its contents.",
            expected_tool_calls=("read_file",),
            expected_keywords=("read_file", "config"),
        ),
        EvalPrompt(
            id="text-02",
            category="text_tools",
            prompt_text="Write a file called output/summary.txt with the text 'Phase 33 complete'.",
            expected_tool_calls=("write_file",),
            expected_keywords=("write_file", "output/summary.txt"),
        ),
        EvalPrompt(
            id="text-03",
            category="text_tools",
            prompt_text="Run 'ls src/' and show me what Python files are in the source directory.",
            expected_tool_calls=("run_command",),
            expected_keywords=("run_command", "ls"),
        ),
        # --- Validation tools ---
        EvalPrompt(
            id="valid-01",
            category="validation_tools",
            prompt_text="Run type checking on src/ and report any type errors.",
            expected_tool_calls=("typecheck",),
            expected_keywords=("typecheck", "error"),
        ),
        EvalPrompt(
            id="valid-02",
            category="validation_tools",
            prompt_text="Check src/ for linting violations with ruff and show the results.",
            expected_tool_calls=("ruff_check",),
            expected_keywords=("ruff_check", "violation"),
        ),
        EvalPrompt(
            id="valid-03",
            category="validation_tools",
            prompt_text="Run the test suite in tests/ and report how many tests passed and failed.",
            expected_tool_calls=("pytest_run",),
            expected_keywords=("pytest_run", "passed"),
        ),
        # --- LSP tools ---
        EvalPrompt(
            id="lsp-01",
            category="lsp_tools",
            prompt_text="Find the definition of AgentConfig in the codebase.",
            expected_tool_calls=("goto_definition",),
            expected_keywords=("goto_definition", "AgentConfig"),
        ),
        EvalPrompt(
            id="lsp-02",
            category="lsp_tools",
            prompt_text="Find all references to execute_code across the project.",
            expected_tool_calls=("find_references",),
            expected_keywords=("find_references", "execute_code"),
        ),
        EvalPrompt(
            id="lsp-03",
            category="lsp_tools",
            prompt_text="Show type information and docstring for LoRAConfig.",
            expected_tool_calls=("hover",),
            expected_keywords=("hover", "LoRAConfig"),
        ),
        EvalPrompt(
            id="lsp-04",
            category="lsp_tools",
            prompt_text="List all classes and functions defined in src/punie/training/lora_config.py.",
            expected_tool_calls=("document_symbols",),
            expected_keywords=("document_symbols", "lora_config"),
        ),
        EvalPrompt(
            id="lsp-05",
            category="lsp_tools",
            prompt_text="Search the workspace for any symbol named TrainingResult.",
            expected_tool_calls=("workspace_symbols",),
            expected_keywords=("workspace_symbols", "TrainingResult"),
        ),
        # --- Git tools ---
        EvalPrompt(
            id="git-01",
            category="git_tools",
            prompt_text="Check git status and tell me which files have been modified.",
            expected_tool_calls=("git_status",),
            expected_keywords=("git_status", "modified"),
        ),
        EvalPrompt(
            id="git-02",
            category="git_tools",
            prompt_text="Show the git diff for uncommitted changes in the project.",
            expected_tool_calls=("git_diff",),
            expected_keywords=("git_diff", "diff"),
        ),
        EvalPrompt(
            id="git-03",
            category="git_tools",
            prompt_text="List the 5 most recent git commits with their authors and messages.",
            expected_tool_calls=("git_log",),
            expected_keywords=("git_log", "commit"),
        ),
        # --- CST code tools ---
        EvalPrompt(
            id="cst-01",
            category="cst_tools",
            prompt_text="Find all function definitions in src/punie/training/train_runner.py.",
            expected_tool_calls=("cst_find_pattern",),
            expected_keywords=("cst_find_pattern", "FunctionDef"),
        ),
        EvalPrompt(
            id="cst-02",
            category="cst_tools",
            prompt_text="Rename the symbol 'old_name' to 'new_name' in src/punie/agent/stubs.py.",
            expected_tool_calls=("cst_rename",),
            expected_keywords=("cst_rename",),
        ),
        EvalPrompt(
            id="cst-03",
            category="cst_tools",
            prompt_text="Add 'from pathlib import Path' to src/punie/agent/config.py if not already imported.",
            expected_tool_calls=("cst_add_import",),
            expected_keywords=("cst_add_import", "pathlib"),
        ),
        # --- Domain validators ---
        EvalPrompt(
            id="domain-01",
            category="domain_validators",
            prompt_text="Validate the tdom component in src/views/home.py — check it follows @dataclass + __call__ -> Node + html() patterns.",
            expected_tool_calls=("validate_component",),
            expected_keywords=("validate_component",),
        ),
        EvalPrompt(
            id="domain-02",
            category="domain_validators",
            prompt_text="Check the service registration in src/services/user_service.py — verify it has @injectable, @dataclass, and Inject[] fields.",
            expected_tool_calls=("validate_service_registration",),
            expected_keywords=("validate_service_registration",),
        ),
        EvalPrompt(
            id="domain-03",
            category="domain_validators",
            prompt_text="Validate the middleware in src/middleware/auth.py — check @middleware decorator, categories, and __call__ signature.",
            expected_tool_calls=("validate_middleware_chain",),
            expected_keywords=("validate_middleware_chain",),
        ),
        EvalPrompt(
            id="domain-04",
            category="domain_validators",
            prompt_text="Check for dependency graph violations in src/services/report_service.py — look for illegal service→component imports.",
            expected_tool_calls=("check_dependency_graph",),
            expected_keywords=("check_dependency_graph",),
        ),
        EvalPrompt(
            id="domain-05",
            category="domain_validators",
            prompt_text="Check src/views/profile.py for XSS risks — verify no f-strings are used inside html() calls.",
            expected_tool_calls=("validate_escape_context",),
            expected_keywords=("validate_escape_context",),
        ),
        EvalPrompt(
            id="domain-06",
            category="domain_validators",
            prompt_text="Validate the route patterns in src/routes/api.py — check path syntax is correct.",
            expected_tool_calls=("validate_route_pattern",),
            expected_keywords=("validate_route_pattern",),
        ),
        # --- Multi-tool workflow ---
        EvalPrompt(
            id="workflow-01",
            category="multi_tool_workflow",
            prompt_text=(
                "I want to add a new view component to the project. "
                "First find the definition of the existing HomeView to understand the pattern, "
                "then read the file to see the full implementation, "
                "validate that the component follows tdom standards, "
                "and finally run the tests to make sure nothing is broken."
            ),
            expected_tool_calls=("goto_definition", "read_file", "validate_component", "pytest_run"),
            expected_keywords=("goto_definition", "read_file", "validate_component", "pytest_run"),
        ),
    )

    return EvalSuite(name="phase33", prompts=prompts)
