"""Generate Phase 28 targeted training examples to fix 4 failure patterns.

Creates ~90 examples across 4 categories:
- Category 1: Multi-Tool Chaining (40 examples) -- ROOT CAUSE #1
- Category 2: Document Symbols & Workspace Symbols Identity (20 examples) -- ROOT CAUSE #3
- Category 3: Multi-Turn Follow-Through (20 examples) -- ROOT CAUSE #4
- Category 4: Field Access with Boolean Filters (10 examples) -- ROOT CAUSE #6

All examples follow Phase 27 structural norms:
- 100% system messages
- Code Mode format (<tool_call><function=execute_code>)
- NO preambles before tool calls
- Tool responses as user messages with <tool_response> wrapping
"""

import json
import random
from pathlib import Path

# Set seed for reproducibility
random.seed(2028)

SYSTEM_MSG = (
    "You are Punie, an AI coding assistant for Python projects. "
    "You help developers write, test, and maintain Python code using available tools."
)


def make_tool_call(code: str) -> str:
    """Format a tool call in the standard XML format."""
    return f"<tool_call><function=execute_code>\n<parameter=code>\n{code}\n</parameter>\n</function></tool_call>"


def make_tool_response(response_text: str) -> str:
    """Format a tool response as it appears in user messages."""
    return f"<tool_response>\n{response_text}\n</tool_response>"


def msg_system() -> dict:
    return {"role": "system", "content": SYSTEM_MSG}


def msg_user(content: str) -> dict:
    return {"role": "user", "content": content}


def msg_assistant_tool(code: str) -> dict:
    return {"role": "assistant", "content": make_tool_call(code)}


def msg_assistant_text(content: str) -> dict:
    return {"role": "assistant", "content": content}


def msg_tool_response(response_text: str) -> dict:
    return {"role": "user", "content": make_tool_response(response_text)}


# ---------------------------------------------------------------------------
# Category 1: Multi-Tool Chaining (40 examples) -- ROOT CAUSE #1
# ---------------------------------------------------------------------------

