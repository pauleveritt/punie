"""Generate multi-turn training examples with tool responses for Phase 27 new tools.

This addresses the critical gap identified in the audit: current training data has
ZERO examples showing what new tools return. The model has never seen actual output
from hover, document_symbols, workspace_symbols, git_status, git_diff, or git_log.

Creates 60 examples (10 per tool) with realistic tool responses:
- hover: HoverResult with content and language fields
- document_symbols: DocumentSymbolsResult with nested symbols
- workspace_symbols: WorkspaceSymbolsResult with multiple matches
- git_status: GitStatusResult with staged/unstaged files
- git_diff: GitDiffResult with additions/deletions
- git_log: GitLogResult with commit history

All examples follow Phase 26 structural norms:
- 100% system messages
- Multi-turn format (user → assistant tool_call → tool → assistant response)
- Code Mode format (<tool_call><function=execute_code>)
"""

import json
import random
from pathlib import Path

# Set seed for reproducibility
random.seed(44)


def create_hover_tool_response_examples() -> list[dict]:
    """Create 10 hover examples with realistic tool responses."""
    examples = []

    cases = [
        (
            "Show hover info for UserService at src/services/user.py line 15",
            "src/services/user.py",
            15,
            5,
            "UserService",
            'class UserService:\\n    "Manages user operations including authentication and profile updates."\\n    def __init__(self, db: Database): ...',
            "python",
        ),
        (
            "Get type information for authenticate method",
            "src/auth.py",
            42,
            10,
            "authenticate",
            "def authenticate(username: str, password: str) -> bool:\n    Authenticates a user with credentials.",
            "python",
        ),
        (
            "What's the return type of process_data?",
            "src/processors/data.py",
            67,
            8,
            "process_data",
            "def process_data(input: dict[str, Any]) -> list[DataRecord]:\n    Processes raw input data into structured records.",
            "python",
        ),
        (
            "Show type info for DatabaseConnection",
            "src/db/connection.py",
            12,
            7,
            "DatabaseConnection",
            "class DatabaseConnection:\\n    \"Thread-safe database connection pool.\"\\n    def connect(self, host: str, port: int = 5432) -> Connection: ...",
            "python",
        ),
        (
            "Get hover for validate_email function",
            "src/utils/validation.py",
            34,
            5,
            "validate_email",
            "def validate_email(email: str) -> bool:\n    Validates email format using RFC 5322 regex.",
            "python",
        ),
        (
            "Show TokenManager class signature",
            "src/auth/tokens.py",
            21,
            7,
            "TokenManager",
            "class TokenManager:\\n    \"JWT token manager with expiration and refresh.\"\\n    def generate(self, user_id: int, expires_in: int = 3600) -> str: ...",
            "python",
        ),
        (
            "Get type details for send_notification",
            "src/notifications.py",
            55,
            5,
            "send_notification",
            "async def send_notification(user_id: int, message: str, channel: NotificationChannel) -> None:\n    Sends notification through specified channel.",
            "python",
        ),
        (
            "Show hover for ApiClient",
            "src/api/client.py",
            18,
            7,
            "ApiClient",
            "class ApiClient:\\n    \"HTTP client with automatic retry and rate limiting.\"\\n    def request(self, method: str, endpoint: str, **kwargs) -> Response: ...",
            "python",
        ),
        (
            "Get type of config variable",
            "src/config.py",
            89,
            1,
            "config",
            "config: Config\n    Global configuration instance loaded from environment.",
            "python",
        ),
        (
            "Show hover for create_user",
            "src/models/user.py",
            28,
            5,
            "create_user",
            "def create_user(username: str, email: str, password_hash: str) -> User:\n    Creates a new user with hashed password.",
            "python",
        ),
    ]

    for query, file_path, line, col, symbol, content, language in cases:
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = hover("{file_path}", {line}, {col}, "{symbol}")\nif result.success:\n    print(f"Symbol: {{result.symbol}}")\n    print(f"Content: {{result.content}}")\n    print(f"Language: {{result.language}}")\nelse:\n    print("No hover info available")\n</parameter></function></tool_call>',
            },
            {
                "role": "tool",
                "content": f'<tool_response>HoverResult(success=True, symbol="{symbol}", content={repr(content)}, language="{language}", parse_error=None)</tool_response>',
            },
            {
                "role": "assistant",
                "content": f'The hover information shows:\n\nSymbol: {symbol}\nLanguage: {language}\n\nContent:\n```{language}\n{content}\n```',
            },
        ]
        examples.append({"messages": messages})

    return examples


