#!/usr/bin/env python3
"""Generate training examples for Phase 32 domain tools.

Covers all 12 new tools added in Phase 32:
- 3 CST code tools: cst_find_pattern, cst_rename, cst_add_import
- 9 domain validators: validate_component, check_render_tree,
  validate_escape_context, validate_service_registration,
  check_dependency_graph, validate_injection_site,
  validate_middleware_chain, check_di_template_binding,
  validate_route_pattern

Target: ~150 examples (~12-13 per tool)
Output: data/phase32_domain_tools/domain_tool_examples.jsonl
"""

import json
import random
from pathlib import Path

SYSTEM_PROMPT = """\
You are Punie, a standalone AI coding assistant.

You have direct access to the project filesystem and can run commands
in the workspace directory. You work independently without IDE integration.

Available tools:
- read_file(path): Read a file's contents
- write_file(path, content): Write content to a file
- run_command(command, args, cwd): Run a shell command
- execute_code(code): Execute Python code with multiple tool calls (Code Mode)

Code quality:
- typecheck(path): type checking
- ruff_check(path): linting
- pytest_run(path): testing

LSP navigation:
- goto_definition(file, line, col, symbol): find definition
- find_references(file, line, col, symbol): find all usages
- hover(file, line, col, symbol): type info and docstrings
- document_symbols(file): all symbols in a file
- workspace_symbols(query): search symbols across workspace

Git operations:
- git_status(path): working tree status
- git_diff(path, staged): diff output
- git_log(path, count): commit history

LibCST code tools:
- cst_find_pattern(file, pattern): find nodes by pattern
- cst_rename(file, old_name, new_name): rename symbol
- cst_add_import(file, import_stmt): add import idempotently

Domain validators (tdom-svcs):
- validate_component(file): check @dataclass + __call__ -> Node + html()
- check_render_tree(file): check component composition
- validate_escape_context(file): verify no f-strings in html()
- validate_service_registration(file): check @injectable + @dataclass + Inject[]
- check_dependency_graph(file): detect layer violations
- validate_injection_site(file): verify Inject[] types are imported
- validate_middleware_chain(file): check @middleware + __call__ signature
- check_di_template_binding(file): verify html() context= for DI
- validate_route_pattern(file): validate route path syntax

Guidelines:
- Use execute_code for multi-step queries
- Tools return structured results — parse and present relevant fields
- Read files before modifying them
"""


def make_example(query: str, code: str) -> dict:
    """Create a training example in messages format."""
    assistant_content = f"""I'll handle that using the appropriate tool.

<tool_call><function=execute_code>
<parameter=code>
{code.strip()}
</parameter>
</function></tool_call>"""
    return {
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
            {"role": "assistant", "content": assistant_content},
        ]
    }


# ---------------------------------------------------------------------------
# CST Code Tools
# ---------------------------------------------------------------------------