def create_multi_tool_chaining_examples() -> list[dict]:
    """Create 40 examples where the assistant calls 2-3 tools in a SINGLE code block."""
    examples = []

    # --- Pattern 1: ruff_check + typecheck + pytest_run (quality pipeline) ---
    quality_queries = [
        ("Run full quality checks on src/", "src", "tests"),
        ("Check code quality: lint, types, and tests", "src", "tests"),
        ("Quality pipeline for src/punie/agent/", "src/punie/agent", "tests"),
        ("Run ruff, ty, and pytest together on src/", "src", "tests"),
        ("Complete code health check for the project", "src", "tests"),
    ]

    for query, src, test in quality_queries:
        code = "\n".join([
            "# Run full quality pipeline",
            f'ruff_result = ruff_check("{src}")',
            'print(f"Ruff: {ruff_result.violation_count} violations")',
            "",
            f'ty_result = typecheck("{src}")',
            'print(f"Types: {ty_result.error_count} errors")',
            "",
            f'test_result = pytest_run("{test}")',
            'print(f"Tests: {test_result.passed} passed, {test_result.failed} failed")',
            "",
            "all_ok = ruff_result.success and ty_result.success and test_result.success",
            'status = "PASS" if all_ok else "FAIL"',
            'print(f"\\nOverall: {status}")',
        ])
        examples.append({"messages": [
            msg_system(), msg_user(query), msg_assistant_tool(code),
        ]})

    # --- Pattern 2: goto_definition + hover (find and inspect) ---
    goto_hover_queries = [
        ("Find where UserService is defined and show its type info", "src/app.py", 15, 8, "UserService"),
        ("Go to definition of process_data and get hover info", "src/services/pipeline.py", 42, 12, "process_data"),
        ("Look up validate_input definition and show its signature", "src/utils/validation.py", 28, 4, "validate_input"),
        ("Find Config definition and show type details", "src/punie/agent/config.py", 10, 6, "Config"),
        ("Jump to create_app definition and hover for details", "src/main.py", 5, 10, "create_app"),
    ]

    for query, file, line, col, symbol in goto_hover_queries:
        code = "\n".join([
            "# Step 1: Find definition",
            f'def_result = goto_definition("{file}", {line}, {col}, "{symbol}")',
            "if def_result.success and def_result.locations:",
            "    loc = def_result.locations[0]",
            '    print(f"Definition at {loc.file}:{loc.line}")',
            "",
            "    # Step 2: Get hover info at that location",
            f'    hover_result = hover(loc.file, loc.line, loc.column, "{symbol}")',
            "    if hover_result.success:",
            '        print(f"Type: {hover_result.type_info}")',
            "        if hover_result.documentation:",
            '            print(f"Docs: {hover_result.documentation}")',
            "    else:",
            '        print("No hover info available")',
            "else:",
            '    print("Definition not found")',
        ])
        examples.append({"messages": [
            msg_system(), msg_user(query), msg_assistant_tool(code),
        ]})

    # --- Pattern 3: git_status + git_diff (status and diff together) ---
    git_queries = [
        ("Show me what changed and the diff details", "."),
        ("Check git status and show the actual changes", "."),
        ("List modified files and show their diffs", "."),
        ("What files changed and what are the changes?", "."),
        ("Show working tree status with diff summary", "."),
    ]

    for query, path in git_queries:
        code = "\n".join([
            "# Step 1: Check status",
            f'status = git_status("{path}")',
            'print(f"Files changed: {status.file_count}")',
            "for f in status.files:",
            '    tag = "staged" if f.staged else "unstaged"',
            '    print(f"  {f.file} ({f.status}, {tag})")',
            "",
            "# Step 2: Get diff details",
            f'diff = git_diff("{path}", staged=False)',
            "if diff.file_count > 0:",
            '    print(f"\\nDiff: +{diff.additions} -{diff.deletions}")',
            "    for f in diff.files:",
            '        print(f"  {f.file}: +{f.additions} -{f.deletions}")',
        ])
        examples.append({"messages": [
            msg_system(), msg_user(query), msg_assistant_tool(code),
        ]})

    # --- Pattern 4: pytest_run + ruff_check (test then lint) ---
    test_lint_queries = [
        ("Run tests then check linting", "tests", "src"),
        ("Test and lint the project", "tests", "src"),
        ("Make sure tests pass and code is clean", "tests", "src"),
        ("Verify tests and lint violations", "tests", "src"),
        ("Check tests and code style together", "tests/unit", "src"),
    ]

    for query, test_path, src_path in test_lint_queries:
        code = "\n".join([
            "# Step 1: Run tests",
            f'test_result = pytest_run("{test_path}")',
            'print(f"Tests: {test_result.passed} passed, {test_result.failed} failed")',
            "if test_result.failed > 0:",
            "    for t in test_result.tests:",
            '        if t.outcome == "failed":',
            '            print(f"  FAIL: {t.name}")',
            "",
            "# Step 2: Run linting",
            f'ruff_result = ruff_check("{src_path}")',
            'print(f"\\nLint: {ruff_result.violation_count} violations")',
            "if ruff_result.violation_count > 0:",
            "    for v in ruff_result.violations[:5]:",
            '        print(f"  {v.file}:{v.line} {v.code} {v.message}")',
        ])
        examples.append({"messages": [
            msg_system(), msg_user(query), msg_assistant_tool(code),
        ]})

    # --- Pattern 5: workspace_symbols + document_symbols (search then list) ---
    ws_doc_queries = [
        ("Search for classes named Handler and list symbols in the file", "Handler"),
        ("Find UserModel in the workspace then show all symbols in that file", "UserModel"),
        ("Search project for Router and list the file contents", "Router"),
        ("Locate BaseService in workspace and show file structure", "BaseService"),
        ("Find TestHelper across the project and list its file symbols", "TestHelper"),
    ]

    for query, symbol in ws_doc_queries:
        code = "\n".join([
            "# Step 1: Search workspace for the symbol",
            f'ws_result = workspace_symbols("{symbol}")',
            "if ws_result.success and ws_result.symbols:",
            "    first = ws_result.symbols[0]",
            '    print(f"Found {first.name} in {first.file}:{first.line}")',
            "",
            "    # Step 2: List all symbols in that file",
            "    doc_result = document_symbols(first.file)",
            "    if doc_result.success:",
            '        print(f"\\nSymbols in {first.file} ({doc_result.symbol_count} total):")',
            "        for sym in doc_result.symbols:",
            '            print(f"  {sym.kind} {sym.name} line {sym.line}")',
            "    else:",
            '        print("Could not list symbols")',
            "else:",
            '    print("Symbol not found in workspace")',
        ])
        examples.append({"messages": [
            msg_system(), msg_user(query), msg_assistant_tool(code),
        ]})

    # --- Pattern 6: document_symbols + hover (list then inspect) ---
    doc_hover_queries = [
        ("List symbols in src/models/user.py and show type info for the main class", "src/models/user.py"),
        ("Show structure of src/services/auth.py and hover on the first function", "src/services/auth.py"),
        ("Outline src/utils/helpers.py and inspect the top-level functions", "src/utils/helpers.py"),
        ("List all definitions in src/api/routes.py and get details on the first", "src/api/routes.py"),
        ("Show file structure of src/punie/agent/toolset.py and hover on a class", "src/punie/agent/toolset.py"),
    ]

    for query, file in doc_hover_queries:
        code = "\n".join([
            "# Step 1: List all symbols in the file",
            f'doc_result = document_symbols("{file}")',
            "if doc_result.success and doc_result.symbols:",
            f'    print(f"{{doc_result.symbol_count}} symbols in {file}:")',
            "    for sym in doc_result.symbols:",
            '        print(f"  {sym.kind} {sym.name} (line {sym.line})")',
            "",
            "    # Step 2: Hover on the first class or function",
            "    first_sym = doc_result.symbols[0]",
            f'    hover_result = hover("{file}", first_sym.line, 0, first_sym.name)',
            "    if hover_result.success:",
            '        print(f"\\nHover on {first_sym.name}:")',
            '        print(f"  Type: {hover_result.type_info}")',
            "    else:",
            '        print(f"No hover info for {first_sym.name}")',
            "else:",
            '    print("No symbols found")',
        ])
        examples.append({"messages": [
            msg_system(), msg_user(query), msg_assistant_tool(code),
        ]})

    # --- Pattern 7: git_status + read_file (status then read modified) ---
    git_read_queries = [
        ("Check what files changed and read the modified ones", "."),
        ("Show git status then read the first modified file", "."),
        ("List changed files and show their contents", "."),
        ("Find modified files and read the most recently changed", "."),
        ("Check for changes and display modified file contents", "."),
    ]

    for query, path in git_read_queries:
        code = "\n".join([
            "# Step 1: Check git status",
            f'status = git_status("{path}")',
            "if not status.clean:",
            '    print(f"{status.file_count} files changed:")',
            "    for f in status.files:",
            '        print(f"  {f.file} ({f.status})")',
            "",
            "    # Step 2: Read the first modified file",
            "    first_file = status.files[0].file",
            "    content = read_file(first_file)",
            '    lines = content.split("\\n")',
            '    print(f"\\n--- {first_file} ({len(lines)} lines) ---")',
            "    for line in lines[:20]:",
            "        print(line)",
            "else:",
            '    print("Working tree clean, no files to read")',
        ])
        examples.append({"messages": [
            msg_system(), msg_user(query), msg_assistant_tool(code),
        ]})

    # --- Pattern 8: find_references + goto_definition (refs then def) ---
    refs_def_queries = [
        ("Find all references to parse_config and go to its definition", "src/config.py", 30, 4, "parse_config"),
        ("Show usages of render_template then jump to definition", "src/views/base.py", 18, 8, "render_template"),
        ("Where is validate_token used and where is it defined?", "src/auth/jwt.py", 55, 12, "validate_token"),
        ("Find references to DatabasePool and its definition", "src/db/pool.py", 8, 6, "DatabasePool"),
        ("List all callers of send_notification and its source", "src/services/notify.py", 22, 4, "send_notification"),
    ]

    for query, file, line, col, symbol in refs_def_queries:
        code = "\n".join([
            "# Step 1: Find all references",
            f'refs = find_references("{file}", {line}, {col}, "{symbol}")',
            "if refs.success:",
            f'    print(f"{{refs.reference_count}} references to {symbol}:")',
            "    for ref in refs.references:",
            '        print(f"  {ref.file}:{ref.line}")',
            "",
            "# Step 2: Go to definition",
            f'defn = goto_definition("{file}", {line}, {col}, "{symbol}")',
            "if defn.success and defn.locations:",
            "    loc = defn.locations[0]",
            '    print(f"\\nDefined at {loc.file}:{loc.line}")',
            "else:",
            '    print("Definition not found")',
        ])
        examples.append({"messages": [
            msg_system(), msg_user(query), msg_assistant_tool(code),
        ]})

    return examples[:40]


# ---------------------------------------------------------------------------
# Category 2: Document Symbols & Workspace Symbols Identity (20 examples)
# -- ROOT CAUSE #3
# ---------------------------------------------------------------------------

