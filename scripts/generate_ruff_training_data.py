"""Generate training examples for ruff_check() typed tool.

Creates 50 examples across 4 categories:
1. Simple lint checks (15)
2. Fix violations (15)
3. Ruff + typecheck combined (10)
4. Direct answers about ruff concepts (10)
"""

import json
from pathlib import Path


def generate_simple_lint_checks():
    """Generate examples of simple ruff_check calls."""
    examples = []

    queries = [
        "Run ruff on src/",
        "Check for linting violations in src/punie/",
        "Lint src/punie/agent/",
        "Check code quality with ruff",
        "Run ruff check on the entire project",
        "Are there any ruff violations in src/?",
        "Check if src/punie/agent/toolset.py has lint issues",
        "Run ruff on tests/",
        "Lint all Python files in src/",
        "Check for unused imports",
        "Find line length violations",
        "Check for missing docstrings",
        "Run ruff on src/punie/acp/",
        "Lint src/punie/local/",
        "Check for formatting issues with ruff",
    ]

    for query in queries:
        code = f"""result = ruff_check("src/")
if result.success:
    print("✓ No violations found")
else:
    print(f"Found {{result.violation_count}} violations")
    print(f"{{result.fixable_count}} are fixable")"""

        examples.append({
            "messages": [
                {"role": "user", "content": query},
                {"role": "assistant", "content": f"<tool_call>\n{code}\n</tool_call>"}
            ]
        })

    return examples


def generate_fix_violations():
    """Generate examples of fixing ruff violations."""
    examples = []

    workflows = [
        ("Find and fix unused imports", "F401", "unused imports"),
        ("Fix line length violations", "E501", "line length"),
        ("Fix missing docstrings", "D100", "missing docstrings"),
        ("Clean up import order", "I001", "import order"),
        ("Fix trailing whitespace", "W291", "trailing whitespace"),
        ("Remove unused variables", "F841", "unused variables"),
        ("Fix indentation issues", "E111", "indentation"),
        ("Fix blank lines", "E302", "blank lines"),
        ("Fix missing type annotations", "ANN001", "missing annotations"),
        ("Clean up commented code", "ERA001", "commented code"),
        ("Fix string quotes", "Q000", "string quotes"),
        ("Fix comparison to None", "E711", "None comparison"),
        ("Fix comparison to True/False", "E712", "boolean comparison"),
        ("Remove star imports", "F403", "star imports"),
        ("Fix mutable default arguments", "B006", "mutable defaults"),
    ]

    for query, code, desc in workflows:
        violation_code = f"""result = ruff_check("src/")
if not result.success:
    fixable = [v for v in result.violations if v.fixable and v.code == "{code}"]
    print(f"Found {{len(fixable)}} fixable {desc} issues")
    if fixable:
        print("Run 'ruff check --fix' to auto-fix these")"""

        examples.append({
            "messages": [
                {"role": "user", "content": query},
                {"role": "assistant", "content": f"<tool_call>\n{violation_code}\n</tool_call>"}
            ]
        })

    return examples


def generate_combined_checks():
    """Generate examples combining ruff with typecheck."""
    examples = []

    queries = [
        "Check both lint and types in src/",
        "Full quality check: ruff and typecheck",
        "Run linting and type checking",
        "Check code quality (lint + types)",
        "Verify no linting or type errors",
        "Quality gate: check lint and types pass",
        "Run both ruff and ty on src/",
        "Pre-commit check: lint and types",
        "Check if code is ready to commit",
        "Run full static analysis",
    ]

    for query in queries:
        code = """ruff = ruff_check("src/")
ty = typecheck("src/")

print(f"Lint: {ruff.violation_count} violations")
print(f"Type: {ty.error_count} errors")

if ruff.success and ty.success:
    print("✓ All checks pass")
else:
    print("✗ Issues found")"""

        examples.append({
            "messages": [
                {"role": "user", "content": query},
                {"role": "assistant", "content": f"<tool_call>\n{code}\n</tool_call>"}
            ]
        })

    return examples