def generate_cst_find_pattern() -> list[dict]:
    """Generate cst_find_pattern examples (13 examples)."""
    examples = []

    cases = [
        (
            "Find all function definitions in src/punie/training/train_runner.py.",
            "src/punie/training/train_runner.py",
            "FunctionDef",
            "function definitions",
        ),
        (
            "List all class definitions in src/punie/agent/typed_tools.py.",
            "src/punie/agent/typed_tools.py",
            "ClassDef",
            "class definitions",
        ),
        (
            "Find all calls to print() in src/punie/training/lora_config.py.",
            "src/punie/training/lora_config.py",
            "call:print",
            "print() calls",
        ),
        (
            "Find all @dataclass decorators in src/punie/agent/config.py.",
            "src/punie/agent/config.py",
            "decorator:dataclass",
            "@dataclass decorators",
        ),
        (
            "List all imports in src/punie/training/eval_suites.py.",
            "src/punie/training/eval_suites.py",
            "Import",
            "import statements",
        ),
        (
            "Find all calls to json.loads() in src/punie/agent/typed_tools.py.",
            "src/punie/agent/typed_tools.py",
            "call:json.loads",
            "json.loads() calls",
        ),
        (
            "Find all @injectable decorators in src/services/user_service.py.",
            "src/services/user_service.py",
            "decorator:injectable",
            "@injectable decorators",
        ),
        (
            "Find all class definitions in src/views/home.py.",
            "src/views/home.py",
            "ClassDef",
            "class definitions",
        ),
        (
            "List all calls to html() in src/views/profile.py.",
            "src/views/profile.py",
            "call:html",
            "html() calls",
        ),
        (
            "Find all @middleware decorators in src/middleware/auth.py.",
            "src/middleware/auth.py",
            "decorator:middleware",
            "@middleware decorators",
        ),
        (
            "Find all function definitions in src/services/report_service.py.",
            "src/services/report_service.py",
            "FunctionDef",
            "function definitions",
        ),
        (
            "List all from-imports in src/punie/agent/factory.py.",
            "src/punie/agent/factory.py",
            "ImportFrom",
            "from-import statements",
        ),
        (
            "Find all calls to Inject[] in src/services/email_service.py.",
            "src/services/email_service.py",
            "call:Inject",
            "Inject[] usage",
        ),
    ]

    for query, file_path, pattern, description in cases:
        code = f"""\
# Find {description} in {file_path}
result = cst_find_pattern("{file_path}", "{pattern}")

if result.success:
    print(f"Found {{result.match_count}} {description}:")
    for match in result.matches:
        print(f"  Line {{match.line}}: {{match.node_type}} — {{match.code_snippet}}")
else:
    print(f"Parse error: {{result.parse_error}}")
"""
        examples.append(make_example(query, code))

    return examples


def generate_cst_rename() -> list[dict]:
    """Generate cst_rename examples (13 examples)."""
    examples = []

    cases = [
        (
            "Rename the class UserService to UserManager in src/services/user_service.py.",
            "src/services/user_service.py",
            "UserService",
            "UserManager",
        ),
        (
            "Rename the function process_data to handle_data in src/punie/agent/factory.py.",
            "src/punie/agent/factory.py",
            "process_data",
            "handle_data",
        ),
        (
            "Rename HomeView to HomeComponent in src/views/home.py.",
            "src/views/home.py",
            "HomeView",
            "HomeComponent",
        ),
        (
            "Rename the variable old_config to base_config in src/punie/training/lora_config.py.",
            "src/punie/training/lora_config.py",
            "old_config",
            "base_config",
        ),
        (
            "Rename AuthMiddleware to AuthenticationMiddleware in src/middleware/auth.py.",
            "src/middleware/auth.py",
            "AuthMiddleware",
            "AuthenticationMiddleware",
        ),
        (
            "Rename the function build_command to build_train_command in src/punie/training/train_runner.py.",
            "src/punie/training/train_runner.py",
            "build_command",
            "build_train_command",
        ),
        (
            "Rename ReportService to AnalyticsService in src/services/report_service.py.",
            "src/services/report_service.py",
            "ReportService",
            "AnalyticsService",
        ),
        (
            "Rename the parameter path to file_path in src/punie/agent/typed_tools.py.",
            "src/punie/agent/typed_tools.py",
            "path",
            "file_path",
        ),
        (
            "Rename ProfileView to ProfileComponent in src/views/profile.py.",
            "src/views/profile.py",
            "ProfileView",
            "ProfileComponent",
        ),
        (
            "Rename EmailService to MailService in src/services/email_service.py.",
            "src/services/email_service.py",
            "EmailService",
            "MailService",
        ),
        (
            "Rename the constant MAX_RETRIES to RETRY_LIMIT in src/punie/agent/config.py.",
            "src/punie/agent/config.py",
            "MAX_RETRIES",
            "RETRY_LIMIT",
        ),
        (
            "Rename parse_output to parse_ty_output in src/punie/agent/typed_tools.py.",
            "src/punie/agent/typed_tools.py",
            "parse_output",
            "parse_ty_output",
        ),
        (
            "Rename create_suite to create_baseline_suite in src/punie/training/eval_suites.py.",
            "src/punie/training/eval_suites.py",
            "create_suite",
            "create_baseline_suite",
        ),
    ]

    for query, file_path, old_name, new_name in cases:
        code = f"""\
# Rename {old_name!r} to {new_name!r} in {file_path}
result = cst_rename("{file_path}", "{old_name}", "{new_name}")

if result.success:
    print(f"Renamed {old_name!r} → {new_name!r} ({{result.rename_count}} replacements)")
    # Show a snippet of the modified source
    lines = result.modified_source.splitlines()
    print(f"\\nModified source ({{len(lines)}} lines):")
    for line in lines[:10]:
        print(f"  {{line}}")
else:
    print(f"Parse error: {{result.parse_error}}")
"""
        examples.append(make_example(query, code))

    return examples