def create_document_symbols_tool_response_examples() -> list[dict]:
    """Create 10 document_symbols examples with realistic tool responses."""
    examples = []

    cases = [
        (
            "What's the structure of src/services/user.py?",
            "src/services/user.py",
            [
                ("UserService", 5, 10, 50, [("__init__", 6, 12, 15), ("get_user", 6, 17, 25)]),
                ("create_user", 12, 30, 45, []),
            ],
        ),
        (
            "List all classes in src/auth.py",
            "src/auth.py",
            [
                ("AuthManager", 5, 5, 100, [("authenticate", 6, 10, 30), ("refresh_token", 6, 35, 50)]),
                ("PasswordHasher", 5, 105, 150, [("hash", 6, 110, 120), ("verify", 6, 125, 135)]),
            ],
        ),
        (
            "Show document symbols for src/models/user.py",
            "src/models/user.py",
            [
                ("User", 5, 8, 60, [("__init__", 6, 10, 18), ("to_dict", 6, 20, 28)]),
                ("UserProfile", 5, 65, 100, [("__init__", 6, 67, 75)]),
            ],
        ),
        (
            "Get file structure for src/processors/data.py",
            "src/processors/data.py",
            [
                ("DataProcessor", 5, 12, 80, [("process", 6, 15, 40), ("validate", 6, 45, 60)]),
                ("process_batch", 12, 85, 120, []),
            ],
        ),
        (
            "List symbols in src/db/connection.py",
            "src/db/connection.py",
            [
                ("DatabaseConnection", 5, 10, 150, [("connect", 6, 15, 30), ("execute", 6, 35, 55), ("close", 6, 60, 70)]),
            ],
        ),
        (
            "Show structure of src/utils/validation.py",
            "src/utils/validation.py",
            [
                ("validate_email", 12, 5, 20, []),
                ("validate_password", 12, 25, 40, []),
                ("ValidationError", 5, 45, 60, [("__init__", 6, 47, 52)]),
            ],
        ),
        (
            "Get symbols from src/auth/tokens.py",
            "src/auth/tokens.py",
            [
                ("TokenManager", 5, 8, 100, [("generate", 6, 12, 30), ("verify", 6, 35, 50), ("refresh", 6, 55, 70)]),
                ("TokenError", 5, 105, 115, []),
            ],
        ),
        (
            "List all functions in src/notifications.py",
            "src/notifications.py",
            [
                ("send_notification", 12, 5, 35, []),
                ("send_email", 12, 40, 65, []),
                ("NotificationChannel", 13, 70, 85, []),
            ],
        ),
        (
            "Show document symbols for src/api/client.py",
            "src/api/client.py",
            [
                ("ApiClient", 5, 10, 120, [("request", 6, 15, 40), ("get", 6, 45, 60), ("post", 6, 65, 80)]),
                ("ApiError", 5, 125, 145, [("__init__", 6, 127, 135)]),
            ],
        ),
        (
            "Get structure of src/config.py",
            "src/config.py",
            [
                ("Config", 5, 5, 80, [("__init__", 6, 8, 20), ("load_env", 6, 25, 40)]),
                ("config", 12, 85, 90, []),
            ],
        ),
    ]

    for query, file_path, symbols_data in cases:
        # Build symbols list for tool response
        symbols_repr = []
        total_count = 0
        for name, kind, line, end_line, children in symbols_data:
            children_repr = []
            for child_name, child_kind, child_line, child_end_line in children:
                children_repr.append(
                    f'SymbolInfo(name="{child_name}", kind={child_kind}, line={child_line}, end_line={child_end_line}, children=[])'
                )
                total_count += 1
            children_str = f"[{', '.join(children_repr)}]"
            symbols_repr.append(
                f'SymbolInfo(name="{name}", kind={kind}, line={line}, end_line={end_line}, children={children_str})'
            )
            total_count += 1

        symbols_str = f"[{', '.join(symbols_repr)}]"

        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = document_symbols("{file_path}")\nif result.success:\n    print(f"File: {{result.file_path}}")\n    print(f"Total symbols: {{result.symbol_count}}")\n    for symbol in result.symbols:\n        print(f"  {{symbol.name}} (kind {{symbol.kind}}) at line {{symbol.line}}")\n        for child in symbol.children:\n            print(f"    - {{child.name}} at line {{child.line}}")\nelse:\n    print("No symbols found")\n</parameter></function></tool_call>',
            },
            {
                "role": "tool",
                "content": f'<tool_response>DocumentSymbolsResult(success=True, file_path="{file_path}", symbols={symbols_str}, symbol_count={total_count}, parse_error=None)</tool_response>',
            },
            {
                "role": "assistant",
                "content": f'The file {file_path} contains {total_count} symbols:\n\n'
                + "\n".join(
                    f"- {name} (kind {kind}) at line {line}"
                    + (
                        "\n"
                        + "\n".join(f"  - {child_name} at line {child_line}" for child_name, _, child_line, _ in children)
                        if children
                        else ""
                    )
                    for name, kind, line, _, children in symbols_data
                ),
            },
        ]
        examples.append({"messages": messages})

    return examples


