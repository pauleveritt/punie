#!/usr/bin/env python3
"""Generate contrastive LSP vs grep examples for Phase 26.

These examples explicitly contrast when to use LSP tools (semantic navigation)
vs run_command with grep (text search). Each pair shows the same entity but
different query intents.

Goal: Teach the model the discriminating features:
- "find definition" / "where is X defined" → goto_definition()
- "where is X used" / "find references" → find_references()
- "search for text" / "find files containing" → run_command("grep")
"""

import json
from pathlib import Path


def create_contrastive_examples() -> list[dict]:
    """Generate 200 contrastive examples (100 pairs × 2)."""
    examples = []

    # Pattern 1: "Find definition" (LSP) vs "Search for class name" (grep)
    symbols = [
        ("UserService", "src/services/user.py", 45, 6),
        ("OrderProcessor", "src/models/order.py", 23, 6),
        ("PaymentHandler", "src/handlers/payment.py", 67, 6),
        ("DatabaseConnection", "src/db/connection.py", 12, 6),
        ("CacheManager", "src/cache/manager.py", 34, 6),
        ("APIClient", "src/api/client.py", 56, 6),
        ("ValidationError", "src/errors/validation.py", 89, 6),
        ("ConfigLoader", "src/config/loader.py", 15, 6),
        ("EventEmitter", "src/events/emitter.py", 78, 6),
        ("TaskQueue", "src/tasks/queue.py", 42, 6),
    ]

    for symbol, file, line, col in symbols:
        # LSP version (semantic: find definition)
        examples.append({
            "messages": [
                {
                    "role": "user",
                    "content": f"Where is the {symbol} class defined?"
                },
                {
                    "role": "assistant",
                    "content": f"""<tool_call><function=execute_code>
<parameter=code>
result = goto_definition("{file}", {line}, {col}, "{symbol}")
if result.success:
    loc = result.locations[0]
    print(f"{symbol} is defined at {{loc.file}}:{{loc.line}}:{{loc.column}}")
else:
    print("Definition not found")
</parameter>
</function></tool_call>"""
                }
            ]
        })

        # Grep version (text search: find occurrences)
        examples.append({
            "messages": [
                {
                    "role": "user",
                    "content": f"Search for all occurrences of the text '{symbol}' in the codebase"
                },
                {
                    "role": "assistant",
                    "content": f"""<tool_call><function=execute_code>
<parameter=code>
result = run_command("grep", args=["-r", "{symbol}", "--include=*.py"])
print(result)
</parameter>
</function></tool_call>"""
                }
            ]
        })

    # Pattern 2: "Find references" (LSP) vs "Search for function name" (grep)
    functions = [
        ("calculate_total", "src/models/invoice.py", 34, 8),
        ("process_payment", "src/handlers/payment.py", 56, 8),
        ("send_email", "src/services/email.py", 23, 8),
        ("validate_input", "src/utils/validation.py", 45, 8),
        ("parse_json", "src/parsers/json.py", 67, 8),
        ("fetch_user", "src/db/users.py", 89, 8),
        ("update_cache", "src/cache/redis.py", 12, 8),
        ("log_event", "src/logging/logger.py", 34, 8),
        ("encrypt_data", "src/security/crypto.py", 78, 8),
        ("compress_file", "src/utils/compression.py", 56, 8),
    ]

    for func, file, line, col in functions:
        # LSP version (semantic: find all callers)
        examples.append({
            "messages": [
                {
                    "role": "user",
                    "content": f"Where is {func} called in the codebase?"
                },
                {
                    "role": "assistant",
                    "content": f"""<tool_call><function=execute_code>
<parameter=code>
result = find_references("{file}", {line}, {col}, "{func}")
if result.success:
    print(f"{func} is referenced {{result.reference_count}} times:")
    for ref in result.references:
        print(f"  {{ref.file}}:{{ref.line}}")
else:
    print("No references found")
</parameter>
</function></tool_call>"""
                }
            ]
        })

        # Grep version (text search: find string matches)
        examples.append({
            "messages": [
                {
                    "role": "user",
                    "content": f"Find all files containing the string '{func}'"
                },
                {
                    "role": "assistant",
                    "content": f"""<tool_call><function=execute_code>
<parameter=code>
result = run_command("grep", args=["-r", "{func}", "--include=*.py"])
print(result)
</parameter>
</function></tool_call>"""
                }
            ]
        })

    # Pattern 3: "Show me where X is used" (LSP) vs "Search for 'X'" (grep)
    methods = [
        ("get_user_by_id", "src/services/user.py", 78, 8),
        ("create_order", "src/models/order.py", 45, 8),
        ("validate_token", "src/auth/tokens.py", 23, 8),
        ("render_template", "src/views/renderer.py", 67, 8),
        ("execute_query", "src/db/query.py", 89, 8),
        ("format_response", "src/api/formatter.py", 12, 8),
        ("handle_error", "src/errors/handler.py", 34, 8),
        ("load_config", "src/config/loader.py", 56, 8),
        ("publish_event", "src/events/publisher.py", 78, 8),
        ("schedule_task", "src/tasks/scheduler.py", 45, 8),
    ]

    for method, file, line, col in methods:
        # LSP version (semantic: find usages)
        examples.append({
            "messages": [
                {
                    "role": "user",
                    "content": f"Show me all places where {method} is used"
                },
                {
                    "role": "assistant",
                    "content": f"""<tool_call><function=execute_code>
<parameter=code>
result = find_references("{file}", {line}, {col}, "{method}")
if result.success:
    print(f"Found {{result.reference_count}} references to {method}:")
    for ref in result.references[:10]:  # Limit to first 10
        print(f"  {{ref.file}}:{{ref.line}}")
else:
    print("No references found")
</parameter>
</function></tool_call>"""
                }
            ]
        })

        # Grep version (text search: match substring)
        examples.append({
            "messages": [
                {
                    "role": "user",
                    "content": f"Search for the text '{method}' in all Python files"
                },
                {
                    "role": "assistant",
                    "content": f"""<tool_call><function=execute_code>
<parameter=code>
result = run_command("grep", args=["-r", "{method}", "--include=*.py"])
print(result)
</parameter>
</function></tool_call>"""
                }
            ]
        })

    # Pattern 4: "Find definition of X" (LSP) vs "Find TODO comments" (grep)
    definitions = [
        ("BaseModel", "src/models/base.py", 12, 6),
        ("AbstractHandler", "src/handlers/base.py", 23, 6),
        ("IRepository", "src/interfaces/repository.py", 34, 6),
        ("ConfigProtocol", "src/protocols/config.py", 45, 6),
        ("LoggerMixin", "src/mixins/logger.py", 56, 6),
    ]

    for symbol, file, line, col in definitions:
        # LSP version (semantic: go to definition)
        examples.append({
            "messages": [
                {
                    "role": "user",
                    "content": f"Find the definition of {symbol}"
                },
                {
                    "role": "assistant",
                    "content": f"""<tool_call><function=execute_code>
<parameter=code>
result = goto_definition("{file}", {line}, {col}, "{symbol}")
if result.success:
    loc = result.locations[0]
    print(f"{symbol} is defined at {{loc.file}}:{{loc.line}}")
else:
    print("Definition not found")
</parameter>
</function></tool_call>"""
                }
            ]
        })

    # Pure grep examples (comments, strings, patterns)
    grep_queries = [
        ("Find all TODO comments", "TODO", "TODO"),
        ("Find all FIXME comments", "FIXME", "FIXME"),
        ("Find all files with 'deprecated' in them", "deprecated", "deprecated"),
        ("Search for the string 'PLACEHOLDER'", "PLACEHOLDER", "PLACEHOLDER"),
        ("Find all print statements", "print(", "print\\\\("),
    ]

    for query, pattern, grep_pattern in grep_queries:
        examples.append({
            "messages": [
                {
                    "role": "user",
                    "content": query
                },
                {
                    "role": "assistant",
                    "content": f"""<tool_call><function=execute_code>
<parameter=code>
result = run_command("grep", args=["-r", "{grep_pattern}", "--include=*.py"])
print(result)
</parameter>
</function></tool_call>"""
                }
            ]
        })

    # Pattern 5: "How many times is X called" (LSP) vs "Count occurrences" (grep)
    callables = [
        ("submit_order", "src/api/orders.py", 45, 8),
        ("refresh_token", "src/auth/refresh.py", 23, 8),
        ("cleanup_cache", "src/cache/cleanup.py", 67, 8),
        ("send_notification", "src/notifications/sender.py", 34, 8),
        ("validate_schema", "src/validators/schema.py", 56, 8),
    ]

    for func, file, line, col in callables:
        # LSP version (semantic: count references)
        examples.append({
            "messages": [
                {
                    "role": "user",
                    "content": f"How many times is {func} called in the codebase?"
                },
                {
                    "role": "assistant",
                    "content": f"""<tool_call><function=execute_code>
<parameter=code>
result = find_references("{file}", {line}, {col}, "{func}")
if result.success:
    print(f"{func} is called {{result.reference_count}} times")
else:
    print("No references found")
</parameter>
</function></tool_call>"""
                }
            ]
        })

        # Grep version (text: count string occurrences)
        examples.append({
            "messages": [
                {
                    "role": "user",
                    "content": f"Count how many lines contain the text '{func}'"
                },
                {
                    "role": "assistant",
                    "content": f"""<tool_call><function=execute_code>
<parameter=code>
result = run_command("grep", args=["-r", "-c", "{func}", "--include=*.py"])
print(result)
</parameter>
</function></tool_call>"""
                }
            ]
        })

    return examples


def main():
    """Generate contrastive examples and save to file."""
    examples = create_contrastive_examples()

    output_dir = Path("data/phase26_contrastive")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "examples.jsonl"
    with output_file.open("w") as f:
        for example in examples:
            f.write(json.dumps(example) + "\n")

    print(f"Generated {len(examples)} contrastive examples")
    print(f"Saved to: {output_file}")

    # Count by pattern
    lsp_count = sum(1 for ex in examples if "goto_definition" in str(ex) or "find_references" in str(ex))
    grep_count = sum(1 for ex in examples if "run_command" in str(ex) and "grep" in str(ex))

    print("\nBreakdown:")
    print(f"  LSP examples (goto_definition/find_references): {lsp_count}")
    print(f"  Grep examples (run_command with grep): {grep_count}")
    print(f"  Total: {len(examples)}")


if __name__ == "__main__":
    main()