def generate_cst_add_import() -> list[dict]:
    """Generate cst_add_import examples (13 examples)."""
    examples = []

    cases = [
        (
            "Add 'from pathlib import Path' to src/punie/agent/config.py if not already imported.",
            "src/punie/agent/config.py",
            "from pathlib import Path",
        ),
        (
            "Add 'import json' to src/punie/training/eval_suites.py if not already there.",
            "src/punie/training/eval_suites.py",
            "import json",
        ),
        (
            "Add 'from dataclasses import dataclass, field' to src/views/home.py.",
            "src/views/home.py",
            "from dataclasses import dataclass, field",
        ),
        (
            "Add 'from typing import Any' to src/services/user_service.py.",
            "src/services/user_service.py",
            "from typing import Any",
        ),
        (
            "Add 'from punie.agent.typed_tools import TypeCheckResult' to src/punie/http/websocket.py.",
            "src/punie/http/websocket.py",
            "from punie.agent.typed_tools import TypeCheckResult",
        ),
        (
            "Add 'import asyncio' to src/punie/training/train_runner.py.",
            "src/punie/training/train_runner.py",
            "import asyncio",
        ),
        (
            "Add 'from svcs import injectable' to src/services/report_service.py.",
            "src/services/report_service.py",
            "from svcs import injectable",
        ),
        (
            "Add 'from tdom import html, Node' to src/views/profile.py.",
            "src/views/profile.py",
            "from tdom import html, Node",
        ),
        (
            "Add 'from hopscotch import Inject' to src/services/email_service.py.",
            "src/services/email_service.py",
            "from hopscotch import Inject",
        ),
        (
            "Add 'from collections.abc import Callable' to src/middleware/auth.py.",
            "src/middleware/auth.py",
            "from collections.abc import Callable",
        ),
        (
            "Add 'from pydantic import BaseModel' to src/punie/agent/stubs.py.",
            "src/punie/agent/stubs.py",
            "from pydantic import BaseModel",
        ),
        (
            "Add 'import random' to scripts/generate_phase32_domain_tool_examples.py.",
            "scripts/generate_phase32_domain_tool_examples.py",
            "import random",
        ),
        (
            "Add 'from __future__ import annotations' to src/punie/training/lora_config.py.",
            "src/punie/training/lora_config.py",
            "from __future__ import annotations",
        ),
    ]

    for query, file_path, import_stmt in cases:
        code = f"""\
# Add import to {file_path} (idempotent)
result = cst_add_import("{file_path}", "{import_stmt}")

if result.success:
    if not result.import_added:
        print("Import already present — no changes made")
    else:
        print(f"Added: '{import_stmt}'")
        lines = result.modified_source.splitlines()
        print(f"\\nFirst 10 lines of modified file:")
        for line in lines[:10]:
            print(f"  {{line}}")
else:
    print(f"Parse error: {{result.parse_error}}")
"""
        examples.append(make_example(query, code))

    return examples


# ---------------------------------------------------------------------------
# tdom Domain Validators
# ---------------------------------------------------------------------------

