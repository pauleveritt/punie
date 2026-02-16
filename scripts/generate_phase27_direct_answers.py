"""Generate Phase 27 direct-answer examples (no tool calls).

Creates 80 examples:
- 20 git concept questions (branching strategy, merge vs rebase)
- 20 LSP concept questions (what is hover, what are document symbols)
- 20 Python best practices (typing, testing, linting)
- 20 tool selection reasoning (when to use which tool)

All examples follow Phase 26 structural norms:
- 100% system messages
- Simple Q&A format (no tool calls)
- Direct informational responses
"""

import json
import random
from pathlib import Path

# Set seed for reproducibility
random.seed(45)


def create_git_concept_examples() -> list[dict]:
    """Create 20 git concept questions."""
    examples = []

    qa_pairs = [
        ("What's the difference between git merge and git rebase?", "Git merge combines two branches by creating a new merge commit that preserves the history of both branches. Git rebase moves or replays commits from one branch onto another, creating a linear history without merge commits. Merge is safer for shared branches, while rebase is useful for cleaning up local history before pushing."),
        ("When should I use git stash?", "Use git stash when you need to temporarily save uncommitted changes to work on something else. It's helpful when you want to switch branches but aren't ready to commit, or when you need to pull changes but have local modifications. Use `git stash pop` to restore the changes later."),
        ("What does git cherry-pick do?", "Git cherry-pick applies the changes from a specific commit onto your current branch. It's useful when you want to copy a single commit from one branch to another without merging the entire branch. The commit gets a new hash on the target branch."),
        ("What's a detached HEAD state?", "A detached HEAD occurs when HEAD points directly to a commit instead of a branch. This happens when you checkout a specific commit hash or tag. Changes made in this state won't be on any branch unless you create one. Use `git checkout -b <branch-name>` to save your work."),
        ("What's the difference between git pull and git fetch?", "Git fetch downloads commits, files, and refs from a remote repository without merging them into your local branch. Git pull does a fetch followed by an automatic merge. Use fetch when you want to review changes before integrating them, and pull for quick updates."),
        ("When should I use git revert vs git reset?", "Git revert creates a new commit that undoes changes from a previous commit, preserving history. Git reset moves the branch pointer backward, potentially removing commits from history. Use revert for shared branches (safe), reset for local-only changes (destructive)."),
        ("What's a fast-forward merge?", "A fast-forward merge occurs when the current branch has no new commits since it diverged from the target branch. Git simply moves the branch pointer forward without creating a merge commit. Use `git merge --no-ff` to force a merge commit even in fast-forward situations."),
        ("What's the difference between git reset --soft, --mixed, and --hard?", "`--soft` moves HEAD but keeps changes staged. `--mixed` (default) moves HEAD and unstages changes but keeps them in working directory. `--hard` moves HEAD and discards all changes completely. Use soft for recommitting, mixed for unstaging, hard with caution."),
        ("When should I use git squash?", "Git squash combines multiple commits into one, creating a cleaner history. Use it during interactive rebase (`git rebase -i`) to consolidate related commits before merging to main. It's helpful for removing 'fix typo' or 'WIP' commits from feature branches."),
        ("What's a git reflog?", "Git reflog records all changes to HEAD, including commits, checkouts, resets, and rebases. It's a safety net for recovering 'lost' commits after destructive operations. Use `git reflog` to see the history and `git reset --hard <commit>` to recover work."),
    ]

    for question, answer in qa_pairs:
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
        examples.append({"messages": messages})

    return examples[:20]