def create_symbol_identity_examples() -> list[dict]:
    """Create 20 examples with diverse natural language triggers for document_symbols
    and workspace_symbols."""
    examples = []

    # --- document_symbols triggers (10 examples) ---
    doc_sym_queries = [
        ("List all symbols in src/punie/agent/toolset.py", "src/punie/agent/toolset.py"),
        ("Show the structure of src/models/user.py", "src/models/user.py"),
        ("What's in src/services/auth.py?", "src/services/auth.py"),
        ("Give me an outline of tests/test_agent.py", "tests/test_agent.py"),
        ("Show classes and functions in src/api/routes.py", "src/api/routes.py"),
        ("List definitions in src/utils/helpers.py", "src/utils/helpers.py"),
        ("What symbols are defined in src/config.py?", "src/config.py"),
        ("Show the file structure of src/db/models.py", "src/db/models.py"),
        ("Enumerate classes in src/punie/agent/stubs.py", "src/punie/agent/stubs.py"),
        ("What classes and functions does src/main.py contain?", "src/main.py"),
    ]

    for query, file in doc_sym_queries:
        code = "\n".join([
            f'result = document_symbols("{file}")',
            "if result.success:",
            f'    print(f"{{result.symbol_count}} symbols in {file}:")',
            "    for sym in result.symbols:",
            '        print(f"  {sym.kind} {sym.name} (line {sym.line})")',
            "else:",
            '    print("Could not list symbols")',
        ])
        examples.append({"messages": [
            msg_system(), msg_user(query), msg_assistant_tool(code),
        ]})

    # --- workspace_symbols triggers (10 examples) ---
    ws_sym_queries = [
        ("Search the workspace for classes named Handler", "Handler"),
        ("Find all classes named Service in the project", "Service"),
        ("Search project for symbols matching Config", "Config"),
        ("Locate all definitions of Manager across the workspace", "Manager"),
        ("Find symbols matching BaseModel in the codebase", "BaseModel"),
        ("Search the project for functions named validate", "validate"),
        ("Where are classes named Repository defined?", "Repository"),
        ("Find all symbols called Factory in the workspace", "Factory"),
        ("Search across files for anything named Parser", "Parser"),
        ("Locate TestCase classes in the project", "TestCase"),
    ]

    for query, symbol in ws_sym_queries:
        code = "\n".join([
            f'result = workspace_symbols("{symbol}")',
            "if result.success:",
            f'    print(f"Found {{result.symbol_count}} symbols matching \\"{symbol}\\\":")',
            "    for sym in result.symbols:",
            '        print(f"  {sym.kind} {sym.name} in {sym.file}:{sym.line}")',
            "else:",
            '    print("No symbols found")',
        ])
        examples.append({"messages": [
            msg_system(), msg_user(query), msg_assistant_tool(code),
        ]})

    return examples[:20]


# ---------------------------------------------------------------------------
# Category 3: Multi-Turn Follow-Through (20 examples) -- ROOT CAUSE #4
# ---------------------------------------------------------------------------