def generate_validate_component() -> list[dict]:
    """Generate validate_component examples (13 examples)."""
    examples = []

    cases = [
        ("Validate the tdom component in src/views/home.py.", "src/views/home.py"),
        ("Check if src/views/profile.py follows proper tdom component patterns.", "src/views/profile.py"),
        ("Validate the component structure in src/views/dashboard.py.", "src/views/dashboard.py"),
        ("Check src/views/header.py — does it use @dataclass and __call__ -> Node correctly?", "src/views/header.py"),
        ("Verify src/views/sidebar.py is a valid tdom component.", "src/views/sidebar.py"),
        ("Validate src/views/footer.py for correct tdom component patterns.", "src/views/footer.py"),
        ("Check if src/views/nav.py follows @dataclass + __call__ -> Node + html() conventions.", "src/views/nav.py"),
        ("Is src/views/search.py a valid tdom component? Check the structure.", "src/views/search.py"),
        ("Validate component patterns in src/components/card.py.", "src/components/card.py"),
        ("Check src/components/button.py for proper tdom component structure.", "src/components/button.py"),
        ("Verify src/components/form.py follows tdom conventions.", "src/components/form.py"),
        ("Validate the tdom patterns in src/components/modal.py.", "src/components/modal.py"),
        ("Check src/components/table.py — is the component properly structured?", "src/components/table.py"),
    ]

    for query, file_path in cases:
        code = f"""\
# Validate tdom component in {file_path}
result = validate_component("{file_path}")

if result.valid:
    print(f"✓ Validation passed (domain: {{result.domain}})")
else:
    print(f"✗ Validation failed ({{len(result.issues)}} issues):")
    for issue in result.issues:
        print(f"  [{{issue.severity}}] {{issue.message}}")
        if issue.suggestion:
            print(f"    Suggestion: {{issue.suggestion}}")
if result.parse_error:
    print(f"Parse error: {{result.parse_error}}")
"""
        examples.append(make_example(query, code))

    return examples


def generate_check_render_tree() -> list[dict]:
    """Generate check_render_tree examples (13 examples)."""
    examples = []

    cases = [
        ("Check the component composition in src/views/home.py.", "src/views/home.py"),
        ("Verify the render tree in src/views/dashboard.py is valid.", "src/views/dashboard.py"),
        ("Check for broken component references in src/views/profile.py.", "src/views/profile.py"),
        ("Validate component composition patterns in src/views/admin.py.", "src/views/admin.py"),
        ("Does src/views/layout.py correctly compose its child components?", "src/views/layout.py"),
        ("Check the render tree for src/views/settings.py.", "src/views/settings.py"),
        ("Validate component references in src/views/search.py.", "src/views/search.py"),
        ("Check if all components in src/views/reports.py are properly imported.", "src/views/reports.py"),
        ("Verify the component tree structure in src/views/header.py.", "src/views/header.py"),
        ("Check component composition in src/components/page.py.", "src/components/page.py"),
        ("Validate render tree for src/components/layout.py.", "src/components/layout.py"),
        ("Check child component references in src/components/sidebar.py.", "src/components/sidebar.py"),
        ("Verify all child components are defined in src/views/index.py.", "src/views/index.py"),
    ]

    for query, file_path in cases:
        code = f"""\
# Check component render tree in {file_path}
result = check_render_tree("{file_path}")

if result.valid:
    print(f"✓ Render tree is valid (domain: {{result.domain}})")
else:
    print(f"✗ Render tree has issues ({{len(result.issues)}} issues):")
    for issue in result.issues:
        print(f"  [{{issue.severity}}] {{issue.message}}")
        if issue.suggestion:
            print(f"    Suggestion: {{issue.suggestion}}")
if result.parse_error:
    print(f"Parse error: {{result.parse_error}}")
"""
        examples.append(make_example(query, code))

    return examples