def create_workspace_symbols_tool_response_examples() -> list[dict]:
    """Create 10 workspace_symbols examples with realistic tool responses."""
    examples = []

    cases = [
        (
            "Search workspace for ApiClient symbols",
            "ApiClient",
            [
                ("ApiClient", 5, "src/api/client.py", 18, "api.client"),
                ("ApiClient", 5, "src/api/v2/client.py", 25, "api.v2.client"),
            ],
        ),
        (
            "Find all User classes in workspace",
            "User",
            [
                ("User", 5, "src/models/user.py", 10, "models.user"),
                ("UserService", 5, "src/services/user.py", 15, "services.user"),
                ("UserProfile", 5, "src/models/profile.py", 30, "models.profile"),
            ],
        ),
        (
            "Search for authenticate methods",
            "authenticate",
            [
                ("authenticate", 6, "src/auth.py", 42, "AuthManager"),
                ("authenticate_user", 12, "src/services/auth.py", 28, None),
            ],
        ),
        (
            "Find DatabaseConnection in workspace",
            "DatabaseConnection",
            [
                ("DatabaseConnection", 5, "src/db/connection.py", 12, "db.connection"),
            ],
        ),
        (
            "Search for TokenManager",
            "TokenManager",
            [
                ("TokenManager", 5, "src/auth/tokens.py", 21, "auth.tokens"),
            ],
        ),
        (
            "Find all process functions",
            "process",
            [
                ("process_data", 12, "src/processors/data.py", 67, None),
                ("process_batch", 12, "src/processors/batch.py", 45, None),
                ("process", 6, "src/processors/data.py", 15, "DataProcessor"),
            ],
        ),
        (
            "Search workspace for Config",
            "Config",
            [
                ("Config", 5, "src/config.py", 8, "config"),
                ("ConfigLoader", 5, "src/config/loader.py", 12, "config.loader"),
            ],
        ),
        (
            "Find send_notification",
            "send_notification",
            [
                ("send_notification", 12, "src/notifications.py", 55, None),
            ],
        ),
        (
            "Search for validation functions",
            "validate",
            [
                ("validate_email", 12, "src/utils/validation.py", 34, None),
                ("validate_password", 12, "src/utils/validation.py", 50, None),
                ("validate", 6, "src/processors/data.py", 45, "DataProcessor"),
            ],
        ),
        (
            "Find Error classes",
            "Error",
            [
                ("ValidationError", 5, "src/utils/validation.py", 45, "validation"),
                ("TokenError", 5, "src/auth/tokens.py", 105, "auth.tokens"),
                ("ApiError", 5, "src/api/client.py", 125, "api.client"),
            ],
        ),
    ]

    for query, search_query, symbols_data in cases:
        # Build symbols list for tool response
        symbols_repr = []
        for name, kind, file, line, container in symbols_data:
            container_str = f'"{container}"' if container else "None"
            symbols_repr.append(f'WorkspaceSymbol(name="{name}", kind={kind}, file="{file}", line={line}, container_name={container_str})')
        symbols_str = f"[{', '.join(symbols_repr)}]"

        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = workspace_symbols("{search_query}")\nif result.success:\n    print(f"Found {{result.symbol_count}} symbols matching \'{search_query}\'")\n    for symbol in result.symbols:\n        container = f" in {{symbol.container_name}}" if symbol.container_name else ""\n        print(f"  {{symbol.name}} (kind {{symbol.kind}}){{container}} at {{symbol.file}}:{{symbol.line}}")\nelse:\n    print(f"No symbols found for \'{search_query}\'")\n</parameter></function></tool_call>',
            },
            {
                "role": "tool",
                "content": f'<tool_response>WorkspaceSymbolsResult(success=True, query="{search_query}", symbols={symbols_str}, symbol_count={len(symbols_data)}, parse_error=None)</tool_response>',
            },
            {
                "role": "assistant",
                "content": f"Found {len(symbols_data)} symbols matching '{search_query}':\n\n"
                + "\n".join(
                    f"- {name} (kind {kind}){f' in {container}' if container else ''} at {file}:{line}"
                    for name, kind, file, line, container in symbols_data
                ),
            },
        ]
        examples.append({"messages": messages})

    return examples


