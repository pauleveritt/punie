#!/usr/bin/env python3
"""Generate high-quality cross-tool training examples for Phase 28.

Focus: Teach multi-step workflows where model must call ALL tools in sequence.

Key patterns:
1. tool1() → access results → tool2() using those results
2. Realistic workflows (not "workflow N" loops)
3. Explicit examples showing ALL tools called
4. Clear dependencies between tool calls

Target: ~75 examples across 5 categories
"""

import json
import random
from pathlib import Path


def generate_git_workflows():
    """Generate git + file reading workflows (15 examples)."""
    examples = []

    # Pattern 1: git diff → read changed files (5 examples)
    diff_read_queries = [
        "Show git diff and read the modified files",
        "Get uncommitted changes and display file contents",
        "Check what files changed and show their content",
        "Review git diff then read the affected files",
        "Display file changes and their current state",
    ]

    for query in diff_read_queries:
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": """I'll check the git diff first, then read the modified files.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Get git diff to see what changed
diff_result = git_diff(".", staged=False)

if diff_result.file_count > 0:
    print(f"Found {diff_result.file_count} modified files:")

    # Step 2: Read each modified file
    for file in diff_result.files:
        print(f"\\n=== {file.file} ===")
        content = read_file(file.file)
        print(content[:500])  # First 500 chars
else:
    print("No uncommitted changes found")
</parameter>
</function></tool_call>"""}
            ]
        })

    # Pattern 2: git status → git diff staged (5 examples)
    status_diff_queries = [
        "Check git status and show staged file diffs",
        "List uncommitted changes and diff the staged ones",
        "Show what's staged and review those changes",
        "Check repo status then diff staged files",
        "Display uncommitted files and their staged diffs",
    ]

    for query in status_diff_queries:
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": """I'll check git status first to see what's uncommitted, then diff the staged files.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Get git status to see all changes
status_result = git_status(".")

print(f"Repository status: {'clean' if status_result.clean else 'has changes'}")
print(f"Total files: {status_result.file_count}")

# Count staged files
staged_files = [f for f in status_result.files if f.staged]
print(f"Staged files: {len(staged_files)}")

if staged_files:
    # Step 2: Get diff for staged files
    diff_result = git_diff(".", staged=True)
    print(f"\\nStaged changes: +{diff_result.additions} -{diff_result.deletions}")

    for file in diff_result.files:
        print(f"  {file.file}: +{file.additions} -{file.deletions}")
else:
    print("No staged files to diff")
</parameter>
</function></tool_call>"""}
            ]
        })

    # Pattern 3: git log → git diff specific commit (5 examples)
    log_diff_queries = [
        "Show recent commits and diff the latest one",
        "List commit history and show what changed in the last commit",
        "Get git log then diff the most recent commit",
        "Display recent commits with the latest diff",
        "Show commit history and changes in HEAD",
    ]

    for query in log_diff_queries:
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": """I'll get the commit history first, then show the diff for the latest commit.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Get recent commit history
log_result = git_log(".", count=5)

if log_result.commit_count > 0:
    print(f"Recent {log_result.commit_count} commits:")
    for commit in log_result.commits:
        print(f"  {commit.hash} by {commit.author}")
        print(f"    {commit.message}")

    # Step 2: Diff the latest commit
    latest = log_result.commits[0]
    print(f"\\n=== Changes in {latest.hash} ===")

    # Get diff (comparing HEAD vs working tree as proxy for commit diff)
    diff_result = git_diff(".", staged=False)
    if diff_result.file_count > 0:
        print(f"Files changed: {diff_result.file_count}")
        for file in diff_result.files:
            print(f"  {file.file}: +{file.additions} -{file.deletions}")
else:
    print("No commits found")