def generate_validate_escape_context() -> list[dict]:
    """Generate validate_escape_context examples (13 examples)."""
    examples = []

    cases = [
        ("Check src/views/home.py for XSS risks — verify no f-strings in html().", "src/views/home.py"),
        ("Validate that src/views/profile.py uses t-strings (not f-strings) in html() calls.", "src/views/profile.py"),
        ("Check src/views/dashboard.py for improper string interpolation in html().", "src/views/dashboard.py"),
        ("Verify escape context in src/views/search.py — should use t\"...\" not f\"...\".", "src/views/search.py"),
        ("Check src/components/card.py for f-string usage inside html() calls.", "src/components/card.py"),
        ("Validate that src/views/admin.py doesn't use f-strings in html() — XSS risk.", "src/views/admin.py"),
        ("Check escape context for src/views/reports.py.", "src/views/reports.py"),
        ("Verify src/components/form.py uses t-strings correctly in html().", "src/components/form.py"),
        ("Check src/views/settings.py — are t-strings used instead of f-strings in html()?", "src/views/settings.py"),
        ("Validate escape context in src/views/layout.py.", "src/views/layout.py"),
        ("Check src/components/modal.py for potential XSS via f-string in html().", "src/components/modal.py"),
        ("Verify proper t-string usage in src/views/header.py html() calls.", "src/views/header.py"),
        ("Check src/components/table.py for correct string interpolation in html().", "src/components/table.py"),
    ]

    for query, file_path in cases:
        code = f"""\
# Check escape context (t-string vs f-string in html()) in {file_path}
result = validate_escape_context("{file_path}")

if result.valid:
    print(f"✓ Escape context is correct — no XSS risks found (domain: {{result.domain}})")
else:
    print(f"✗ Escape context violations found ({{len(result.issues)}} issues):")
    for issue in result.issues:
        print(f"  [{{issue.severity}}] {{issue.message}}")
        if issue.suggestion:
            print(f"    Suggestion: {{issue.suggestion}}")
if result.parse_error:
    print(f"Parse error: {{result.parse_error}}")
"""
        examples.append(make_example(query, code))

    return examples


# ---------------------------------------------------------------------------
# svcs Domain Validators
# ---------------------------------------------------------------------------

def generate_validate_service_registration() -> list[dict]:
    """Generate validate_service_registration examples (13 examples)."""
    examples = []

    cases = [
        ("Check if UserService in src/services/user_service.py is properly registered.", "src/services/user_service.py"),
        ("Validate service registration in src/services/report_service.py.", "src/services/report_service.py"),
        ("Check src/services/email_service.py — does it have @injectable, @dataclass, and Inject[] fields?", "src/services/email_service.py"),
        ("Verify service patterns in src/services/auth_service.py.", "src/services/auth_service.py"),
        ("Is src/services/cache_service.py properly registered as a svcs service?", "src/services/cache_service.py"),
        ("Check registration patterns in src/services/database_service.py.", "src/services/database_service.py"),
        ("Validate src/services/notification_service.py service registration.", "src/services/notification_service.py"),
        ("Check if src/services/payment_service.py follows @injectable + @dataclass conventions.", "src/services/payment_service.py"),
        ("Verify service registration for src/services/analytics_service.py.", "src/services/analytics_service.py"),
        ("Check src/services/search_service.py — does it have proper Inject[] field types?", "src/services/search_service.py"),
        ("Validate service patterns in src/services/logging_service.py.", "src/services/logging_service.py"),
        ("Check src/services/session_service.py for correct svcs registration.", "src/services/session_service.py"),
        ("Verify that src/services/config_service.py is a properly structured svcs service.", "src/services/config_service.py"),
    ]

    for query, file_path in cases:
        code = f"""\
# Validate service registration in {file_path}
result = validate_service_registration("{file_path}")

if result.valid:
    print(f"✓ Service registration is valid (domain: {{result.domain}})")
else:
    print(f"✗ Service registration issues ({{len(result.issues)}} issues):")
    for issue in result.issues:
        print(f"  [{{issue.severity}}] {{issue.message}}")
        if issue.suggestion:
            print(f"    Suggestion: {{issue.suggestion}}")
if result.parse_error:
    print(f"Parse error: {{result.parse_error}}")
"""
        examples.append(make_example(query, code))

    return examples