def create_git_status_tool_response_examples() -> list[dict]:
    """Create 10 git_status examples with realistic tool responses."""
    examples = []

    cases = [
        (
            "What files have changed?",
            ".",
            False,
            4,
            [
                ("src/app.py", "modified", True),
                ("src/config.py", "modified", False),
                ("src/new.py", "added", True),
                ("tests/test_new.py", "untracked", False),
            ],
        ),
        (
            "Show git status",
            ".",
            False,
            3,
            [
                ("src/models/user.py", "modified", True),
                ("README.md", "modified", False),
                ("docs/api.md", "added", True),
            ],
        ),
        (
            "Check for uncommitted changes",
            ".",
            False,
            5,
            [
                ("src/auth.py", "modified", True),
                ("src/db/connection.py", "modified", False),
                ("src/utils/helpers.py", "deleted", False),
                ("src/api/client.py", "modified", False),
                ("tests/__init__.py", "untracked", False),
            ],
        ),
        (
            "List staged files",
            ".",
            False,
            2,
            [
                ("src/services/user.py", "modified", True),
                ("tests/test_services.py", "added", True),
            ],
        ),
        (
            "Show working tree status",
            ".",
            True,
            0,
            [],
        ),
        (
            "Check for untracked files",
            ".",
            False,
            3,
            [
                ("temp.py", "untracked", False),
                ("notes.txt", "untracked", False),
                ("src/draft.py", "untracked", False),
            ],
        ),
        (
            "What's pending commit?",
            ".",
            False,
            2,
            [
                ("src/processors/data.py", "modified", True),
                ("src/processors/batch.py", "added", True),
            ],
        ),
        (
            "Show staged vs unstaged",
            ".",
            False,
            6,
            [
                ("src/main.py", "modified", True),
                ("src/config.py", "modified", True),
                ("tests/test_main.py", "modified", False),
                ("tests/test_config.py", "added", False),
                ("requirements.txt", "modified", False),
                ("setup.py", "modified", False),
            ],
        ),
        (
            "Check working directory status",
            ".",
            False,
            4,
            [
                ("src/auth/tokens.py", "renamed", True),
                ("src/api/v2/client.py", "modified", False),
                ("migrations/001.sql", "added", True),
                ("scripts/deploy.sh", "modified", False),
            ],
        ),
        (
            "List modified files",
            ".",
            False,
            3,
            [
                ("src/models/base.py", "modified", True),
                ("src/models/user.py", "modified", True),
                ("tests/test_models.py", "modified", False),
            ],
        ),
    ]

    for query, path, clean, file_count, files_data in cases:
        # Build files list for tool response
        files_repr = [f'GitFileStatus(file="{file}", status="{status}", staged={staged})' for file, status, staged in files_data]
        files_str = f"[{', '.join(files_repr)}]"

        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = git_status("{path}")\nif result.clean:\n    print("Working tree is clean")\nelse:\n    staged = [f for f in result.files if f.staged]\n    unstaged = [f for f in result.files if not f.staged]\n    print(f"Total changes: {{result.file_count}}")\n    print(f"Staged: {{len(staged)}}")\n    print(f"Unstaged: {{len(unstaged)}}")\n    for file in result.files:\n        status_str = "staged" if file.staged else "unstaged"\n        print(f"  {{file.file}} ({{file.status}}, {{status_str}})")\n</parameter></function></tool_call>',
            },
            {
                "role": "tool",
                "content": f'<tool_response>GitStatusResult(success=True, clean={clean}, file_count={file_count}, files={files_str}, parse_error=None)</tool_response>',
            },
            {
                "role": "assistant",
                "content": (
                    "Working tree is clean"
                    if clean
                    else f"Total changes: {file_count}\nStaged: {sum(1 for _, _, s in files_data if s)}\nUnstaged: {sum(1 for _, _, s in files_data if not s)}\n\n"
                    + "\n".join(f"- {file} ({status}, {'staged' if staged else 'unstaged'})" for file, status, staged in files_data)
                ),
            },
        ]
        examples.append({"messages": messages})

    return examples