</parameter>
</function></tool_call>"""}
            ]
        })

    return examples


def generate_quality_check_workflows():
    """Generate ruff + pytest + typecheck workflows (15 examples)."""
    examples = []

    # Pattern 1: Full quality check - ALL THREE tools (5 examples)
    full_check_queries = [
        "Run complete quality check: ruff, pytest, and typecheck",
        "Execute full code quality suite (lint, test, types)",
        "Check code quality with all tools: ruff, typecheck, pytest",
        "Run comprehensive quality analysis with all checkers",
        "Perform full validation: linting, type checking, and tests",
    ]

    for query in full_check_queries:
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": """I'll run all three quality checks: ruff for linting, typecheck for types, and pytest for tests.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Run ruff linter
print("=== Linting with ruff ===")
ruff_result = ruff_check("src/")
print(f"Violations: {ruff_result.violation_count}")
if ruff_result.violation_count > 0:
    for v in ruff_result.violations[:3]:
        print(f"  {v.file}:{v.line} - {v.code}: {v.message}")

# Step 2: Run type checker
print("\\n=== Type checking with ty ===")
type_result = typecheck("src/")
print(f"Type errors: {type_result.error_count}")
if type_result.error_count > 0:
    for err in type_result.errors[:3]:
        print(f"  {err.file}:{err.line} - {err.message}")

# Step 3: Run pytest
print("\\n=== Running tests ===")
test_result = pytest_run("tests/")
print(f"Tests: {test_result.passed} passed, {test_result.failed} failed")
if test_result.failed > 0:
    for test in test_result.tests:
        if test.outcome == "failed":
            print(f"  FAIL: {test.name}")

# Summary
print("\\n=== Summary ===")
print(f"Lint: {'✓' if ruff_result.violation_count == 0 else '✗'}")
print(f"Types: {'✓' if type_result.error_count == 0 else '✗'}")
print(f"Tests: {'✓' if test_result.failed == 0 else '✗'}")
</parameter>
</function></tool_call>"""}
            ]
        })

    # Pattern 2: typecheck → ruff (fix type errors then lint) (5 examples)
    type_then_lint_queries = [
        "Check types first, then run ruff on the same files",
        "Type check the code and lint any files with errors",
        "Run typecheck followed by ruff linting",
        "Validate types then check code style with ruff",
        "First check types, then lint the codebase",
    ]

    for query in type_then_lint_queries:
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": """I'll check types first, then run ruff linting.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Type check
print("=== Type checking ===")
type_result = typecheck("src/")
print(f"Type errors: {type_result.error_count}")

if type_result.error_count > 0:
    print("\\nFiles with type errors:")
    error_files = set(err.file for err in type_result.errors)
    for file in list(error_files)[:5]:
        print(f"  {file}")

# Step 2: Lint the codebase
print("\\n=== Linting with ruff ===")
ruff_result = ruff_check("src/")
print(f"Violations: {ruff_result.violation_count}")

if ruff_result.violation_count > 0:
    fixable = [v for v in ruff_result.violations if v.fixable]
    print(f"Fixable violations: {len(fixable)}")
    for v in fixable[:3]:
        print(f"  {v.file}:{v.line} - {v.code}")
</parameter>
</function></tool_call>"""}
            ]
        })

    # Pattern 3: pytest → ruff on failures (5 examples)
    test_then_lint_queries = [
        "Run tests and lint any failing test files",
        "Execute pytest then ruff check on failed tests",
        "Test the code and lint failures with ruff",
        "Run tests first, then lint the failing test files",
        "Check tests and apply ruff to any failures",
    ]

    for query in test_then_lint_queries:
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": """I'll run tests first, then lint any files with failing tests.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Run pytest
print("=== Running tests ===")
test_result = pytest_run("tests/")
print(f"Results: {test_result.passed} passed, {test_result.failed} failed")

if test_result.failed > 0:
    # Get unique files with failures
    failed_files = set()
    for test in test_result.tests:
        if test.outcome == "failed":
            print(f"  FAIL: {test.name}")
            # Extract file path from test name (e.g., tests/test_foo.py::test_bar)
            if "::" in test.name:
                test_file = test.name.split("::")[0]
                failed_files.add(test_file)

    # Step 2: Lint the failing test files
    if failed_files:
        print(f"\\n=== Linting {len(failed_files)} failing test files ===")
        for test_file in list(failed_files)[:3]:
            lint_result = ruff_check(test_file)
            print(f"\\n{test_file}: {lint_result.violation_count} violations")