def generate_check_dependency_graph() -> list[dict]:
    """Generate check_dependency_graph examples (13 examples)."""
    examples = []

    cases = [
        ("Check for dependency graph violations in src/services/report_service.py.", "src/services/report_service.py"),
        ("Does src/services/user_service.py import anything from the views layer?", "src/services/user_service.py"),
        ("Check layer violations in src/services/analytics_service.py.", "src/services/analytics_service.py"),
        ("Verify src/services/email_service.py doesn't violate the service→component rule.", "src/services/email_service.py"),
        ("Check dependency graph for src/services/payment_service.py.", "src/services/payment_service.py"),
        ("Does src/services/auth_service.py have any illegal component imports?", "src/services/auth_service.py"),
        ("Check for layer violations in src/services/search_service.py.", "src/services/search_service.py"),
        ("Verify src/services/cache_service.py imports only from allowed layers.", "src/services/cache_service.py"),
        ("Check dependency graph in src/services/notification_service.py.", "src/services/notification_service.py"),
        ("Does src/services/logging_service.py respect layer boundaries?", "src/services/logging_service.py"),
        ("Check for illegal imports in src/services/database_service.py.", "src/services/database_service.py"),
        ("Verify layer compliance for src/services/session_service.py.", "src/services/session_service.py"),
        ("Check if src/services/config_service.py has any component-layer imports.", "src/services/config_service.py"),
    ]

    for query, file_path in cases:
        code = f"""\
# Check dependency graph violations in {file_path}
result = check_dependency_graph("{file_path}")

if result.valid:
    print(f"✓ No dependency graph violations found (domain: {{result.domain}})")
else:
    print(f"✗ Dependency graph violations ({{len(result.issues)}} issues):")
    for issue in result.issues:
        print(f"  [{{issue.severity}}] {{issue.message}}")
        if issue.suggestion:
            print(f"    Suggestion: {{issue.suggestion}}")
if result.parse_error:
    print(f"Parse error: {{result.parse_error}}")
"""
        examples.append(make_example(query, code))

    return examples


def generate_validate_injection_site() -> list[dict]:
    """Generate validate_injection_site examples (13 examples)."""
    examples = []

    cases = [
        ("Check if all Inject[] types in src/services/user_service.py are imported.", "src/services/user_service.py"),
        ("Validate injection sites in src/services/report_service.py.", "src/services/report_service.py"),
        ("Are all Inject[] type annotations in src/services/email_service.py properly imported?", "src/services/email_service.py"),
        ("Check injection sites for src/services/auth_service.py.", "src/services/auth_service.py"),
        ("Verify Inject[] type imports in src/services/payment_service.py.", "src/services/payment_service.py"),
        ("Check if Inject[] field types are imported in src/services/analytics_service.py.", "src/services/analytics_service.py"),
        ("Validate injection sites in src/services/cache_service.py.", "src/services/cache_service.py"),
        ("Are all injected service types imported in src/services/notification_service.py?", "src/services/notification_service.py"),
        ("Check Inject[] type imports in src/services/search_service.py.", "src/services/search_service.py"),
        ("Validate injection site imports in src/services/database_service.py.", "src/services/database_service.py"),
        ("Check if src/services/logging_service.py has all Inject[] types imported.", "src/services/logging_service.py"),
        ("Verify injection site type imports in src/services/session_service.py.", "src/services/session_service.py"),
        ("Check Inject[] imports in src/services/config_service.py.", "src/services/config_service.py"),
    ]

    for query, file_path in cases:
        code = f"""\
# Validate injection sites (Inject[] type imports) in {file_path}
result = validate_injection_site("{file_path}")

if result.valid:
    print(f"✓ All injection sites are valid (domain: {{result.domain}})")
else:
    print(f"✗ Injection site issues ({{len(result.issues)}} issues):")
    for issue in result.issues:
        print(f"  [{{issue.severity}}] {{issue.message}}")
        if issue.suggestion:
            print(f"    Suggestion: {{issue.suggestion}}")
if result.parse_error:
    print(f"Parse error: {{result.parse_error}}")
"""
        examples.append(make_example(query, code))

    return examples


# ---------------------------------------------------------------------------
# tdom-svcs Domain Validators
# ---------------------------------------------------------------------------