def create_git_diff_tool_response_examples() -> list[dict]:
    """Create 10 git_diff examples with realistic tool responses."""
    examples = []

    cases = [
        (
            "Show unstaged changes",
            ".",
            False,
            2,
            25,
            12,
            [("src/app.py", 15, 8), ("src/config.py", 10, 4)],
        ),
        (
            "Show staged changes",
            ".",
            True,
            1,
            8,
            3,
            [("src/models/user.py", 8, 3)],
        ),
        (
            "Get diff for working directory",
            ".",
            False,
            3,
            42,
            18,
            [("src/auth.py", 12, 5), ("src/db/connection.py", 20, 10), ("tests/test_auth.py", 10, 3)],
        ),
        (
            "Show diff statistics",
            ".",
            False,
            4,
            56,
            28,
            [
                ("src/services/user.py", 18, 10),
                ("src/api/client.py", 25, 12),
                ("tests/test_services.py", 10, 5),
                ("README.md", 3, 1),
            ],
        ),
        (
            "What changed in staged files?",
            ".",
            True,
            2,
            30,
            15,
            [("src/processors/data.py", 20, 10), ("src/processors/batch.py", 10, 5)],
        ),
        (
            "Show unstaged modifications",
            ".",
            False,
            1,
            5,
            2,
            [("src/config.py", 5, 2)],
        ),
        (
            "Get diff for uncommitted changes",
            ".",
            False,
            5,
            68,
            32,
            [
                ("src/main.py", 12, 8),
                ("src/utils/helpers.py", 15, 10),
                ("tests/test_main.py", 20, 5),
                ("tests/test_helpers.py", 18, 8),
                ("requirements.txt", 3, 1),
            ],
        ),
        (
            "Show additions and deletions",
            ".",
            True,
            3,
            45,
            20,
            [("src/auth/tokens.py", 25, 12), ("src/api/v2/client.py", 15, 6), ("migrations/001.sql", 5, 2)],
        ),
        (
            "Check staged diff",
            ".",
            True,
            2,
            28,
            14,
            [("src/models/base.py", 18, 10), ("src/models/user.py", 10, 4)],
        ),
        (
            "Show working tree diff",
            ".",
            False,
            0,
            0,
            0,
            [],
        ),
    ]

    for query, path, staged, file_count, additions, deletions, files_data in cases:
        # Build files list for tool response
        files_repr = [
            f'DiffFile(file="{file}", additions={adds}, deletions={dels}, hunks=[])' for file, adds, dels in files_data
        ]
        files_str = f"[{', '.join(files_repr)}]"

        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = git_diff("{path}", staged={staged})\nif result.file_count > 0:\n    print(f"Files changed: {{result.file_count}}")\n    print(f"Total additions: {{result.additions}}")\n    print(f"Total deletions: {{result.deletions}}")\n    for file in result.files:\n        print(f"  {{file.file}}: +{{file.additions}} -{{file.deletions}}")\nelse:\n    print("No changes to show")\n</parameter></function></tool_call>',
            },
            {
                "role": "tool",
                "content": f'<tool_response>GitDiffResult(success=True, file_count={file_count}, additions={additions}, deletions={deletions}, files={files_str}, parse_error=None)</tool_response>',
            },
            {
                "role": "assistant",
                "content": (
                    "No changes to show"
                    if file_count == 0
                    else f"Files changed: {file_count}\nTotal additions: {additions}\nTotal deletions: {deletions}\n\n"
                    + "\n".join(f"- {file}: +{adds} -{dels}" for file, adds, dels in files_data)
                ),
            },
        ]
        examples.append({"messages": messages})

    return examples