def create_lsp_concept_examples() -> list[dict]:
    """Create 20 LSP concept questions."""
    examples = []

    qa_pairs = [
        ("What is LSP hover?", "LSP hover (textDocument/hover) provides information about a symbol when you hover over it in the editor. It typically shows the symbol's type signature, documentation, and related information. In Python, this includes function signatures, class definitions, and docstrings."),
        ("What are document symbols?", "Document symbols (textDocument/documentSymbol) provide a hierarchical view of all symbols in a file, including classes, functions, methods, variables, and constants. They show the symbol's name, kind (class/function/variable), line range, and children (nested symbols). Useful for file navigation and outline views."),
        ("When should I use workspace symbols vs document symbols?", "Use document symbols to explore the structure of a single file (classes, functions, methods). Use workspace symbols to search for a symbol across all files in the project. Document symbols are hierarchical, workspace symbols are flat with file locations."),
        ("What's the difference between goto definition and find references?", "Goto definition finds where a symbol is declared/defined. Find references finds all places where a symbol is used. Use goto_definition to understand what something is, find_references to see everywhere it's used or who depends on it."),
        ("What information does hover provide?", "Hover provides type signatures, parameter information, return types, docstrings, and overload information. For functions, it shows the signature with parameter types and names. For classes, it shows the class definition and documentation. For variables, it shows the inferred or annotated type."),
        ("What are symbol kinds in LSP?", "Symbol kinds identify the type of a symbol: File(1), Module(2), Class(5), Method(6), Property(7), Field(8), Function(12), Variable(13), Constant(14), etc. Each kind has a numeric identifier used by document and workspace symbol operations."),
        ("When should I use LSP vs grep for finding code?", "Use LSP (goto_definition, find_references, workspace_symbols) when you need semantic understanding - finding actual definitions and usages. Use grep when you need text pattern matching, searching in comments, or finding strings. LSP understands scope and context, grep doesn't."),
        ("What's the difference between hover and signature help?", "Hover shows information about a symbol under the cursor (type, docs). Signature help shows parameter information when calling a function, including which parameter you're currently typing. Hover is contextual information, signature help is real-time typing assistance."),
        ("Can LSP find usages in other files?", "Yes, find_references searches across the entire workspace to find all usages of a symbol. It returns a list of locations (file, line, column) where the symbol is referenced. This works across file boundaries and respects imports and scoping rules."),
        ("What's the performance difference between LSP and text search?", "LSP queries are typically faster because they use prebuilt semantic indexes. Text search (grep/rg) must scan file contents. However, LSP requires an LSP server to be running and maintaining indexes. LSP is accurate (semantic) but has startup cost, text search is fast but literal."),
    ]

    for question, answer in qa_pairs:
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
        examples.append({"messages": messages})

    return examples[:20]


def create_python_best_practices_examples() -> list[dict]:
    """Create 20 Python best practices questions."""
    examples = []

    qa_pairs = [
        ("When should I use type hints in Python?", "Use type hints for function signatures, class attributes, and complex variables. They improve code readability, enable static type checking with tools like ty or mypy, and provide better IDE support. Always use them in public APIs, library code, and large codebases. Optional for small scripts."),
        ("What's the difference between pytest and unittest?", "Pytest uses simple functions and assert statements, while unittest requires classes and special assertion methods. Pytest has better fixture support, parametrization, and plugin ecosystem. Pytest is more Pythonic and requires less boilerplate. Use pytest for new projects, unittest for stdlib-only requirements."),
        ("When should I run a linter vs a formatter?", "Run a linter (ruff check) to find bugs, style violations, and code smells - it reports issues but doesn't change code. Run a formatter (ruff format) to automatically fix style - it changes code. Typical workflow: format first, then lint to catch remaining issues."),
        ("What's the benefit of type checking?", "Type checking catches type-related bugs before runtime, improves code documentation, enables better IDE autocomplete, and makes refactoring safer. It prevents common errors like passing wrong argument types, accessing non-existent attributes, and returning incorrect values."),
        ("When should I use assert vs raise Exception?", "Use assert for internal invariants and debugging (can be disabled with -O flag). Use raise Exception for actual error handling and validation. Assertions are for 'this should never happen' conditions, exceptions are for expected error cases that callers should handle."),
        ("What's the difference between staticmethod and classmethod?", "staticmethod is a regular function inside a class, doesn't receive self or cls. classmethod receives the class (cls) as first argument, useful for alternative constructors. Use staticmethod for utility functions, classmethod when you need class reference or inheritance support."),
        ("When should I use dataclasses?", "Use dataclasses for simple data containers that primarily hold data and have minimal behavior. They automatically generate __init__, __repr__, __eq__, and more. Great for configuration objects, API responses, and DTOs. Use regular classes when you need complex initialization or extensive methods."),
        ("What's the benefit of f-strings over format()?", "F-strings (f'Hello {name}') are more readable, faster, and support expressions directly. The format() method ('{}'.format(name)) is older and more verbose. F-strings were added in Python 3.6 and are now the recommended approach for string formatting."),
        ("When should I use list comprehension vs map/filter?", "Use list comprehensions for readability and when you need multiple operations. They're more Pythonic and easier to understand. Use map/filter when passing existing functions or when working with other functional tools. List comprehensions are generally preferred in Python."),
        ("What's the purpose of __all__ in Python modules?", "__all__ defines what's exported when someone does `from module import *`. It controls the public API and hides internal implementation details. Use it in library code to explicitly declare the public interface. Without it, all names not starting with _ are exported."),
    ]

    for question, answer in qa_pairs:
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
        examples.append({"messages": messages})

    return examples[:20]