else:
    print("\\nAll tests passed! No need to lint failures.")
</parameter>
</function></tool_call>"""}
            ]
        })

    return examples


def generate_lsp_workflows():
    """Generate LSP multi-tool workflows (15 examples)."""
    examples = []

    # Pattern 1: goto_definition → hover (5 examples)
    goto_hover_queries = [
        "Find UserService definition and show hover info",
        "Go to LSPClient definition then get hover details",
        "Locate process_data definition and show type information",
        "Jump to TypeChecker definition and display hover",
        "Find execute_code definition and show its signature",
    ]

    for query in goto_hover_queries:
        symbol = query.split("Find ")[-1].split(" ")[0] if "Find " in query else "Symbol"
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": f"""I'll find the {symbol} definition first, then show hover information.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Find definition
print("=== Finding {symbol} definition ===")
def_result = goto_definition("src/app.py", 10, 5, "{symbol}")

if def_result.success and def_result.locations:
    loc = def_result.locations[0]
    print(f"Found at {{{loc.file}}}:{{{loc.line}}}:{{{loc.column}}}")

    # Step 2: Get hover info at that location
    print("\\n=== Hover information ===")
    hover_result = hover(loc.file, loc.line, loc.column, "{symbol}")

    if hover_result.success:
        print(f"Symbol: {{{hover_result.symbol}}}")
        if hover_result.content:
            print(f"Content ({{{hover_result.language}}}):")
            print(f"  {{{hover_result.content[:200]}}}")
    else:
        print("No hover information available")
else:
    print("Definition not found")
</parameter>
</function></tool_call>"""}
            ]
        })

    # Pattern 2: find_references → read_file (5 examples)
    refs_read_queries = [
        "Find all references to execute_code and read those files",
        "Locate references to LSPClient and show file contents",
        "Search for process_data references and display the files",
        "Find where TypeChecker is used and read those locations",
        "Get references to git_status and show the calling code",
    ]

    for query in refs_read_queries:
        symbol = query.split("to ")[-1].split(" ")[0] if " to " in query else "execute_code"
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": f"""I'll find all references to {symbol} first, then read the relevant files.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Find references
print("=== Finding {symbol} references ===")
refs_result = find_references("src/main.py", 25, 10, "{symbol}")

if refs_result.success and refs_result.reference_count > 0:
    print(f"Found {refs_result.reference_count} references")

    # Get unique files
    ref_files = set(ref.file for ref in refs_result.references)
    print(f"In {{len(ref_files)}} files")

    # Step 2: Read each file
    for file in list(ref_files)[:3]:  # Limit to first 3 files
        print(f"\\n=== {file} ===")
        content = read_file(file)
        # Show first 300 chars
        print(content[:300])
else:
    print("No references found")
</parameter>
</function></tool_call>"""}
            ]
        })

    # Pattern 3: workspace_symbols → document_symbols (5 examples)
    workspace_doc_queries = [
        "Search workspace for GitStatusResult then show its document symbols",
        "Find LSPClient across workspace and display its structure",
        "Locate TypeChecker in workspace and list its symbols",
        "Search for TestResult and show document structure",
        "Find UserService workspace-wide then show file symbols",
    ]

    for query in workspace_doc_queries:
        symbol = query.split("for ")[-1].split(" ")[0] if " for " in query else "GitStatusResult"
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": f"""I'll search the workspace for {symbol} first, then show the document structure.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Search workspace
print("=== Searching workspace for {symbol} ===")
search_result = workspace_symbols("{symbol}")