def create_git_log_tool_response_examples() -> list[dict]:
    """Create 10 git_log examples with realistic tool responses."""
    examples = []

    cases = [
        (
            "Get recent 5 commits",
            ".",
            5,
            [
                ("abc1234", "feat: add new authentication system"),
                ("def5678", "fix: resolve token expiration bug"),
                ("789abcd", "docs: update API documentation"),
                ("012ef34", "refactor: simplify user service"),
                ("345gh67", "test: add integration tests for auth"),
            ],
        ),
        (
            "Show last 3 commits",
            ".",
            3,
            [
                ("a1b2c3d", "feat: implement workspace symbols"),
                ("e4f5g6h", "fix: handle null hover responses"),
                ("i7j8k9l", "chore: update dependencies"),
            ],
        ),
        (
            "Get commit history (10 commits)",
            ".",
            10,
            [
                ("aaa1111", "feat: add git integration"),
                ("bbb2222", "feat: add document symbols"),
                ("ccc3333", "feat: add hover support"),
                ("ddd4444", "fix: parser error handling"),
                ("eee5555", "refactor: extract LSP client"),
                ("fff6666", "docs: add training guide"),
                ("ggg7777", "test: add parser tests"),
                ("hhh8888", "chore: update mlx"),
                ("iii9999", "fix: async bridge issue"),
                ("jjj0000", "feat: add ruff integration"),
            ],
        ),
        (
            "Show recent commit messages",
            ".",
            4,
            [
                ("111aaaa", "feat: add field access training"),
                ("222bbbb", "fix: validation script bug"),
                ("333cccc", "docs: document Phase 26"),
                ("444dddd", "refactor: merge training data"),
            ],
        ),
        (
            "Get last 7 commits",
            ".",
            7,
            [
                ("a1a1a1a", "feat: semantic validation"),
                ("b2b2b2b", "feat: parser tests"),
                ("c3c3c3c", "feat: tool responses"),
                ("d4d4d4d", "fix: git log parser"),
                ("e5e5e5e", "refactor: improve diversity"),
                ("f6f6f6f", "docs: audit findings"),
                ("g7g7g7g", "test: end-to-end validation"),
            ],
        ),
        (
            "Show commit log",
            ".",
            6,
            [
                ("aa11bb", "feat: add pytest integration"),
                ("cc22dd", "feat: add typecheck tool"),
                ("ee33ff", "fix: handle empty output"),
                ("gg44hh", "refactor: Code Mode format"),
                ("ii55jj", "docs: update examples"),
                ("kk66ll", "test: add unit tests"),
            ],
        ),
        (
            "Get recent 8 commits",
            ".",
            8,
            [
                ("1a2b3c", "feat: LSP navigation"),
                ("4d5e6f", "feat: goto definition"),
                ("7g8h9i", "feat: find references"),
                ("0j1k2l", "fix: URI parsing"),
                ("3m4n5o", "refactor: result models"),
                ("6p7q8r", "docs: LSP protocol"),
                ("9s0t1u", "test: LSP tests"),
                ("2v3w4x", "chore: update deps"),
            ],
        ),
        (
            "Show commit history (recent 5)",
            ".",
            5,
            [
                ("abc123", "feat: quantization"),
                ("def456", "feat: model fusion"),
                ("ghi789", "fix: memory leak"),
                ("jkl012", "refactor: training loop"),
                ("mno345", "docs: Phase 27 summary"),
            ],
        ),
        (
            "Get last 3 commit messages",
            ".",
            3,
            [
                ("111222", "feat: expand tool coverage"),
                ("333444", "feat: rebalance data"),
                ("555666", "fix: duplicate examples"),
            ],
        ),
        (
            "Show recent commits (4)",
            ".",
            4,
            [
                ("aaa111", "feat: add audit script"),
                ("bbb222", "feat: semantic checks"),
                ("ccc333", "fix: validation metrics"),
                ("ddd444", "docs: implementation guide"),
            ],
        ),
    ]

    for query, path, count, commits_data in cases:
        # Build commits list for tool response
        commits_repr = [
            f'GitCommit(hash="{hash}", message="{message}", author=None, date=None)' for hash, message in commits_data
        ]
        commits_str = f"[{', '.join(commits_repr)}]"

        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = git_log("{path}", {count})\nif result.commit_count > 0:\n    print(f"Recent {{result.commit_count}} commits:")\n    for commit in result.commits:\n        print(f"  {{commit.hash}} {{commit.message}}")\nelse:\n    print("No commits found")\n</parameter></function></tool_call>',
            },
            {
                "role": "tool",
                "content": f'<tool_response>GitLogResult(success=True, commits={commits_str}, commit_count={count}, parse_error=None)</tool_response>',
            },
            {
                "role": "assistant",
                "content": f"Recent {count} commits:\n\n" + "\n".join(f"- {hash}: {message}" for hash, message in commits_data),
            },
        ]
        examples.append({"messages": messages})

    return examples