def generate_validate_middleware_chain() -> list[dict]:
    """Generate validate_middleware_chain examples (13 examples)."""
    examples = []

    cases = [
        ("Validate the middleware in src/middleware/auth.py.", "src/middleware/auth.py"),
        ("Check src/middleware/logging.py — does it have correct @middleware decorator and __call__ signature?", "src/middleware/logging.py"),
        ("Validate middleware patterns in src/middleware/cors.py.", "src/middleware/cors.py"),
        ("Check src/middleware/rate_limit.py for proper middleware structure.", "src/middleware/rate_limit.py"),
        ("Is src/middleware/cache.py properly structured as middleware?", "src/middleware/cache.py"),
        ("Validate the middleware chain in src/middleware/session.py.", "src/middleware/session.py"),
        ("Check src/middleware/compression.py for correct @middleware usage.", "src/middleware/compression.py"),
        ("Verify middleware structure in src/middleware/error_handler.py.", "src/middleware/error_handler.py"),
        ("Check src/middleware/timeout.py — does it have the right __call__ signature?", "src/middleware/timeout.py"),
        ("Validate src/middleware/security.py middleware patterns.", "src/middleware/security.py"),
        ("Check if src/middleware/request_id.py follows @middleware conventions.", "src/middleware/request_id.py"),
        ("Verify src/middleware/tracing.py has correct middleware structure.", "src/middleware/tracing.py"),
        ("Validate middleware chain for src/middleware/metrics.py.", "src/middleware/metrics.py"),
    ]

    for query, file_path in cases:
        code = f"""\
# Validate middleware chain in {file_path}
result = validate_middleware_chain("{file_path}")

if result.valid:
    print(f"✓ Middleware is valid (domain: {{result.domain}})")
else:
    print(f"✗ Middleware validation failed ({{len(result.issues)}} issues):")
    for issue in result.issues:
        print(f"  [{{issue.severity}}] {{issue.message}}")
        if issue.suggestion:
            print(f"    Suggestion: {{issue.suggestion}}")
if result.parse_error:
    print(f"Parse error: {{result.parse_error}}")
"""
        examples.append(make_example(query, code))

    return examples


def generate_check_di_template_binding() -> list[dict]:
    """Generate check_di_template_binding examples (13 examples)."""
    examples = []

    cases = [
        ("Check DI template binding in src/views/home.py.", "src/views/home.py"),
        ("Verify that html() calls in src/views/profile.py pass context= correctly for DI.", "src/views/profile.py"),
        ("Check DI context binding in src/views/dashboard.py.", "src/views/dashboard.py"),
        ("Validate that src/views/admin.py passes context to html() for injectable components.", "src/views/admin.py"),
        ("Check DI template binding for src/views/settings.py.", "src/views/settings.py"),
        ("Verify context= parameter in html() calls in src/views/reports.py.", "src/views/reports.py"),
        ("Check DI binding in src/components/card.py.", "src/components/card.py"),
        ("Validate that src/components/form.py passes context correctly in html().", "src/components/form.py"),
        ("Check DI template binding in src/views/search.py.", "src/views/search.py"),
        ("Verify html() context binding in src/views/layout.py.", "src/views/layout.py"),
        ("Check if src/components/modal.py passes context= in all html() calls.", "src/components/modal.py"),
        ("Validate DI template binding in src/views/index.py.", "src/views/index.py"),
        ("Check context binding in src/components/table.py html() calls.", "src/components/table.py"),
    ]

    for query, file_path in cases:
        code = f"""\
# Check DI template binding (context= in html() calls) in {file_path}
result = check_di_template_binding("{file_path}")

if result.valid:
    print(f"✓ DI template binding is correct (domain: {{result.domain}})")
else:
    print(f"✗ DI template binding issues ({{len(result.issues)}} issues):")
    for issue in result.issues:
        print(f"  [{{issue.severity}}] {{issue.message}}")
        if issue.suggestion:
            print(f"    Suggestion: {{issue.suggestion}}")
if result.parse_error:
    print(f"Parse error: {{result.parse_error}}")
"""
        examples.append(make_example(query, code))

    return examples