def create_multi_turn_follow_through_examples() -> list[dict]:
    """Create 20 multi-turn examples where turn 2 MUST call a tool (not narrate)."""
    examples = []

    # --- 1: ruff_check -> user asks to also typecheck ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Check src/ for lint violations"),
        msg_assistant_tool("\n".join([
            'result = ruff_check("src")',
            'print(f"Violations: {result.violation_count}")',
            "for v in result.violations[:5]:",
            '    print(f"  {v.file}:{v.line} {v.code} {v.message}")',
        ])),
        msg_tool_response(
            'RuffResult(success=False, violation_count=3, fixable_count=2, violations=['
            'RuffViolation(file="src/utils.py", line=12, column=1, code="F401", message="unused import os", fixable=True), '
            'RuffViolation(file="src/utils.py", line=25, column=5, code="E711", message="comparison to None", fixable=True), '
            'RuffViolation(file="src/models.py", line=8, column=1, code="F841", message="local variable x unused", fixable=False)'
            '], parse_error=None)'
        ),
        msg_assistant_text(
            "Found 3 violations (2 fixable):\n"
            "  src/utils.py:12 F401 unused import os\n"
            "  src/utils.py:25 E711 comparison to None\n"
            "  src/models.py:8 F841 local variable x unused"
        ),
        msg_user("Now run type checking on src/ too"),
        msg_assistant_tool("\n".join([
            'result = typecheck("src")',
            "if result.success:",
            '    print("No type errors found")',
            "else:",
            '    print(f"Found {result.error_count} type errors")',
            "    for error in result.errors:",
            '        print(f"  {error.file}:{error.line} {error.message}")',
        ])),
    ]})

    # --- 2: pytest fails -> user asks goto_definition ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Run tests in tests/"),
        msg_assistant_tool("\n".join([
            'result = pytest_run("tests")',
            'print(f"Passed: {result.passed}, Failed: {result.failed}")',
            "if result.failed > 0:",
            "    for t in result.tests:",
            '        if t.outcome == "failed":',
            '            print(f"  FAIL: {t.name}")',
            "            if t.message:",
            '                print(f"    {t.message[:80]}")',
        ])),
        msg_tool_response(
            'TestResult(success=False, passed=12, failed=1, skipped=0, '
            'duration=3.45, tests=[TestCase(name="test_validate_input", '
            'outcome="failed", duration=0.12, message="AssertionError: expected True got False")],'
            ' parse_error=None)'
        ),
        msg_assistant_text(
            "12 passed, 1 failed.\n"
            "  FAIL: test_validate_input\n"
            "    AssertionError: expected True got False"
        ),
        msg_user("Go to the definition of validate_input so I can see what's wrong"),
        msg_assistant_tool("\n".join([
            'result = goto_definition("src/utils/validation.py", 15, 4, "validate_input")',
            "if result.success and result.locations:",
            "    loc = result.locations[0]",
            '    print(f"validate_input defined at {loc.file}:{loc.line}")',
            "else:",
            '    print("Definition not found")',
        ])),
    ]})

    # --- 3: git_status -> user asks for diff ---
    examples.append({"messages": [
        msg_system(),
        msg_user("What files have changed?"),
        msg_assistant_tool("\n".join([
            'result = git_status(".")',
            "if not result.clean:",
            '    print(f"{result.file_count} files changed:")',
            "    for f in result.files:",
            '        print(f"  {f.file} ({f.status})")',
            "else:",
            '    print("Working tree clean")',
        ])),
        msg_tool_response(
            'GitStatusResult(success=True, clean=False, file_count=2, '
            'files=[GitFile(file="src/models.py", status="modified", staged=False), '
            'GitFile(file="tests/test_models.py", status="modified", staged=True)], parse_error=None)'
        ),
        msg_assistant_text("2 files changed:\n  src/models.py (modified)\n  tests/test_models.py (modified)"),
        msg_user("Show me the diff for those changes"),
        msg_assistant_tool("\n".join([
            'diff = git_diff(".", staged=False)',
            "if diff.file_count > 0:",
            '    print(f"Unstaged: +{diff.additions} -{diff.deletions}")',
            "    for f in diff.files:",
            '        print(f"  {f.file}: +{f.additions} -{f.deletions}")',
            "",
            'staged_diff = git_diff(".", staged=True)',
            "if staged_diff.file_count > 0:",
            '    print(f"\\nStaged: +{staged_diff.additions} -{staged_diff.deletions}")',
            "    for f in staged_diff.files:",
            '        print(f"  {f.file}: +{f.additions} -{f.deletions}")',
        ])),
    ]})

    # --- 4: document_symbols -> user asks hover ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Show the structure of src/services/auth.py"),
        msg_assistant_tool("\n".join([
            'result = document_symbols("src/services/auth.py")',
            "if result.success:",
            '    print(f"{result.symbol_count} symbols:")',
            "    for sym in result.symbols:",
            '        print(f"  {sym.kind} {sym.name} (line {sym.line})")',
            "else:",
            '    print("No symbols found")',
        ])),
        msg_tool_response(
            'DocumentSymbolsResult(success=True, symbol_count=4, symbols=['
            'DocumentSymbol(name="AuthService", kind="class", line=8, end_line=45, children=[]), '
            'DocumentSymbol(name="authenticate", kind="function", line=12, end_line=25, children=[]), '
            'DocumentSymbol(name="refresh_token", kind="function", line=27, end_line=38, children=[]), '
            'DocumentSymbol(name="TOKEN_EXPIRY", kind="variable", line=5, end_line=5, children=[])'
            '], parse_error=None)'
        ),
        msg_assistant_text(
            "4 symbols in src/services/auth.py:\n"
            "  class AuthService (line 8)\n"
            "  function authenticate (line 12)\n"
            "  function refresh_token (line 27)\n"
            "  variable TOKEN_EXPIRY (line 5)"
        ),
        msg_user("Show me hover details for AuthService"),
        msg_assistant_tool("\n".join([
            'result = hover("src/services/auth.py", 8, 6, "AuthService")',
            "if result.success:",
            '    print(f"Symbol: {result.symbol}")',
            '    print(f"Type: {result.type_info}")',
            "    if result.documentation:",
            '        print(f"Docs: {result.documentation}")',
            "else:",
            '    print("No hover info available")',
        ])),
    ]})

    # --- 5: workspace_symbols -> user asks goto_definition ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Search the workspace for EventHandler"),
        msg_assistant_tool("\n".join([
            'result = workspace_symbols("EventHandler")',
            "if result.success:",
            '    print(f"Found {result.symbol_count} matches:")',
            "    for sym in result.symbols:",
            '        print(f"  {sym.kind} {sym.name} in {sym.file}:{sym.line}")',
            "else:",
            '    print("No symbols found")',
        ])),
        msg_tool_response(
            'WorkspaceSymbolsResult(success=True, symbol_count=2, symbols=['
            'WorkspaceSymbol(name="EventHandler", kind="class", file="src/events/handler.py", line=15), '
            'WorkspaceSymbol(name="EventHandlerBase", kind="class", file="src/events/base.py", line=8)'
            '], parse_error=None)'
        ),
        msg_assistant_text(
            "Found 2 matches:\n"
            "  class EventHandler in src/events/handler.py:15\n"
            "  class EventHandlerBase in src/events/base.py:8"
        ),
        msg_user("Go to the definition of EventHandler"),
        msg_assistant_tool("\n".join([
            'result = goto_definition("src/events/handler.py", 15, 6, "EventHandler")',
            "if result.success and result.locations:",
            "    loc = result.locations[0]",
            '    print(f"EventHandler defined at {loc.file}:{loc.line}")',
            "else:",
            '    print("Definition not found")',
        ])),
    ]})

    # --- 6: typecheck with errors -> user asks for references ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Type check src/services/"),
        msg_assistant_tool("\n".join([
            'result = typecheck("src/services")',
            "if result.success:",
            '    print("No type errors")',
            "else:",
            '    print(f"Found {result.error_count} errors")',
            "    for err in result.errors:",
            '        print(f"  {err.file}:{err.line} {err.message}")',
        ])),
        msg_tool_response(
            'TypeCheckResult(success=False, error_count=2, warning_count=1, errors=['
            'TypeCheckError(file="src/services/user.py", line=34, column=12, code="E0001", '
            'severity="error", message="Argument of type str is not assignable to parameter of type int"), '
            'TypeCheckError(file="src/services/user.py", line=52, column=8, code="E0002", '
            'severity="error", message="Cannot access member process on type None")'
            '], parse_error=None)'
        ),
        msg_assistant_text(
            "Found 2 type errors:\n"
            "  src/services/user.py:34 Argument of type str is not assignable to parameter of type int\n"
            "  src/services/user.py:52 Cannot access member process on type None"
        ),
        msg_user("Find all references to the function at line 34 to see who calls it"),
        msg_assistant_tool("\n".join([
            'result = find_references("src/services/user.py", 34, 12, "process")',
            "if result.success:",
            '    print(f"{result.reference_count} references:")',
            "    for ref in result.references:",
            '        print(f"  {ref.file}:{ref.line}")',
            "else:",
            '    print("No references found")',
        ])),
    ]})

    # --- 7: find_references -> user asks to run relevant tests ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Find all references to create_order"),
        msg_assistant_tool("\n".join([
            'result = find_references("src/services/order.py", 20, 4, "create_order")',
            "if result.success:",
            '    print(f"{result.reference_count} references:")',
            "    for ref in result.references:",
            '        print(f"  {ref.file}:{ref.line}")',
            "else:",
            '    print("No references found")',
        ])),
        msg_tool_response(
            'FindReferencesResult(success=True, symbol="create_order", reference_count=4, '
            'references=[ReferenceLocation(file="src/services/order.py", line=20, column=4, preview=None), '
            'ReferenceLocation(file="src/api/routes.py", line=45, column=12, preview=None), '
            'ReferenceLocation(file="tests/test_order.py", line=10, column=8, preview=None), '
            'ReferenceLocation(file="tests/test_api.py", line=33, column=16, preview=None)'
            '], parse_error=None)'
        ),
        msg_assistant_text(
            "4 references to create_order:\n"
            "  src/services/order.py:20\n"
            "  src/api/routes.py:45\n"
            "  tests/test_order.py:10\n"
            "  tests/test_api.py:33"
        ),
        msg_user("Run the tests that reference create_order"),
        msg_assistant_tool("\n".join([
            'result = pytest_run("tests/test_order.py")',
            'print(f"test_order.py: {result.passed} passed, {result.failed} failed")',
            "",
            'result2 = pytest_run("tests/test_api.py")',
            'print(f"test_api.py: {result2.passed} passed, {result2.failed} failed")',
        ])),
    ]})

    # --- 8: git_log -> user asks for diff ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Show recent commits"),
        msg_assistant_tool("\n".join([
            'result = git_log(".", count=5)',
            "if result.commit_count > 0:",
            "    for commit in result.commits:",
            '        print(f"{commit.hash[:7]} {commit.message}")',
            "else:",
            '    print("No commits found")',
        ])),
        msg_tool_response(
            'GitLogResult(success=True, commit_count=5, commits=['
            'GitCommit(hash="abc1234", message="fix: validate input types", author="alice", date="2026-02-15"), '
            'GitCommit(hash="def5678", message="feat: add user service", author="bob", date="2026-02-14"), '
            'GitCommit(hash="ghi9012", message="refactor: simplify auth", author="alice", date="2026-02-13"), '
            'GitCommit(hash="jkl3456", message="test: add order tests", author="carol", date="2026-02-12"), '
            'GitCommit(hash="mno7890", message="docs: update readme", author="bob", date="2026-02-11")'
            '], parse_error=None)'
        ),
        msg_assistant_text(
            "Recent commits:\n"
            "  abc1234 fix: validate input types\n"
            "  def5678 feat: add user service\n"
            "  ghi9012 refactor: simplify auth\n"
            "  jkl3456 test: add order tests\n"
            "  mno7890 docs: update readme"
        ),
        msg_user("Check what changed in the latest commit by showing the diff"),
        msg_assistant_tool("\n".join([
            'diff = git_diff(".", staged=False)',
            "if diff.file_count > 0:",
            '    print(f"Changes: {diff.file_count} files, +{diff.additions} -{diff.deletions}")',
            "    for f in diff.files:",
            '        print(f"  {f.file}: +{f.additions} -{f.deletions}")',
            "else:",
            '    print("No uncommitted changes")',
        ])),
    ]})

    # --- 9: ruff_check clean -> user asks to run tests ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Lint src/services/"),
        msg_assistant_tool("\n".join([
            'result = ruff_check("src/services")',
            "if result.success:",
            '    print("No violations")',
            "else:",
            '    print(f"{result.violation_count} violations:")',
            "    for v in result.violations:",
            '        print(f"  {v.file}:{v.line} {v.code} {v.message}")',
        ])),
        msg_tool_response(
            'RuffResult(success=True, violation_count=0, fixable_count=0, violations=[], parse_error=None)'
        ),
        msg_assistant_text("No lint violations found in src/services/."),
        msg_user("Great, now run the tests for services"),
        msg_assistant_tool("\n".join([
            'result = pytest_run("tests/test_services")',
            'print(f"Passed: {result.passed}, Failed: {result.failed}")',
            'print(f"Duration: {result.duration:.2f}s")',
            "if result.failed > 0:",
            "    for t in result.tests:",
            '        if t.outcome == "failed":',
            '            print(f"  FAIL: {t.name}")',
        ])),
    ]})

    # --- 10: hover -> user asks for references ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Show me hover info for DatabasePool in src/db/pool.py"),
        msg_assistant_tool("\n".join([
            'result = hover("src/db/pool.py", 10, 6, "DatabasePool")',
            "if result.success:",
            '    print(f"Symbol: {result.symbol}")',
            '    print(f"Type: {result.type_info}")',
            "    if result.documentation:",
            '        print(f"Docs: {result.documentation}")',
            "else:",
            '    print("No hover info")',
        ])),
        msg_tool_response(
            'HoverResult(success=True, symbol="DatabasePool", type_info="class DatabasePool(builtins.object)", '
            'documentation="Connection pool for database access.", parse_error=None)'
        ),
        msg_assistant_text(
            "DatabasePool:\n"
            "  Type: class DatabasePool(builtins.object)\n"
            "  Docs: Connection pool for database access."
        ),
        msg_user("Find all references to DatabasePool"),
        msg_assistant_tool("\n".join([
            'result = find_references("src/db/pool.py", 10, 6, "DatabasePool")',
            "if result.success:",
            '    print(f"{result.reference_count} references:")',
            "    for ref in result.references:",
            '        print(f"  {ref.file}:{ref.line}")',
            "else:",
            '    print("No references found")',
        ])),
    ]})

    # --- 11: goto_definition -> user asks to check types ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Go to the definition of transform_data"),
        msg_assistant_tool("\n".join([
            'result = goto_definition("src/pipeline.py", 30, 8, "transform_data")',
            "if result.success and result.locations:",
            "    loc = result.locations[0]",
            '    print(f"Defined at {loc.file}:{loc.line}")',
            "else:",
            '    print("Not found")',
        ])),
        msg_tool_response(
            'GotoDefinitionResult(success=True, symbol="transform_data", locations=['
            'DefinitionLocation(file="src/pipeline.py", line=30, column=4, end_line=30, end_column=18, preview=None)'
            '], parse_error=None)'
        ),
        msg_assistant_text("transform_data is defined at src/pipeline.py:30"),
        msg_user("Run type checking on that file"),
        msg_assistant_tool("\n".join([
            'result = typecheck("src/pipeline.py")',
            "if result.success:",
            '    print("No type errors in src/pipeline.py")',
            "else:",
            '    print(f"{result.error_count} type errors:")',
            "    for err in result.errors:",
            '        print(f"  line {err.line}: {err.message}")',
        ])),
    ]})

    # --- 12: git_diff -> user asks for git log ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Show me the current diff"),
        msg_assistant_tool("\n".join([
            'result = git_diff(".", staged=False)',
            "if result.file_count > 0:",
            '    print(f"{result.file_count} files changed")',
            '    print(f"+{result.additions} -{result.deletions}")',
            "    for f in result.files:",
            '        print(f"  {f.file}: +{f.additions} -{f.deletions}")',
            "else:",
            '    print("No changes")',
        ])),
        msg_tool_response(
            'GitDiffResult(success=True, file_count=1, additions=15, deletions=3, '
            'files=[DiffFile(file="src/utils.py", additions=15, deletions=3, hunks=[])], parse_error=None)'
        ),
        msg_assistant_text("1 file changed (+15 -3):\n  src/utils.py: +15 -3"),
        msg_user("Show me the recent commit history for context"),
        msg_assistant_tool("\n".join([
            'result = git_log(".", count=5)',
            "if result.commit_count > 0:",
            "    for commit in result.commits:",
            '        print(f"{commit.hash[:7]} {commit.message}")',
            "else:",
            '    print("No commits")',
        ])),
    ]})

    # --- 13: pytest with failure -> user asks to lint the failing file ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Run tests in tests/unit/"),
        msg_assistant_tool("\n".join([
            'result = pytest_run("tests/unit")',
            'print(f"Passed: {result.passed}, Failed: {result.failed}")',
            "if result.failed > 0:",
            "    for t in result.tests:",
            '        if t.outcome == "failed":',
            '            print(f"  FAIL: {t.name} - {t.message}")',
        ])),
        msg_tool_response(
            'TestResult(success=False, passed=8, failed=2, skipped=1, duration=2.1, tests=['
            'TestCase(name="test_parse_config", outcome="failed", duration=0.05, message="KeyError: missing_key"), '
            'TestCase(name="test_save_data", outcome="failed", duration=0.03, message="TypeError: expected str")'
            '], parse_error=None)'
        ),
        msg_assistant_text(
            "8 passed, 2 failed, 1 skipped:\n"
            "  FAIL: test_parse_config - KeyError: missing_key\n"
            "  FAIL: test_save_data - TypeError: expected str"
        ),
        msg_user("Check src/config.py for lint issues since parse_config is failing"),
        msg_assistant_tool("\n".join([
            'result = ruff_check("src/config.py")',
            "if result.success:",
            '    print("No lint violations in src/config.py")',
            "else:",
            '    print(f"{result.violation_count} violations:")',
            "    for v in result.violations:",
            '        print(f"  line {v.line}: {v.code} {v.message}")',
        ])),
    ]})

    # --- 14: workspace_symbols -> user asks document_symbols ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Find all Validator classes in the project"),
        msg_assistant_tool("\n".join([
            'result = workspace_symbols("Validator")',
            "if result.success:",
            '    print(f"Found {result.symbol_count} matches:")',
            "    for sym in result.symbols:",
            '        print(f"  {sym.kind} {sym.name} in {sym.file}:{sym.line}")',
            "else:",
            '    print("No matches")',
        ])),
        msg_tool_response(
            'WorkspaceSymbolsResult(success=True, symbol_count=3, symbols=['
            'WorkspaceSymbol(name="InputValidator", kind="class", file="src/validators/input.py", line=10), '
            'WorkspaceSymbol(name="SchemaValidator", kind="class", file="src/validators/schema.py", line=8), '
            'WorkspaceSymbol(name="Validator", kind="class", file="src/validators/base.py", line=5)'
            '], parse_error=None)'
        ),
        msg_assistant_text(
            "Found 3 Validator classes:\n"
            "  class InputValidator in src/validators/input.py:10\n"
            "  class SchemaValidator in src/validators/schema.py:8\n"
            "  class Validator in src/validators/base.py:5"
        ),
        msg_user("List all symbols in src/validators/input.py"),
        msg_assistant_tool("\n".join([
            'result = document_symbols("src/validators/input.py")',
            "if result.success:",
            '    print(f"{result.symbol_count} symbols:")',
            "    for sym in result.symbols:",
            '        print(f"  {sym.kind} {sym.name} (line {sym.line})")',
            "else:",
            '    print("No symbols found")',
        ])),
    ]})

    # --- 15: quality check -> user asks for git_status ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Check quality of src/api/"),
        msg_assistant_tool("\n".join([
            'ruff_result = ruff_check("src/api")',
            'ty_result = typecheck("src/api")',
            'print(f"Lint: {ruff_result.violation_count} violations")',
            'print(f"Types: {ty_result.error_count} errors")',
        ])),
        msg_tool_response(
            'RuffResult(success=True, violation_count=0, fixable_count=0, violations=[], parse_error=None)\n'
            'TypeCheckResult(success=True, error_count=0, warning_count=0, errors=[], parse_error=None)'
        ),
        msg_assistant_text("All clear:\n  Lint: 0 violations\n  Types: 0 errors"),
        msg_user("Good. Check git status to see if there are changes to commit"),
        msg_assistant_tool("\n".join([
            'result = git_status(".")',
            "if result.clean:",
            '    print("Working tree clean, nothing to commit")',
            "else:",
            '    print(f"{result.file_count} files with changes:")',
            "    for f in result.files:",
            '        tag = "staged" if f.staged else "unstaged"',
            '        print(f"  {f.file} ({f.status}, {tag})")',
        ])),
    ]})

    # --- 16: document_symbols -> user asks to run tests ---
    examples.append({"messages": [
        msg_system(),
        msg_user("What functions are in src/services/order.py?"),
        msg_assistant_tool("\n".join([
            'result = document_symbols("src/services/order.py")',
            "if result.success:",
            '    print(f"{result.symbol_count} symbols:")',
            "    for sym in result.symbols:",
            '        print(f"  {sym.kind} {sym.name} (line {sym.line})")',
            "else:",
            '    print("Could not list symbols")',
        ])),
        msg_tool_response(
            'DocumentSymbolsResult(success=True, symbol_count=5, symbols=['
            'DocumentSymbol(name="OrderService", kind="class", line=10, end_line=80, children=[]), '
            'DocumentSymbol(name="create_order", kind="function", line=15, end_line=30, children=[]), '
            'DocumentSymbol(name="cancel_order", kind="function", line=32, end_line=45, children=[]), '
            'DocumentSymbol(name="get_order", kind="function", line=47, end_line=55, children=[]), '
            'DocumentSymbol(name="ORDER_STATUS", kind="variable", line=5, end_line=5, children=[])'
            '], parse_error=None)'
        ),
        msg_assistant_text(
            "5 symbols in src/services/order.py:\n"
            "  class OrderService (line 10)\n"
            "  function create_order (line 15)\n"
            "  function cancel_order (line 32)\n"
            "  function get_order (line 47)\n"
            "  variable ORDER_STATUS (line 5)"
        ),
        msg_user("Run the tests for the order service"),
        msg_assistant_tool("\n".join([
            'result = pytest_run("tests/test_order.py")',
            'print(f"Passed: {result.passed}, Failed: {result.failed}")',
            'print(f"Duration: {result.duration:.2f}s")',
            "if result.failed > 0:",
            "    for t in result.tests:",
            '        if t.outcome == "failed":',
            '            print(f"  FAIL: {t.name}")',
        ])),
    ]})

    # --- 17: git_status with untracked -> user asks to lint new files ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Show git status"),
        msg_assistant_tool("\n".join([
            'result = git_status(".")',
            "if not result.clean:",
            '    print(f"{result.file_count} files:")',
            "    for f in result.files:",
            '        print(f"  {f.file} ({f.status})")',
            "else:",
            '    print("Clean")',
        ])),
        msg_tool_response(
            'GitStatusResult(success=True, clean=False, file_count=3, files=['
            'GitFile(file="src/new_module.py", status="untracked", staged=False), '
            'GitFile(file="src/utils.py", status="modified", staged=True), '
            'GitFile(file="tests/test_new.py", status="untracked", staged=False)'
            '], parse_error=None)'
        ),
        msg_assistant_text(
            "3 files:\n"
            "  src/new_module.py (untracked)\n"
            "  src/utils.py (modified)\n"
            "  tests/test_new.py (untracked)"
        ),
        msg_user("Lint the new module before I commit it"),
        msg_assistant_tool("\n".join([
            'result = ruff_check("src/new_module.py")',
            "if result.success:",
            '    print("No lint violations in src/new_module.py")',
            "else:",
            '    print(f"{result.violation_count} violations:")',
            "    for v in result.violations:",
            '        print(f"  line {v.line}: {v.code} {v.message}")',
        ])),
    ]})

    # --- 18: hover -> user asks for document_symbols ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Show hover info for Router in src/api/routes.py line 5"),
        msg_assistant_tool("\n".join([
            'result = hover("src/api/routes.py", 5, 6, "Router")',
            "if result.success:",
            '    print(f"Symbol: {result.symbol}")',
            '    print(f"Type: {result.type_info}")',
            "else:",
            '    print("No hover info")',
        ])),
        msg_tool_response(
            'HoverResult(success=True, symbol="Router", type_info="class Router(builtins.object)", '
            'documentation="HTTP request router.", parse_error=None)'
        ),
        msg_assistant_text(
            "Router:\n"
            "  Type: class Router(builtins.object)\n"
            "  Docs: HTTP request router."
        ),
        msg_user("Show all symbols in that file"),
        msg_assistant_tool("\n".join([
            'result = document_symbols("src/api/routes.py")',
            "if result.success:",
            '    print(f"{result.symbol_count} symbols:")',
            "    for sym in result.symbols:",
            '        print(f"  {sym.kind} {sym.name} (line {sym.line})")',
            "else:",
            '    print("No symbols found")',
        ])),
    ]})

    # --- 19: pytest success -> user asks for git_diff ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Run tests/test_auth.py"),
        msg_assistant_tool("\n".join([
            'result = pytest_run("tests/test_auth.py")',
            'print(f"Passed: {result.passed}, Failed: {result.failed}")',
            'print(f"Duration: {result.duration:.2f}s")',
        ])),
        msg_tool_response(
            'TestResult(success=True, passed=6, failed=0, skipped=0, duration=1.2, tests=[], parse_error=None)'
        ),
        msg_assistant_text("All 6 tests passed (1.20s)."),
        msg_user("Show the unstaged diff so I can review before committing"),
        msg_assistant_tool("\n".join([
            'result = git_diff(".", staged=False)',
            "if result.file_count > 0:",
            '    print(f"{result.file_count} files changed")',
            '    print(f"+{result.additions} -{result.deletions}")',
            "    for f in result.files:",
            '        print(f"  {f.file}: +{f.additions} -{f.deletions}")',
            "else:",
            '    print("No unstaged changes")',
        ])),
    ]})

    # --- 20: typecheck success -> user asks for workspace_symbols ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Run type checking on src/models/"),
        msg_assistant_tool("\n".join([
            'result = typecheck("src/models")',
            "if result.success:",
            '    print("No type errors")',
            "else:",
            '    print(f"{result.error_count} errors")',
            "    for err in result.errors:",
            '        print(f"  {err.file}:{err.line} {err.message}")',
        ])),
        msg_tool_response(
            'TypeCheckResult(success=True, error_count=0, warning_count=0, errors=[], parse_error=None)'
        ),
        msg_assistant_text("No type errors in src/models/."),
        msg_user("Search the workspace for all Model classes"),
        msg_assistant_tool("\n".join([
            'result = workspace_symbols("Model")',
            "if result.success:",
            '    print(f"Found {result.symbol_count} Model symbols:")',
            "    for sym in result.symbols:",
            '        print(f"  {sym.kind} {sym.name} in {sym.file}:{sym.line}")',
            "else:",
            '    print("No symbols found")',
        ])),
    ]})

    return examples[:20]


