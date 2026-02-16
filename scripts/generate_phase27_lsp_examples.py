"""Generate Phase 27 LSP training examples (hover, document_symbols, workspace_symbols).

Creates 180 examples:
- 30 hover discrimination (hover vs read_file for type info)
- 30 hover + field access (access result.content, result.language)
- 30 document_symbols discrimination (document_symbols vs grep for file structure)
- 30 document_symbols + field access (iterate result.symbols, access .kind)
- 30 workspace_symbols discrimination (workspace_symbols vs run_command grep)
- 30 workspace_symbols + field access (filter result.symbols, access .container_name)

All examples follow Phase 26 structural norms:
- 100% system messages
- ~37% multi-turn (5-message format)
- ~33% preambles
- Code Mode format (<tool_call><function=execute_code>)
"""

import json
import random
from pathlib import Path

# Set seed for reproducibility
random.seed(42)


def create_hover_discrimination_examples() -> list[dict]:
    """Create 30 hover discrimination examples (hover vs read_file)."""
    examples = []

    queries = [
        ("What's the type of UserService in src/services/user.py at line 15?", "src/services/user.py", 15, 5, "UserService"),
        ("Show me type information for the authenticate method at src/auth.py:42", "src/auth.py", 42, 10, "authenticate"),
        ("Get type signature for create_user function in src/models/user.py line 28", "src/models/user.py", 28, 5, "create_user"),
        ("What's the return type of process_data at src/processors/data.py:67?", "src/processors/data.py", 67, 8, "process_data"),
        ("Show hover info for DatabaseConnection class at src/db/connection.py line 12", "src/db/connection.py", 12, 7, "DatabaseConnection"),
        ("Get type info for validate_email at src/utils/validation.py:34", "src/utils/validation.py", 34, 5, "validate_email"),
        ("What does the TokenManager class look like at src/auth/tokens.py line 21?", "src/auth/tokens.py", 21, 7, "TokenManager"),
        ("Show me the signature of send_notification in src/notifications.py:55", "src/notifications.py", 55, 5, "send_notification"),
        ("Get type details for ApiClient at src/api/client.py line 18", "src/api/client.py", 18, 7, "ApiClient"),
        ("What's the type of config variable at src/config.py:89?", "src/config.py", 89, 1, "config"),
    ]

    for query, file_path, line, col, symbol in queries:
        # Single-turn with system message
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = hover("{file_path}", {line}, {col}, "{symbol}")\nif result.success:\n    print(f"Type: {{result.content}}")\nelse:\n    print("No type information available")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn with preamble
        if len(examples) % 3 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": f"I'll use hover to get type information for {symbol}.",
                },
                {
                    "role": "user",
                    "content": "Yes, show me the type info.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\nresult = hover("{file_path}", {line}, {col}, "{symbol}")\nif result.success:\n    print(f"Type: {{result.content}}")\n    print(f"Language: {{result.language}}")\nelse:\n    print("No hover info found")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:30]


def create_hover_field_access_examples() -> list[dict]:
    """Create 30 hover + field access examples."""
    examples = []

    queries = [
        ("Check if UserService has type info and show it", "src/services/user.py", 15, 5, "UserService"),
        ("Get hover content for authenticate and check language", "src/auth.py", 42, 10, "authenticate"),
        ("Show type info content for create_user if available", "src/models/user.py", 28, 5, "create_user"),
        ("Check hover language for process_data and display content", "src/processors/data.py", 67, 8, "process_data"),
        ("Get DatabaseConnection hover and show content length", "src/db/connection.py", 12, 7, "DatabaseConnection"),
        ("Check if validate_email has hover content", "src/utils/validation.py", 34, 5, "validate_email"),
        ("Show TokenManager hover content if success is true", "src/auth/tokens.py", 21, 7, "TokenManager"),
        ("Get hover for send_notification and check content", "src/notifications.py", 55, 5, "send_notification"),
        ("Display ApiClient hover content and language", "src/api/client.py", 18, 7, "ApiClient"),
        ("Check if config has hover and show first 100 chars", "src/config.py", 89, 1, "config"),
    ]

    for query, file_path, line, col, symbol in queries:
        # Field access with conditional
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = hover("{file_path}", {line}, {col}, "{symbol}")\nif result.success and result.content:\n    print(f"Content: {{result.content[:200]}}")\n    print(f"Language: {{result.language}}")\nelse:\n    print(f"No hover info for {symbol}")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn with content length check
        if len(examples) % 3 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": f"I'll check hover information for {symbol}.",
                },
                {
                    "role": "user",
                    "content": "Show me the details.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\nresult = hover("{file_path}", {line}, {col}, "{symbol}")\nif result.success:\n    content_len = len(result.content) if result.content else 0\n    print(f"Has content: {{content_len > 0}}")\n    print(f"Content length: {{content_len}} chars")\n    print(f"Language: {{result.language}}")\nelse:\n    print("No hover available")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:30]


def create_document_symbols_discrimination_examples() -> list[dict]:
    """Create 30 document_symbols discrimination examples."""
    examples = []

    queries = [
        ("What classes and functions are in src/services/user.py?", "src/services/user.py"),
        ("Show me the structure of src/auth.py", "src/auth.py"),
        ("List all symbols in src/models/user.py", "src/models/user.py"),
        ("What's defined in src/processors/data.py?", "src/processors/data.py"),
        ("Show file structure for src/db/connection.py", "src/db/connection.py"),
        ("Get all symbols from src/utils/validation.py", "src/utils/validation.py"),
        ("What classes are in src/auth/tokens.py?", "src/auth/tokens.py"),
        ("List functions in src/notifications.py", "src/notifications.py"),
        ("Show structure of src/api/client.py", "src/api/client.py"),
        ("What's defined in src/config.py?", "src/config.py"),
    ]

    for query, file_path in queries:
        # Single-turn
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = document_symbols("{file_path}")\nif result.success:\n    print(f"Found {{result.symbol_count}} symbols")\n    for symbol in result.symbols:\n        print(f"  {{symbol.name}} (kind={{symbol.kind}}) at line {{symbol.line}}")\nelse:\n    print("No symbols found")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn with preamble
        if len(examples) % 3 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": "I'll use document_symbols to get the file structure.",
                },
                {
                    "role": "user",
                    "content": "Go ahead.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\nresult = document_symbols("{file_path}")\nif result.success:\n    print(f"File: {{result.file_path}}")\n    print(f"Total symbols: {{result.symbol_count}}")\n    for symbol in result.symbols[:5]:  # Show first 5\n        print(f"  {{symbol.name}} at line {{symbol.line}}")\nelse:\n    print("No symbols available")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:30]


def create_document_symbols_field_access_examples() -> list[dict]:
    """Create 30 document_symbols + field access examples."""
    examples = []

    queries = [
        ("Count classes in src/services/user.py", "src/services/user.py"),
        ("How many functions are in src/auth.py?", "src/auth.py"),
        ("Show symbols by kind in src/models/user.py", "src/models/user.py"),
        ("Filter classes from src/processors/data.py", "src/processors/data.py"),
        ("Count methods in src/db/connection.py", "src/db/connection.py"),
        ("Show function names from src/utils/validation.py", "src/utils/validation.py"),
        ("List class symbols in src/auth/tokens.py", "src/auth/tokens.py"),
        ("Count all symbols in src/notifications.py", "src/notifications.py"),
        ("Show top-level symbols in src/api/client.py", "src/api/client.py"),
        ("Filter by symbol kind in src/config.py", "src/config.py"),
    ]

    for query, file_path in queries:
        # Field access with filtering
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = document_symbols("{file_path}")\nif result.success:\n    classes = [s for s in result.symbols if s.kind == 5]  # Class kind\n    functions = [s for s in result.symbols if s.kind == 12]  # Function kind\n    print(f"Classes: {{len(classes)}}")\n    print(f"Functions: {{len(functions)}}")\n    print(f"Total: {{result.symbol_count}}")\nelse:\n    print("No symbols found")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn with iteration
        if len(examples) % 3 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": "I'll analyze the symbol kinds.",
                },
                {
                    "role": "user",
                    "content": "Show me the breakdown.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\nresult = document_symbols("{file_path}")\nif result.success:\n    for symbol in result.symbols:\n        if symbol.children:\n            print(f"{{symbol.name}}: {{len(symbol.children)}} children")\n        else:\n            print(f"{{symbol.name}} at line {{symbol.line}}")\nelse:\n    print("No symbols available")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:30]


def create_workspace_symbols_discrimination_examples() -> list[dict]:
    """Create 30 workspace_symbols discrimination examples."""
    examples = []

    queries = [
        ("Find all UserService symbols in the workspace", "UserService"),
        ("Search for authenticate functions", "authenticate"),
        ("Find create_user across the codebase", "create_user"),
        ("Search for DatabaseConnection", "DatabaseConnection"),
        ("Find all TokenManager references", "TokenManager"),
        ("Search for ApiClient in the workspace", "ApiClient"),
        ("Find process_data symbols", "process_data"),
        ("Search for validate_email", "validate_email"),
        ("Find notification symbols", "notification"),
        ("Search for config symbols", "config"),
    ]

    for query, symbol_query in queries:
        # Single-turn
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = workspace_symbols("{symbol_query}")\nif result.success:\n    print(f"Found {{result.symbol_count}} matches")\n    for symbol in result.symbols:\n        print(f"  {{symbol.name}} in {{symbol.file}}:{{symbol.line}}")\nelse:\n    print("No symbols found")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn with preamble
        if len(examples) % 3 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": f"I'll search the workspace for '{symbol_query}'.",
                },
                {
                    "role": "user",
                    "content": "Show the results.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\nresult = workspace_symbols("{symbol_query}")\nif result.success:\n    print(f"Query: {{result.query}}")\n    print(f"Matches: {{result.symbol_count}}")\n    for symbol in result.symbols[:10]:  # First 10\n        container = f" in {{symbol.container_name}}" if symbol.container_name else ""\n        print(f"  {{symbol.name}}{{container}} at {{symbol.file}}:{{symbol.line}}")\nelse:\n    print("No matches found")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:30]


def create_workspace_symbols_field_access_examples() -> list[dict]:
    """Create 30 workspace_symbols + field access examples."""
    examples = []

    queries = [
        ("Find UserService and filter by container", "UserService"),
        ("Search authenticate and count by file", "authenticate"),
        ("Find create_user and show container names", "create_user"),
        ("Search DatabaseConnection and group by kind", "DatabaseConnection"),
        ("Find TokenManager in specific containers", "TokenManager"),
        ("Search ApiClient and filter by file", "ApiClient"),
        ("Find process_data and count occurrences", "process_data"),
        ("Search validate_email and show containers", "validate_email"),
        ("Find notification symbols by kind", "notification"),
        ("Search config and filter results", "config"),
    ]

    for query, symbol_query in queries:
        # Field access with filtering
        messages = [
            {"role": "system", "content": "You are Punie, an AI coding assistant."},
            {"role": "user", "content": query},
            {
                "role": "assistant",
                "content": f'<tool_call><function=execute_code><parameter=code>\nresult = workspace_symbols("{symbol_query}")\nif result.success:\n    with_container = [s for s in result.symbols if s.container_name]\n    print(f"Total: {{result.symbol_count}}")\n    print(f"With container: {{len(with_container)}}")\n    for symbol in with_container[:5]:\n        print(f"  {{symbol.name}} in {{symbol.container_name}}")\nelse:\n    print("No symbols found")\n</parameter></function></tool_call>',
            },
        ]
        examples.append({"messages": messages})

        # Multi-turn with grouping
        if len(examples) % 3 == 0:
            messages_multi = [
                {"role": "system", "content": "You are Punie, an AI coding assistant."},
                {"role": "user", "content": query},
                {
                    "role": "assistant",
                    "content": "I'll search and group the results.",
                },
                {
                    "role": "user",
                    "content": "Show me the breakdown.",
                },
                {
                    "role": "assistant",
                    "content": f'<tool_call><function=execute_code><parameter=code>\nresult = workspace_symbols("{symbol_query}")\nif result.success:\n    files = {{}}\n    for symbol in result.symbols:\n        if symbol.file not in files:\n            files[symbol.file] = 0\n        files[symbol.file] += 1\n    print(f"Found in {{len(files)}} files:")\n    for file, count in files.items():\n        print(f"  {{file}}: {{count}} matches")\nelse:\n    print("No symbols found")\n</parameter></function></tool_call>',
                },
            ]
            examples.append({"messages": messages_multi})

    return examples[:30]


def main():
    """Generate all Phase 27 LSP examples."""
    output_dir = Path("data/phase27_lsp")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_examples = []

    print("Generating hover discrimination examples...")
    all_examples.extend(create_hover_discrimination_examples())

    print("Generating hover field access examples...")
    all_examples.extend(create_hover_field_access_examples())

    print("Generating document_symbols discrimination examples...")
    all_examples.extend(create_document_symbols_discrimination_examples())

    print("Generating document_symbols field access examples...")
    all_examples.extend(create_document_symbols_field_access_examples())

    print("Generating workspace_symbols discrimination examples...")
    all_examples.extend(create_workspace_symbols_discrimination_examples())

    print("Generating workspace_symbols field access examples...")
    all_examples.extend(create_workspace_symbols_field_access_examples())

    # Shuffle examples
    random.shuffle(all_examples)

    # Save as JSONL
    output_file = output_dir / "phase27_lsp_examples.jsonl"
    with open(output_file, "w") as f:
        for example in all_examples:
            f.write(json.dumps(example) + "\n")

    print(f"\nGenerated {len(all_examples)} LSP examples")
    print(f"Saved to: {output_file}")

    # Print distribution
    single_turn = sum(1 for ex in all_examples if len(ex["messages"]) == 3)
    multi_turn = sum(1 for ex in all_examples if len(ex["messages"]) == 5)
    print("\nDistribution:")
    print(f"  Single-turn: {single_turn} ({single_turn/len(all_examples)*100:.1f}%)")
    print(f"  Multi-turn: {multi_turn} ({multi_turn/len(all_examples)*100:.1f}%)")


if __name__ == "__main__":
    main()