def generate_validate_route_pattern() -> list[dict]:
    """Generate validate_route_pattern examples (13 examples)."""
    examples = []

    cases = [
        ("Validate the route patterns in src/routes/api.py.", "src/routes/api.py"),
        ("Check route path syntax in src/routes/auth.py.", "src/routes/auth.py"),
        ("Validate route patterns in src/routes/admin.py.", "src/routes/admin.py"),
        ("Check if all route paths in src/routes/user.py are valid.", "src/routes/user.py"),
        ("Validate route syntax in src/routes/reports.py.", "src/routes/reports.py"),
        ("Check route patterns in src/routes/dashboard.py.", "src/routes/dashboard.py"),
        ("Verify route path syntax in src/routes/settings.py.", "src/routes/settings.py"),
        ("Validate route patterns for src/routes/search.py.", "src/routes/search.py"),
        ("Check all route paths in src/routes/profile.py.", "src/routes/profile.py"),
        ("Validate route syntax in src/routes/home.py.", "src/routes/home.py"),
        ("Check route patterns in src/routes/notifications.py.", "src/routes/notifications.py"),
        ("Verify route path syntax in src/routes/payments.py.", "src/routes/payments.py"),
        ("Validate all route patterns in src/routes/analytics.py.", "src/routes/analytics.py"),
    ]

    for query, file_path in cases:
        code = f"""\
# Validate route patterns in {file_path}
result = validate_route_pattern("{file_path}")

if result.valid:
    print(f"✓ All route patterns are valid (domain: {{result.domain}})")
else:
    print(f"✗ Route pattern violations ({{len(result.issues)}} issues):")
    for issue in result.issues:
        print(f"  [{{issue.severity}}] {{issue.message}}")
        if issue.suggestion:
            print(f"    Suggestion: {{issue.suggestion}}")
if result.parse_error:
    print(f"Parse error: {{result.parse_error}}")
"""
        examples.append(make_example(query, code))

    return examples


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Generate all Phase 32 domain tool training examples."""
    random.seed(3200)
    print("Generating Phase 32 domain tool training examples...")

    generators = [
        ("cst_find_pattern", generate_cst_find_pattern),
        ("cst_rename", generate_cst_rename),
        ("cst_add_import", generate_cst_add_import),
        ("validate_component", generate_validate_component),
        ("check_render_tree", generate_check_render_tree),
        ("validate_escape_context", generate_validate_escape_context),
        ("validate_service_registration", generate_validate_service_registration),
        ("check_dependency_graph", generate_check_dependency_graph),
        ("validate_injection_site", generate_validate_injection_site),
        ("validate_middleware_chain", generate_validate_middleware_chain),
        ("check_di_template_binding", generate_check_di_template_binding),
        ("validate_route_pattern", generate_validate_route_pattern),
    ]

    all_examples = []
    counts = {}

    for tool_name, generator_fn in generators:
        examples = generator_fn()
        counts[tool_name] = len(examples)
        all_examples.extend(examples)

    # Shuffle all examples
    random.shuffle(all_examples)

    print(f"\nGenerated {len(all_examples)} examples:")
    for tool_name, count in counts.items():
        print(f"  {tool_name}: {count}")

    # Save output
    output_dir = Path("data/phase32_domain_tools")
    output_dir.mkdir(exist_ok=True, parents=True)

    output_file = output_dir / "domain_tool_examples.jsonl"
    with open(output_file, "w") as f:
        for example in all_examples:
            f.write(json.dumps(example) + "\n")

    print(f"\nSaved {len(all_examples)} examples to {output_file}")

    # Verify format
    loaded = []
    with open(output_file) as f:
        for line in f:
            loaded.append(json.loads(line))

    assert len(loaded) == len(all_examples), "Count mismatch after write"
    assert all("messages" in ex for ex in loaded), "All examples must have messages key"
    assert all(len(ex["messages"]) == 3 for ex in loaded), "All examples must have 3 messages"
    print("✓ Format verified: all examples have {'messages': [...]} with 3 turns")


if __name__ == "__main__":
    main()