def generate_direct_answers():
    """Generate direct answer examples about ruff concepts."""
    examples = []

    qa_pairs = [
        (
            "What is the F401 ruff code?",
            "F401 is the ruff rule code for unused imports. It detects when you've imported a module, class, or function but never use it in your code. This violation is auto-fixable with `ruff check --fix`."
        ),
        (
            "What does ruff do?",
            "Ruff is an extremely fast Python linter and code formatter written in Rust. It checks for code quality issues, style violations, and potential bugs. It can auto-fix many violations and is a drop-in replacement for tools like Flake8, pylint, and Black."
        ),
        (
            "How do I fix all ruff violations?",
            "Run `ruff check --fix` to automatically fix all auto-fixable violations. Not all violations can be auto-fixed - some require manual intervention. You can see which violations are fixable in the ruff_check() result by checking the `fixable` field."
        ),
        (
            "What's the difference between ruff and pylint?",
            "Ruff is much faster (10-100x) than pylint because it's written in Rust. It covers most of pylint's checks plus many from other tools (Flake8, isort, etc.). Ruff focuses on speed and auto-fixing, while pylint has more configurable checks but is slower."
        ),
        (
            "What are E501 violations?",
            "E501 violations indicate lines that are too long (exceed the configured line length limit, typically 88 or 120 characters). These can usually be fixed by breaking long lines, using parentheses for implicit line continuation, or refactoring complex expressions."
        ),
        (
            "Can ruff format code?",
            "Yes, ruff has a built-in formatter (`ruff format`) that's compatible with Black. However, ruff_check() focuses on linting - it finds violations but doesn't automatically reformat code. Use `ruff check --fix` for fixable violations or `ruff format` for full formatting."
        ),
        (
            "What does 'fixable' mean in ruff results?",
            "A violation is 'fixable' if ruff can automatically correct it without human intervention. The ruff_check() function returns a `fixable` boolean field for each violation. Fixable violations are marked with [*] in ruff's output."
        ),
        (
            "What are the most common ruff violations?",
            "The most common violations are: F401 (unused imports), E501 (line too long), E402 (imports not at top), F841 (unused variable), E302 (missing blank lines), and I001 (import order). Many of these are auto-fixable."
        ),
        (
            "Should I run ruff before committing?",
            "Yes! Running ruff before committing helps catch issues early. Many projects use pre-commit hooks to automatically run ruff. You can check both lint and types with: `ruff_check('src/')` and `typecheck('src/')`."
        ),
        (
            "How do I ignore specific ruff rules?",
            "Configure ignored rules in `pyproject.toml` under `[tool.ruff]` with `ignore = [\"E501\", \"F401\"]` or use inline comments like `# noqa: E501`. However, it's better to fix violations when possible rather than ignoring them."
        ),
    ]

    for question, answer in qa_pairs:
        examples.append({
            "messages": [
                {"role": "user", "content": question},
                {"role": "assistant", "content": answer}
            ]
        })

    return examples


def main():
    """Generate all ruff training examples."""
    output_dir = Path("data/ruff_training")
    output_dir.mkdir(parents=True, exist_ok=True)

    examples = []
    examples.extend(generate_simple_lint_checks())  # 15
    examples.extend(generate_fix_violations())  # 15
    examples.extend(generate_combined_checks())  # 10
    examples.extend(generate_direct_answers())  # 10

    # Write to JSONL
    output_file = output_dir / "ruff_examples.jsonl"
    with output_file.open("w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")

    print(f"✓ Generated {len(examples)} ruff training examples")
    print(f"  Simple lint checks: 15")
    print(f"  Fix violations: 15")
    print(f"  Combined with typecheck: 10")
    print(f"  Direct answers: 10")
    print(f"  Output: {output_file}")


if __name__ == "__main__":
    main()