def main():
    """Generate all tool response examples."""
    output_dir = Path(__file__).parent.parent / "data" / "phase27_tool_responses"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating tool response examples...")

    # Generate examples for each tool
    hover_examples = create_hover_tool_response_examples()
    print(f"  - hover: {len(hover_examples)} examples")

    doc_symbols_examples = create_document_symbols_tool_response_examples()
    print(f"  - document_symbols: {len(doc_symbols_examples)} examples")

    workspace_symbols_examples = create_workspace_symbols_tool_response_examples()
    print(f"  - workspace_symbols: {len(workspace_symbols_examples)} examples")

    git_status_examples = create_git_status_tool_response_examples()
    print(f"  - git_status: {len(git_status_examples)} examples")

    git_diff_examples = create_git_diff_tool_response_examples()
    print(f"  - git_diff: {len(git_diff_examples)} examples")

    git_log_examples = create_git_log_tool_response_examples()
    print(f"  - git_log: {len(git_log_examples)} examples")

    # Combine all examples
    all_examples = (
        hover_examples
        + doc_symbols_examples
        + workspace_symbols_examples
        + git_status_examples
        + git_diff_examples
        + git_log_examples
    )

    print(f"\nTotal: {len(all_examples)} examples")

    # Write to train.jsonl (no split for this augmentation - will be merged with existing data)
    train_file = output_dir / "train.jsonl"
    with open(train_file, "w") as f:
        for example in all_examples:
            f.write(json.dumps(example) + "\n")

    print(f"\nWrote {len(all_examples)} examples to {train_file}")
    print("Done!")


if __name__ == "__main__":
    main()