# ---------------------------------------------------------------------------
# Category 4: Field Access with Boolean Filters (10 examples) -- ROOT CAUSE #6
# ---------------------------------------------------------------------------

def create_boolean_filter_examples() -> list[dict]:
    """Create 10 examples using .fixable, .staged, .success as boolean filters."""
    examples = []

    # --- 1: Filter fixable ruff violations ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Show only fixable lint violations in src/"),
        msg_assistant_tool("\n".join([
            'result = ruff_check("src")',
            "fixable = [v for v in result.violations if v.fixable]",
            "not_fixable = [v for v in result.violations if not v.fixable]",
            'print(f"Fixable: {len(fixable)}")',
            "for v in fixable:",
            '    print(f"  {v.file}:{v.line} {v.code} {v.message}")',
            'print(f"\\nNot fixable: {len(not_fixable)}")',
            "for v in not_fixable:",
            '    print(f"  {v.file}:{v.line} {v.code} {v.message}")',
        ])),
    ]})

    # --- 2: Count auto-fixable ---
    examples.append({"messages": [
        msg_system(),
        msg_user("How many of the ruff violations can be auto-fixed?"),
        msg_assistant_tool("\n".join([
            'result = ruff_check("src")',
            "fixable = [v for v in result.violations if v.fixable]",
            'print(f"Total violations: {result.violation_count}")',
            'print(f"Auto-fixable: {len(fixable)}")',
            'print(f"Manual fix needed: {result.violation_count - len(fixable)}")',
            "if fixable:",
            '    print("\\nFixable rules:")',
            "    codes = set(v.code for v in fixable)",
            "    for code in sorted(codes):",
            "        count = sum(1 for v in fixable if v.code == code)",
            '        print(f"  {code}: {count}")',
        ])),
    ]})

    # --- 3: Filter staged git files ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Show only staged files ready for commit"),
        msg_assistant_tool("\n".join([
            'result = git_status(".")',
            "staged = [f for f in result.files if f.staged]",
            "unstaged = [f for f in result.files if not f.staged]",
            'print(f"Ready to commit ({len(staged)} files):")',
            "for f in staged:",
            '    print(f"  {f.file} ({f.status})")',
            'print(f"\\nNot staged ({len(unstaged)} files):")',
            "for f in unstaged:",
            '    print(f"  {f.file} ({f.status})")',
        ])),
    ]})

    # --- 4: Filter unstaged only ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Filter git status to show only unstaged changes"),
        msg_assistant_tool("\n".join([
            'result = git_status(".")',
            "unstaged = [f for f in result.files if not f.staged]",
            "if unstaged:",
            '    print(f"{len(unstaged)} unstaged files:")',
            "    for f in unstaged:",
            '        print(f"  {f.file} ({f.status})")',
            "else:",
            '    print("All changes are staged")',
        ])),
    ]})

    # --- 5: Count staged vs unstaged ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Count staged vs unstaged files"),
        msg_assistant_tool("\n".join([
            'result = git_status(".")',
            "staged = [f for f in result.files if f.staged]",
            "unstaged = [f for f in result.files if not f.staged]",
            'print(f"Staged: {len(staged)} files")',
            'print(f"Unstaged: {len(unstaged)} files")',
            'print(f"Total: {result.file_count} files")',
        ])),
    ]})

    # --- 6: Check .success as boolean across tools ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Run all quality checks and tell me which ones passed"),
        msg_assistant_tool("\n".join([
            'ruff = ruff_check("src")',
            'ty = typecheck("src")',
            'tests = pytest_run("tests")',
            "",
            "checks = [",
            '    ("Lint (ruff)", ruff.success),',
            '    ("Types (ty)", ty.success),',
            '    ("Tests (pytest)", tests.success),',
            "]",
            "",
            "for name, passed in checks:",
            '    status = "PASS" if passed else "FAIL"',
            '    print(f"  {status}: {name}")',
            "",
            "all_pass = all(s for _, s in checks)",
            'overall = "ALL PASSED" if all_pass else "SOME FAILED"',
            'print(f"\\nOverall: {overall}")',
        ])),
    ]})

    # --- 7: Check if tests pass with .success ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Check if tests pass, and if not, show the failures"),
        msg_assistant_tool("\n".join([
            'result = pytest_run("tests")',
            "if not result.success:",
            '    print(f"FAILED: {result.failed} tests failed out of {result.passed + result.failed}")',
            "    for t in result.tests:",
            '        if t.outcome == "failed":',
            '            print(f"  {t.name}: {t.message}")',
            "else:",
            '    print(f"All {result.passed} tests passed in {result.duration:.2f}s")',
        ])),
    ]})

    # --- 8: Type check with .success gate ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Check types and only show output if there are errors"),
        msg_assistant_tool("\n".join([
            'result = typecheck("src")',
            "if not result.success:",
            '    print(f"{result.error_count} type errors found:")',
            "    for err in result.errors:",
            '        print(f"  {err.file}:{err.line} {err.message}")',
            "    if result.warning_count > 0:",
            '        print(f"\\nAlso {result.warning_count} warnings")',
            "else:",
            '    print("Type check clean")',
        ])),
    ]})

    # --- 9: List only failed tests ---
    examples.append({"messages": [
        msg_system(),
        msg_user("List only the failed tests with their error messages"),
        msg_assistant_tool("\n".join([
            'result = pytest_run("tests")',
            'failed_tests = [t for t in result.tests if t.outcome == "failed"]',
            "if failed_tests:",
            '    print(f"{len(failed_tests)} failed tests:")',
            "    for t in failed_tests:",
            '        print(f"  {t.name}")',
            "        if t.message:",
            '            print(f"    Error: {t.message[:100]}")',
            "else:",
            '    print(f"All {result.passed} tests passed!")',
        ])),
    ]})

    # --- 10: Separate fixable from unfixable ---
    examples.append({"messages": [
        msg_system(),
        msg_user("Lint src/ and separate fixable from unfixable violations"),
        msg_assistant_tool("\n".join([
            'result = ruff_check("src")',
            "if not result.success:",
            "    fixable = [v for v in result.violations if v.fixable]",
            "    unfixable = [v for v in result.violations if not v.fixable]",
            "",
            "    if fixable:",
            '        print(f"Auto-fixable ({len(fixable)}):")',
            "        for v in fixable:",
            '            print(f"  {v.file}:{v.line} {v.code} {v.message}")',
            "",
            "    if unfixable:",
            '        print(f"\\nManual fix needed ({len(unfixable)}):")',
            "        for v in unfixable:",
            '            print(f"  {v.file}:{v.line} {v.code} {v.message}")',
            "else:",
            '    print("No violations found")',
        ])),
    ]})

    return examples[:10]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    """Generate all Phase 28 targeted examples and split into train/valid."""
    output_dir = Path("data/phase28_targeted")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_examples = []

    print("Category 1: Multi-Tool Chaining...")
    cat1 = create_multi_tool_chaining_examples()
    all_examples.extend(cat1)
    print(f"  Generated {len(cat1)} examples")

    print("Category 2: Document/Workspace Symbols Identity...")
    cat2 = create_symbol_identity_examples()
    all_examples.extend(cat2)
    print(f"  Generated {len(cat2)} examples")

    print("Category 3: Multi-Turn Follow-Through...")
    cat3 = create_multi_turn_follow_through_examples()
    all_examples.extend(cat3)
    print(f"  Generated {len(cat3)} examples")

    print("Category 4: Field Access with Boolean Filters...")
    cat4 = create_boolean_filter_examples()
    all_examples.extend(cat4)
    print(f"  Generated {len(cat4)} examples")

    total = len(all_examples)
    print(f"\nTotal examples: {total}")

    # Shuffle all examples
    random.shuffle(all_examples)

    # Split 90/10 into train/valid
    split_point = int(total * 0.9)
    train_examples = all_examples[:split_point]
    valid_examples = all_examples[split_point:]

    # Write train.jsonl
    train_file = output_dir / "train.jsonl"
    with open(train_file, "w") as f:
        for ex in train_examples:
            f.write(json.dumps(ex) + "\n")

    # Write valid.jsonl
    valid_file = output_dir / "valid.jsonl"
    with open(valid_file, "w") as f:
        for ex in valid_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\nTrain: {len(train_examples)} examples -> {train_file}")
    print(f"Valid: {len(valid_examples)} examples -> {valid_file}")

    # Print distribution stats
    print("\n=== Distribution ===")

    # By category
    print("\nBy category:")
    print(f"  Multi-Tool Chaining: {len(cat1)}")
    print(f"  Symbol Identity: {len(cat2)}")
    print(f"  Multi-Turn Follow-Through: {len(cat3)}")
    print(f"  Boolean Filters: {len(cat4)}")

    # By turn count
    single_turn = sum(1 for ex in all_examples if len(ex["messages"]) == 3)
    multi_turn = sum(1 for ex in all_examples if len(ex["messages"]) > 3)
    print("\nBy turn count:")
    print(f"  Single-turn: {single_turn} ({single_turn / total * 100:.1f}%)")
    print(f"  Multi-turn: {multi_turn} ({multi_turn / total * 100:.1f}%)")

    # Count tool calls per example
    multi_tool_single_block = 0
    for ex in all_examples:
        for msg in ex["messages"]:
            if msg["role"] == "assistant" and "<tool_call>" in msg.get("content", ""):
                code = msg["content"]
                # Count distinct tool function calls in the code block
                tool_funcs = [
                    "ruff_check", "typecheck", "pytest_run",
                    "goto_definition", "find_references", "hover",
                    "document_symbols", "workspace_symbols",
                    "git_status", "git_diff", "git_log", "read_file",
                ]
                calls = sum(1 for fn in tool_funcs if fn + "(" in code)
                if calls >= 2:
                    multi_tool_single_block += 1
                    break

    print(f"\nMulti-tool single code block: {multi_tool_single_block}")

    # Check that all examples have system message
    has_system = sum(
        1 for ex in all_examples
        if ex["messages"][0]["role"] == "system"
    )
    print(f"With system message: {has_system}/{total}")

    # Check no preamble before tool calls
    no_preamble_issues = 0
    for ex in all_examples:
        for msg in ex["messages"]:
            if msg["role"] == "assistant" and "<tool_call>" in msg.get("content", ""):
                if not msg["content"].startswith("<tool_call>"):
                    no_preamble_issues += 1
    print(f"Preamble before tool_call: {no_preamble_issues} (should be 0)")


if __name__ == "__main__":
    main()