def create_tool_selection_examples() -> list[dict]:
    """Create 20 tool selection reasoning questions."""
    examples = []

    qa_pairs = [
        ("When should I use git_status vs git_diff?", "Use git_status to see which files have changed (modified, added, deleted, untracked) and their staging status. Use git_diff to see the actual line-by-line changes in those files. Status answers 'what changed', diff answers 'how did it change'. Typically run status first, then diff for details."),
        ("Should I use workspace_symbols or grep to find a function?", "Use workspace_symbols when you know the symbol name and want semantic matches (actual definitions and declarations). Use grep when you need pattern matching, fuzzy search, or want to search in comments and strings. workspace_symbols is more accurate but requires LSP; grep is more flexible."),
        ("When should I use hover vs read_file?", "Use hover to get type information, signatures, and documentation for a specific symbol at a location. Use read_file to see the entire file contents or multiple symbols. Hover is targeted and semantic, read_file is comprehensive but requires manual parsing."),
        ("Should I use pytest_run or run_command pytest?", "Use pytest_run for structured results (passed/failed counts, test details, duration). Use run_command when you need custom pytest flags or want raw output. pytest_run returns a TestResult object with fields you can access; run_command returns raw text."),
        ("When should I use document_symbols vs reading a file?", "Use document_symbols to get a structured overview of all classes, functions, and methods in a file with their locations and hierarchy. Use read_file when you need to see the actual code implementation. document_symbols is faster for navigation, read_file is better for understanding logic."),
        ("Should I use ruff_check or run_command ruff?", "Use ruff_check for structured violation data (file, line, code, message, fixable). Use run_command when you need custom ruff flags or configuration. ruff_check returns a RuffResult object with filterable violations; run_command returns formatted text."),
        ("When should I use find_references vs grep?", "Use find_references for semantic code navigation - finding actual usages of a symbol. Use grep for text pattern matching, finding strings, or searching comments. find_references understands scope and imports; grep is literal text search."),
        ("Should I use typecheck or run_command ty?", "Use typecheck for structured type error data (file, line, column, error code, message). Use run_command when you need custom ty flags. typecheck returns a TypeCheckResult with iterable errors; run_command returns formatted output."),
        ("When should I combine multiple tools vs use one?", "Combine tools when you need multi-faceted analysis (e.g., git_diff to see changes, then read_file to understand context). Use single tools when one provides all needed information. Combining tools is powerful but slower; single tools are faster but limited."),
        ("Should I use git_log or run_command git log?", "Use git_log for structured commit data (hash, message, author, date). Use run_command for custom git log formats (--graph, --stat, etc.). git_log returns a GitLogResult with iterable commits; run_command provides formatting flexibility."),
    ]

    for question, answer in qa_pairs:
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ]
        examples.append({"messages": messages})

    return examples[:20]


def main():
    """Generate all Phase 27 direct-answer examples."""
    output_dir = Path("data/phase27_direct_answers")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_examples = []

    print("Generating git concept examples...")
    all_examples.extend(create_git_concept_examples())

    print("Generating LSP concept examples...")
    all_examples.extend(create_lsp_concept_examples())

    print("Generating Python best practices examples...")
    all_examples.extend(create_python_best_practices_examples())

    print("Generating tool selection examples...")
    all_examples.extend(create_tool_selection_examples())

    # Shuffle examples
    random.shuffle(all_examples)

    # Save as JSONL
    output_file = output_dir / "phase27_direct_answers.jsonl"
    with open(output_file, "w") as f:
        for example in all_examples:
            f.write(json.dumps(example) + "\n")

    print(f"\nGenerated {len(all_examples)} direct-answer examples")
    print(f"Saved to: {output_file}")


if __name__ == "__main__":
    main()