if search_result.success and search_result.symbol_count > 0:
    print(f"Found {{search_result.symbol_count}} matches")

    # Get first match
    match = search_result.symbols[0]
    print(f"\\nBest match: {{match.name}} in {{match.file}}")

    # Step 2: Get document symbols for that file
    print(f"\\n=== Document structure of {{match.file}} ===")
    doc_result = document_symbols(match.file)

    if doc_result.success:
        print(f"Found {{doc_result.symbol_count}} symbols:")
        for sym in doc_result.symbols[:5]:
            print(f"  {{sym.name}} ({{sym.kind}}) at line {{sym.line}}")
            if sym.children:
                for child in sym.children[:2]:
                    print(f"    - {{child.name}}")
    else:
        print("Could not get document structure")
else:
    print("Symbol not found in workspace")
</parameter>
</function></tool_call>"""}
            ]
        })

    return examples


def generate_mixed_workflows():
    """Generate git + code analysis workflows (15 examples)."""
    examples = []

    # Pattern 1: git diff → ruff changed files (5 examples)
    diff_ruff_queries = [
        "Get git diff and lint the modified files with ruff",
        "Check uncommitted changes and run ruff on them",
        "Show git diff then lint those files",
        "Find modified files and check them with ruff",
        "Review changes and apply ruff linting",
    ]

    for query in diff_ruff_queries:
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": """I'll check the git diff first, then lint the modified files.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Get git diff
print("=== Git diff ===")
diff_result = git_diff(".", staged=False)

if diff_result.file_count > 0:
    print(f"Modified files: {diff_result.file_count}")

    # Filter Python files
    py_files = [f.file for f in diff_result.files if f.file.endswith('.py')]
    print(f"Python files: {len(py_files)}")

    # Step 2: Lint each modified Python file
    if py_files:
        print("\\n=== Linting modified files ===")
        for file in py_files[:3]:
            lint_result = ruff_check(file)
            print(f"\\n{file}: {lint_result.violation_count} violations")
            if lint_result.violation_count > 0:
                for v in lint_result.violations[:2]:
                    print(f"  {v.line}: {v.code} - {v.message}")
else:
    print("No uncommitted changes")
</parameter>
</function></tool_call>"""}
            ]
        })

    # Pattern 2: git status → typecheck staged (5 examples)
    status_typecheck_queries = [
        "Check git status and typecheck staged Python files",
        "List staged files and run type checking on them",
        "Show git status then validate types in staged changes",
        "Get staged files and check their types",
        "Review staged changes and run typecheck",
    ]

    for query in status_typecheck_queries:
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": """I'll check git status first, then typecheck the staged Python files.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Get git status
print("=== Git status ===")
status_result = git_status(".")

if not status_result.clean:
    staged_files = [f for f in status_result.files if f.staged]
    print(f"Staged files: {len(staged_files)}")

    # Filter Python files
    staged_py = [f.file for f in staged_files if f.file.endswith('.py')]

    if staged_py:
        print(f"Staged Python files: {len(staged_py)}")

        # Step 2: Typecheck staged Python files
        print("\\n=== Type checking staged files ===")
        for file in staged_py[:3]:
            type_result = typecheck(file)
            print(f"\\n{file}: {type_result.error_count} errors")
            if type_result.error_count > 0:
                for err in type_result.errors[:2]:
                    print(f"  {err.line}: {err.message}")
    else:
        print("No Python files staged")
else:
    print("Working tree clean")
</parameter>
</function></tool_call>"""}
            ]
        })

    # Pattern 3: document_symbols → ruff (analyze structure then lint) (5 examples)
    symbols_ruff_queries = [
        "List document symbols then lint the file with ruff",
        "Show file structure and check code style",
        "Get document symbols and run ruff analysis",
        "Display file symbols then apply linting",
        "Analyze structure and check for style violations",
    ]

    for query in symbols_ruff_queries:
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": """I'll get the document structure first, then lint the file.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Get document symbols
print("=== Document structure ===")
doc_result = document_symbols("src/models/user.py")

if doc_result.success:
    print(f"Symbols: {{doc_result.symbol_count}}")
    for sym in doc_result.symbols:
        print(f"  {{sym.name}} ({{sym.kind}}) at line {{sym.line}}")

    # Step 2: Lint the same file
    print("\\n=== Linting ===")
    lint_result = ruff_check("src/models/user.py")
    print(f"Violations: {lint_result.violation_count}")

    if lint_result.violation_count > 0:
        for v in lint_result.violations[:3]:
            print(f"  {v.line}: {v.code} - {v.message}")
else:
    print("Could not get document structure")
</parameter>
</function></tool_call>"""}
            ]
        })

    return examples


def generate_advanced_workflows():
    """Generate complex multi-step workflows (15 examples)."""
    examples = []

    # Pattern 1: goto_def → read_file → ruff (find, read, lint) (5 examples)
    goto_read_lint_queries = [
        "Find UserService definition, read it, then lint the file",
        "Go to execute_code, show its code, and check style",
        "Locate TypeChecker, read the implementation, and run ruff",
        "Jump to LSPClient, display it, then check for violations",
        "Find process_data definition, read it, and lint",
    ]

    for query in goto_read_lint_queries:
        symbol = query.split("Find ")[-1].split(" ")[0] if "Find " in query else "Symbol"
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": f"""I'll find {symbol}, read its implementation, then lint the file.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Find definition
print("=== Finding {symbol} ===")
def_result = goto_definition("src/app.py", 15, 8, "{symbol}")

if def_result.success and def_result.locations:
    loc = def_result.locations[0]
    print(f"Found at {{loc.file}}:{{loc.line}}")

    # Step 2: Read the file
    print(f"\\n=== Reading {{loc.file}} ===")
    read_result = read_file(loc.file)
    if read_result.success:
        # Show excerpt around definition
        lines = read_result.content.split("\\n")
        start = max(0, loc.line - 5)
        end = min(len(lines), loc.line + 10)
        for i, line in enumerate(lines[start:end], start=start+1):
            marker = ">>>" if i == loc.line else "   "
            print(f"{marker} {i:4d} {line}")

    # Step 3: Lint the file
    print(f"\\n=== Linting {{loc.file}} ===")
    lint_result = ruff_check(loc.file)
    print(f"Violations: {lint_result.violation_count}")
    if lint_result.violation_count > 0:
        for v in lint_result.violations[:3]:
            print(f"  {v.line}: {v.code} - {v.message}")
else:
    print("Definition not found")
</parameter>
</function></tool_call>"""}
            ]
        })

    # Pattern 2: workspace_symbols → hover → find_references (5 examples)
    search_hover_refs_queries = [
        "Search workspace for GitStatusResult, show hover, find references",
        "Find LSPClient everywhere, get type info, list references",
        "Locate TestResult, show signature, find all uses",
        "Search for TypeChecker, display hover, locate references",
        "Find UserService workspace-wide, show type, list usages",
    ]

    for query in search_hover_refs_queries:
        symbol = query.split("for ")[-1].split(",")[0].strip() if " for " in query else "GitStatusResult"
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": f"""I'll search for {symbol}, get hover info, then find all references.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Search workspace
print("=== Workspace search for {symbol} ===")
search_result = workspace_symbols("{symbol}")

if search_result.success and search_result.symbol_count > 0:
    match = search_result.symbols[0]
    print(f"Found: {{match.name}} in {{match.location.file}}:{{match.location.line}}")

    # Step 2: Get hover info
    print("\\n=== Hover information ===")
    hover_result = hover(match.location.file, match.location.line, match.location.column, "{symbol}")
    if hover_result.success:
        print(f"Type: {hover_result.type_info or 'N/A'}")
        if hover_result.docstring:
            print(f"Docs: {{hover_result.docstring[:150]}}")

    # Step 3: Find all references
    print("\\n=== Finding references ===")
    refs_result = find_references(match.location.file, match.location.line, match.location.column, "{symbol}")
    if refs_result.success:
        print(f"References: {refs_result.reference_count}")
        for ref in refs_result.references[:5]:
            print(f"  {{ref.file}}:{{ref.line}}")
else:
    print("Symbol not found")
</parameter>
</function></tool_call>"""}
            ]
        })

    # Pattern 3: git log → git diff → read_file (5 examples)
    log_diff_read_queries = [
        "Show git log, diff the latest commit, read changed files",
        "List commits, check latest changes, display file contents",
        "Review commit history, diff HEAD, read modified files",
        "Get git log, show recent diff, read the changes",
        "Display commits, diff latest, show file contents",
    ]

    for query in log_diff_read_queries:
        examples.append({
            "messages": [
                {"role": "system", "content": "You are Punie, an AI coding assistant with access to Python tools."},
                {"role": "user", "content": query},
                {"role": "assistant", "content": """I'll get commit history, diff the latest, then read the changed files.

<tool_call><function=execute_code>
<parameter=code>
# Step 1: Get git log
print("=== Recent commits ===")
log_result = git_log(".", count=3)

if log_result.commit_count > 0:
    for commit in log_result.commits:
        print(f"{commit.hash} by {commit.author}")
        print(f"  {commit.message}")

    latest = log_result.commits[0]

    # Step 2: Git diff (proxy for commit changes)
    print(f"\\n=== Changes in {latest.hash} ===")
    diff_result = git_diff(".", staged=False)

    if diff_result.file_count > 0:
        print(f"Modified: {diff_result.file_count} files")

        # Step 3: Read changed files
        for file in diff_result.files[:2]:
            print(f"\\n=== {file.file} ===")
            read_result = read_file(file.file)
            if read_result.success:
                print(read_result.content[:200])
    else:
        print("No uncommitted changes to show")
else:
    print("No commits found")
</parameter>
</function></tool_call>"""}
            ]
        })

    return examples


def main():
    """Generate all cross-tool training examples."""
    print("Generating Phase 28 cross-tool training examples...")

    # Generate examples
    git_examples = generate_git_workflows()
    quality_examples = generate_quality_check_workflows()
    lsp_examples = generate_lsp_workflows()
    mixed_examples = generate_mixed_workflows()
    advanced_examples = generate_advanced_workflows()

    all_examples = (
        git_examples +
        quality_examples +
        lsp_examples +
        mixed_examples +
        advanced_examples
    )

    print(f"\nGenerated {len(all_examples)} examples:")
    print(f"  Git workflows: {len(git_examples)}")
    print(f"  Quality checks: {len(quality_examples)}")
    print(f"  LSP workflows: {len(lsp_examples)}")
    print(f"  Mixed workflows: {len(mixed_examples)}")
    print(f"  Advanced workflows: {len(advanced_examples)}")

    # Add preambles to ~33% of examples
    preamble_count = 0
    for ex in all_examples:
        if random.random() < 0.33:
            # Add preamble (only for single-turn examples)
            if len(ex["messages"]) == 3:  # system, user, assistant
                preamble = random.choice([
                    "I'll help with that.",
                    "Let me handle that for you.",
                    "I'll do that now.",
                    "Let me check that.",
                    "I'll analyze that.",
                ])
                # Prepend to assistant message
                original = ex["messages"][2]["content"]
                ex["messages"][2]["content"] = f"{preamble}\n\n{original}"
                preamble_count += 1

    print(f"\nAdded preambles to {preamble_count} examples ({preamble_count/len(all_examples)*100:.1f}%)")

    # Save to file
    output_dir = Path("data/phase28_cross_tool")
    output_dir.mkdir(exist_ok=True, parents=True)

    output_file = output_dir / "train.jsonl"
    with open(output_file, "w") as f:
        for example in all_examples:
            f.write(json.dumps(example) + "\n")

    print(f"\nSaved to {output_file}")
    print(f"Total: {len(all_examples)} high-quality cross-tool examples")


if __name__ == "__main__":
    main()
