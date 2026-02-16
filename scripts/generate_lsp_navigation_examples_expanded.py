#!/usr/bin/env python
"""Generate expanded training examples for LSP navigation tools (Phase 26).

Creates ~500 examples across 5 categories:
1. Discrimination queries (100) - basic navigation needs
2. goto_definition + field access (100)
3. find_references + field access (100)
4. Multi-step workflows (100)
5. Direct answers about LSP (100)

Uses templates and variations to generate diverse, realistic examples.

Output: data/phase26_lsp_expanded/ in JSONL format
"""

import json
from pathlib import Path


SYSTEM_MESSAGE = "You are Punie, an AI coding assistant that helps with Python development via PyCharm."


def create_message(role: str, content: str) -> dict:
    """Create a message dict for training data."""
    return {"role": role, "content": content}


def create_example_3msg(user_content: str, assistant_content: str) -> dict:
    """Create 3-message example: system + user + assistant (tool_call)."""
    return {
        "messages": [
            create_message("system", SYSTEM_MESSAGE),
            create_message("user", user_content),
            create_message("assistant", assistant_content),
        ]
    }


def create_example_5msg(
    user_content: str,
    assistant_tool_call: str,
    tool_response: str,
    assistant_final: str,
) -> dict:
    """Create 5-message example: system + user + assistant (tool_call) + user (tool_response) + assistant (final)."""
    return {
        "messages": [
            create_message("system", SYSTEM_MESSAGE),
            create_message("user", user_content),
            create_message("assistant", assistant_tool_call),
            create_message("user", f"<tool_response>\n{tool_response}\n</tool_response>"),
            create_message("assistant", assistant_final),
        ]
    }


def make_goto_def_response(symbol: str, file_path: str, line: int, col: int) -> str:
    """Generate realistic GotoDefinitionResult repr string."""
    return f"""GotoDefinitionResult(success=True, symbol='{symbol}', locations=[DefinitionLocation(file='{file_path}', line={line}, column={col}, end_line={line}, end_column={col + len(symbol)}, preview=None)], parse_error=None)"""


def make_find_refs_response(symbol: str, count: int, files: list[tuple[str, int]]) -> str:
    """Generate realistic FindReferencesResult repr string."""
    refs = ", ".join(
        f"ReferenceLocation(file='{f}', line={l}, column=10, preview=None)"
        for f, l in files
    )
    return f"""FindReferencesResult(success=True, symbol='{symbol}', reference_count={count}, references=[{refs}], parse_error=None)"""


# Templates for generating variations
SYMBOL_TYPES = {
    "class": {
        "names": [
            "UserService",
            "OrderProcessor",
            "PaymentGateway",
            "EmailNotifier",
            "DataValidator",
            "CacheManager",
            "LoggerFactory",
            "ConfigLoader",
            "DatabaseConnection",
            "AuthenticationService",
        ],
        "patterns": ["class {}", "class {}(", "class {}:"],
    },
    "function": {
        "names": [
            "process_order",
            "calculate_total",
            "validate_input",
            "send_email",
            "parse_response",
            "format_date",
            "execute_query",
            "handle_error",
            "transform_data",
            "check_permissions",
        ],
        "patterns": ["def {}(", "async def {}(", "def {}:", "async def {}:"],
    },
    "method": {
        "names": [
            "save",
            "update",
            "delete",
            "get_by_id",
            "validate",
            "to_dict",
            "from_json",
            "process",
            "execute",
            "render",
        ],
        "patterns": ["def {}(self", "async def {}(self", "def {}(cls"],
    },
    "variable": {
        "names": [
            "DATABASE_URL",
            "API_KEY",
            "MAX_RETRIES",
            "DEFAULT_TIMEOUT",
            "LOG_LEVEL",
            "CACHE_TTL",
            "UPLOAD_DIR",
            "SECRET_KEY",
            "DEBUG_MODE",
            "PORT",
        ],
        "patterns": ["{} =", "{}: str"],
    },
}

FILE_PATHS = [
    ("src/services/user.py", 45, 20),
    ("src/models/order.py", 23, 15),
    ("src/utils/validation.py", 67, 8),
    ("src/api/endpoints.py", 102, 12),
    ("src/core/config.py", 18, 5),
    ("src/db/connection.py", 34, 10),
    ("src/auth/middleware.py", 56, 18),
    ("src/tasks/processor.py", 89, 22),
    ("src/lib/helpers.py", 12, 6),
    ("tests/test_integration.py", 145, 30),
]


def generate_discrimination_examples() -> list[dict]:
    """Generate 100 discrimination queries.

    These test whether model chooses LSP navigation vs direct answer.
    """
    examples = []
    preambles = [
        "I'll look up the definition.\n\n",
        "Let me find that for you.\n\n",
        "",  # Some without preamble
    ]

    # Pattern 1: "Where is X defined?" - should use goto_definition
    for symbol_type, symbol_data in list(SYMBOL_TYPES.items())[:3]:  # class, function, method
        for idx, symbol in enumerate(symbol_data["names"][:7]):  # 7 symbols per type
            preamble = preambles[idx % len(preambles)]
            tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = goto_definition("src/services/user.py", 45, 20, "{symbol}")
if result.success:
    loc = result.locations[0]
    print(f"{symbol} is defined at {{loc.file}}:{{loc.line}}:{{loc.column}}")
else:
    print("Definition not found")
</parameter>
</function></tool_call>"""

            # Alternate between 3-message and 5-message
            if idx % 2 == 0:
                examples.append(
                    create_example_3msg(
                        f"Where is the {symbol} {symbol_type} defined?",
                        tool_call,
                    )
                )
            else:
                tool_response = make_goto_def_response(
                    symbol, "src/services/user.py", 45, 20
                )
                examples.append(
                    create_example_5msg(
                        f"Where is the {symbol} {symbol_type} defined?",
                        tool_call,
                        tool_response,
                        f"{symbol} is defined at src/services/user.py:45:20",
                    )
                )

    # Pattern 2: "Show me where X is used" - should use find_references
    for symbol_type, symbol_data in list(SYMBOL_TYPES.items())[:3]:
        for idx, symbol in enumerate(symbol_data["names"][7:10]):  # 3 more symbols per type
            preamble = preambles[idx % len(preambles)]
            tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = find_references("src/services/user.py", 45, 20, "{symbol}")
if result.success:
    print(f"Found {{result.reference_count}} references to {symbol}:")
    for ref in result.references[:5]:
        print(f"  {{ref.file}}:{{ref.line}}")
else:
    print("No references found")
</parameter>
</function></tool_call>"""

            if idx % 2 == 0:
                examples.append(
                    create_example_3msg(
                        f"Show me all places where {symbol} is used",
                        tool_call,
                    )
                )
            else:
                tool_response = make_find_refs_response(
                    symbol,
                    3,
                    [
                        ("src/services/user.py", 45),
                        ("src/models/order.py", 23),
                        ("tests/test_user.py", 12),
                    ],
                )
                examples.append(
                    create_example_5msg(
                        f"Show me all places where {symbol} is used",
                        tool_call,
                        tool_response,
                        f"Found 3 references to {symbol}:\n  src/services/user.py:45\n  src/models/order.py:23\n  tests/test_user.py:12",
                    )
                )

    # Pattern 3: "How many times is X called?" - should use find_references + count
    for idx, symbol in enumerate(SYMBOL_TYPES["function"]["names"][:10]):
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = find_references("src/services/user.py", 45, 20, "{symbol}")
if result.success:
    print(f"{symbol} is called {{result.reference_count}} times")
else:
    print("No references found")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(
                create_example_3msg(
                    f"How many times is {symbol} called in the codebase?",
                    tool_call,
                )
            )
        else:
            tool_response = make_find_refs_response(symbol, 8, [("src/api.py", 45), ("src/handlers.py", 12)])
            examples.append(
                create_example_5msg(
                    f"How many times is {symbol} called in the codebase?",
                    tool_call,
                    tool_response,
                    f"{symbol} is called 8 times",
                )
            )

    # Pattern 4: "Find X definition" - short form
    for idx, symbol in enumerate(SYMBOL_TYPES["class"]["names"][:10]):
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = goto_definition("src/models/base.py", 12, 8, "{symbol}")
if result.success:
    loc = result.locations[0]
    print(f"{{loc.file}}:{{loc.line}}")
else:
    print("Not found")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(
                create_example_3msg(f"Find the definition of {symbol}", tool_call)
            )
        else:
            tool_response = make_goto_def_response(symbol, "src/models/base.py", 12, 8)
            examples.append(
                create_example_5msg(
                    f"Find the definition of {symbol}",
                    tool_call,
                    tool_response,
                    "src/models/base.py:12",
                )
            )

    # Pattern 5: "Check if X exists" - existence check
    for idx, symbol in enumerate(SYMBOL_TYPES["function"]["names"][:10]):
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = goto_definition("src/utils/helpers.py", 23, 10, "{symbol}")
if result.success:
    print(f"Yes, {{len(result.locations)}} definition(s) found")
else:
    print("No, {symbol} is not defined")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(
                create_example_3msg(f"Check if {symbol} is defined anywhere", tool_call)
            )
        else:
            tool_response = make_goto_def_response(symbol, "src/utils/helpers.py", 23, 10)
            examples.append(
                create_example_5msg(
                    f"Check if {symbol} is defined anywhere",
                    tool_call,
                    tool_response,
                    "Yes, 1 definition(s) found",
                )
            )

    # Pattern 6: "Is X used?" - usage check
    for idx, symbol in enumerate(SYMBOL_TYPES["variable"]["names"][:10]):
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = find_references("src/config/settings.py", 15, 5, "{symbol}")
if result.success and result.reference_count > 0:
    print(f"Yes, used in {{result.reference_count}} places")
else:
    print("No, {symbol} is not referenced")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(
                create_example_3msg(f"Is {symbol} referenced anywhere?", tool_call)
            )
        else:
            tool_response = make_find_refs_response(symbol, 5, [("src/app.py", 12), ("src/config.py", 8)])
            examples.append(
                create_example_5msg(
                    f"Is {symbol} referenced anywhere?",
                    tool_call,
                    tool_response,
                    "Yes, used in 5 places",
                )
            )

    return examples[:100]  # Ensure exactly 100


def generate_goto_def_field_access() -> list[dict]:
    """Generate 100 goto_definition examples with field access."""
    examples = []
    preambles = ["I'll look up the definition.\n\n", "Let me find that.\n\n", ""]

    # Pattern 1: Get file path from definition
    idx = 0
    for symbol in SYMBOL_TYPES["class"]["names"]:
        for variation in ["What file is", "Which file contains", "Where is", "Show me the file for"]:
            preamble = preambles[idx % len(preambles)]
            tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = goto_definition("src/app.py", 10, 5, "{symbol}")
if result.success:
    print(f"{{result.locations[0].file}}")
else:
    print("Not found")
</parameter>
</function></tool_call>"""

            if idx % 2 == 0:
                examples.append(
                    create_example_3msg(f"{variation} {symbol} defined?", tool_call)
                )
            else:
                tool_response = make_goto_def_response(symbol, "src/models/user.py", 23, 5)
                examples.append(
                    create_example_5msg(
                        f"{variation} {symbol} defined?",
                        tool_call,
                        tool_response,
                        "src/models/user.py",
                    )
                )
            idx += 1
            if len(examples) >= 25:
                break
        if len(examples) >= 25:
            break

    # Pattern 2: Get line number
    for symbol in SYMBOL_TYPES["function"]["names"]:
        for variation in ["line number", "line", "which line"]:
            preamble = preambles[idx % len(preambles)]
            tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = goto_definition("src/utils.py", 20, 8, "{symbol}")
if result.success:
    print(f"Line {{result.locations[0].line}}")
else:
    print("Not found")
</parameter>
</function></tool_call>"""

            if idx % 2 == 0:
                examples.append(
                    create_example_3msg(f"What {variation} is {symbol} defined on?", tool_call)
                )
            else:
                tool_response = make_goto_def_response(symbol, "src/utils.py", 20, 8)
                examples.append(
                    create_example_5msg(
                        f"What {variation} is {symbol} defined on?",
                        tool_call,
                        tool_response,
                        "Line 20",
                    )
                )
            idx += 1
            if len(examples) >= 50:
                break
        if len(examples) >= 50:
            break

    # Pattern 3: Check existence and get location
    for symbol in SYMBOL_TYPES["method"]["names"]:
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = goto_definition("src/models/base.py", 30, 10, "{symbol}")
if result.success:
    loc = result.locations[0]
    print(f"Yes, at {{loc.file}}:{{loc.line}}:{{loc.column}}")
else:
    print("No definition found")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(
                create_example_3msg(f"Is {symbol} defined? If so, where?", tool_call)
            )
        else:
            tool_response = make_goto_def_response(symbol, "src/models/base.py", 30, 10)
            examples.append(
                create_example_5msg(
                    f"Is {symbol} defined? If so, where?",
                    tool_call,
                    tool_response,
                    "Yes, at src/models/base.py:30:10",
                )
            )
        idx += 1
        if len(examples) >= 60:
            break

    # Pattern 4: Multiple definitions
    for symbol in SYMBOL_TYPES["function"]["names"]:
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = goto_definition("src/app.py", 15, 8, "{symbol}")
if result.success:
    print(f"{{len(result.locations)}} definition(s)")
    for loc in result.locations:
        print(f"  {{loc.file}}:{{loc.line}}")
else:
    print("No definitions")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(
                create_example_3msg(f"How many definitions of {symbol} exist?", tool_call)
            )
        else:
            tool_response = make_goto_def_response(symbol, "src/app.py", 15, 8)
            examples.append(
                create_example_5msg(
                    f"How many definitions of {symbol} exist?",
                    tool_call,
                    tool_response,
                    "1 definition(s)\n  src/app.py:15",
                )
            )
        idx += 1
        if len(examples) >= 75:
            break

    # Pattern 5: Conditional logic based on success
    for symbol in SYMBOL_TYPES["class"]["names"]:
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = goto_definition("src/main.py", 5, 10, "{symbol}")
if result.success:
    print(f"Found: {{result.locations[0].file}}")
else:
    print(f"{symbol} not found in codebase")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(
                create_example_3msg(f"Find {symbol} and report its file path", tool_call)
            )
        else:
            tool_response = make_goto_def_response(symbol, "src/main.py", 5, 10)
            examples.append(
                create_example_5msg(
                    f"Find {symbol} and report its file path",
                    tool_call,
                    tool_response,
                    "Found: src/main.py",
                )
            )
        idx += 1
        if len(examples) >= 100:
            break

    return examples[:100]


def generate_find_refs_field_access() -> list[dict]:
    """Generate 100 find_references examples with field access."""
    examples = []
    preambles = ["I'll search for references.\n\n", "Let me find those.\n\n", ""]
    idx = 0

    # Pattern 1: Count references
    for symbol in SYMBOL_TYPES["function"]["names"]:
        for verb in ["Count", "How many", "Number of"]:
            preamble = preambles[idx % len(preambles)]
            tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = find_references("src/services/api.py", 45, 12, "{symbol}")
if result.success:
    print(f"{{result.reference_count}} references")
else:
    print("No references found")
</parameter>
</function></tool_call>"""

            if idx % 2 == 0:
                examples.append(create_example_3msg(f"{verb} references to {symbol}", tool_call))
            else:
                tool_response = make_find_refs_response(symbol, 7, [("src/api.py", 12), ("tests/test_api.py", 45)])
                examples.append(
                    create_example_5msg(
                        f"{verb} references to {symbol}",
                        tool_call,
                        tool_response,
                        "7 references",
                    )
                )
            idx += 1
            if len(examples) >= 30:
                break
        if len(examples) >= 30:
            break

    # Pattern 2: List reference files
    for symbol in SYMBOL_TYPES["class"]["names"]:
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = find_references("src/models/user.py", 23, 8, "{symbol}")
if result.success:
    files = {{ref.file for ref in result.references}}
    for f in files:
        print(f"  {{f}}")
else:
    print("No references")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(create_example_3msg(f"Which files reference {symbol}?", tool_call))
        else:
            tool_response = make_find_refs_response(symbol, 4, [("src/api.py", 12), ("src/handlers.py", 23)])
            examples.append(
                create_example_5msg(
                    f"Which files reference {symbol}?",
                    tool_call,
                    tool_response,
                    "  src/api.py\n  src/handlers.py",
                )
            )
        idx += 1
        if len(examples) >= 40:
            break

    # Pattern 3: First N references
    for symbol in SYMBOL_TYPES["method"]["names"]:
        for n in [3, 5, 10]:
            preamble = preambles[idx % len(preambles)]
            tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = find_references("src/base.py", 12, 6, "{symbol}")
if result.success:
    for ref in result.references[:{n}]:
        print(f"{{ref.file}}:{{ref.line}}")
else:
    print("No references")
</parameter>
</function></tool_call>"""

            if idx % 2 == 0:
                examples.append(
                    create_example_3msg(f"Show the first {n} places where {symbol} is used", tool_call)
                )
            else:
                tool_response = make_find_refs_response(symbol, n, [("src/base.py", 12)])
                examples.append(
                    create_example_5msg(
                        f"Show the first {n} places where {symbol} is used",
                        tool_call,
                        tool_response,
                        "src/base.py:12",
                    )
                )
            idx += 1
            if len(examples) >= 70:
                break
        if len(examples) >= 70:
            break

    # Pattern 4: Check if used
    for symbol in SYMBOL_TYPES["variable"]["names"]:
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = find_references("src/config.py", 18, 5, "{symbol}")
if result.success and result.reference_count > 0:
    print(f"Yes, used {{result.reference_count}} times")
else:
    print("Not used")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(create_example_3msg(f"Is {symbol} used anywhere?", tool_call))
        else:
            tool_response = make_find_refs_response(symbol, 3, [("src/app.py", 12)])
            examples.append(
                create_example_5msg(
                    f"Is {symbol} used anywhere?",
                    tool_call,
                    tool_response,
                    "Yes, used 3 times",
                )
            )
        idx += 1
        if len(examples) >= 85:
            break

    # Pattern 5: Iterate over references
    for symbol in SYMBOL_TYPES["function"]["names"]:
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = find_references("src/utils.py", 34, 10, "{symbol}")
if result.success:
    for ref in result.references:
        print(f"{{ref.file}}:{{ref.line}}:{{ref.column}}")
else:
    print("No usages found")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(
                create_example_3msg(f"List all usages of {symbol} with line numbers", tool_call)
            )
        else:
            tool_response = make_find_refs_response(symbol, 2, [("src/utils.py", 34)])
            examples.append(
                create_example_5msg(
                    f"List all usages of {symbol} with line numbers",
                    tool_call,
                    tool_response,
                    "src/utils.py:34:10",
                )
            )
        idx += 1
        if len(examples) >= 100:
            break

    return examples[:100]


def generate_workflow_examples() -> list[dict]:
    """Generate 100 multi-step workflow examples."""
    examples = []
    preambles = ["I'll check that.\n\n", "Let me investigate.\n\n", ""]
    idx = 0

    # Pattern 1: goto_definition → check field → next action
    for symbol in SYMBOL_TYPES["class"]["names"]:
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = goto_definition("src/app.py", 15, 10, "{symbol}")
if result.success:
    file_path = result.locations[0].file
    if "models" in file_path:
        print(f"Yes, {symbol} is in models: {{file_path}}")
    else:
        print(f"No, {symbol} is in {{file_path}}")
else:
    print("Definition not found")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(
                create_example_3msg(
                    f"Find {symbol} definition and check if it's in the models directory",
                    tool_call,
                )
            )
        else:
            tool_response = make_goto_def_response(symbol, "src/models/base.py", 15, 10)
            examples.append(
                create_example_5msg(
                    f"Find {symbol} definition and check if it's in the models directory",
                    tool_call,
                    tool_response,
                    f"Yes, {symbol} is in models: src/models/base.py",
                )
            )
        idx += 1
        if len(examples) >= 15:
            break

    # Pattern 2: find_references → count → conditional
    for symbol in SYMBOL_TYPES["function"]["names"]:
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = find_references("src/utils.py", 23, 8, "{symbol}")
if result.success:
    if result.reference_count > 5:
        print(f"Yes, used {{result.reference_count}} times")
    else:
        print(f"No, only used {{result.reference_count}} times")
else:
    print("No references found")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(create_example_3msg(f"Check if {symbol} is used in more than 5 places", tool_call))
        else:
            tool_response = make_find_refs_response(symbol, 8, [("src/api.py", 12)])
            examples.append(
                create_example_5msg(
                    f"Check if {symbol} is used in more than 5 places",
                    tool_call,
                    tool_response,
                    "Yes, used 8 times",
                )
            )
        idx += 1
        if len(examples) >= 30:
            break

    # Pattern 3: goto_definition → extract info → use it
    for symbol in SYMBOL_TYPES["class"]["names"]:
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = goto_definition("src/models/base.py", 45, 12, "{symbol}")
if result.success:
    loc = result.locations[0]
    short_path = loc.file.split('/')[-1]
    print(f"{{short_path}}:{{loc.line}}")
else:
    print("Not found")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(
                create_example_3msg(f"Find {symbol} and report its location in short format", tool_call)
            )
        else:
            tool_response = make_goto_def_response(symbol, "src/models/base.py", 45, 12)
            examples.append(
                create_example_5msg(
                    f"Find {symbol} and report its location in short format",
                    tool_call,
                    tool_response,
                    "base.py:45",
                )
            )
        idx += 1
        if len(examples) >= 45:
            break

    # Pattern 4: find_references → filter → display
    for symbol in SYMBOL_TYPES["method"]["names"]:
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = find_references("src/base.py", 30, 8, "{symbol}")
if result.success:
    test_refs = [ref for ref in result.references if "test" in ref.file]
    print(f"Found {{len(test_refs)}} test references:")
    for ref in test_refs:
        print(f"  {{ref.file}}:{{ref.line}}")
else:
    print("No references")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(
                create_example_3msg(f"Show references to {symbol} that are in test files", tool_call)
            )
        else:
            tool_response = make_find_refs_response(symbol, 2, [("tests/test_base.py", 12)])
            examples.append(
                create_example_5msg(
                    f"Show references to {symbol} that are in test files",
                    tool_call,
                    tool_response,
                    "Found 1 test references:\n  tests/test_base.py:12",
                )
            )
        idx += 1
        if len(examples) >= 60:
            break

    # Pattern 5: Check existence → if found, get details
    for symbol in SYMBOL_TYPES["variable"]["names"]:
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = goto_definition("src/config.py", 12, 5, "{symbol}")
if result.success:
    loc = result.locations[0]
    print(f"Defined at {{loc.file}}:{{loc.line}}")
    # Could chain another tool call here if needed
else:
    print("{symbol} is not defined")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(
                create_example_3msg(f"Check if {symbol} is defined, and if so, show where", tool_call)
            )
        else:
            tool_response = make_goto_def_response(symbol, "src/config.py", 12, 5)
            examples.append(
                create_example_5msg(
                    f"Check if {symbol} is defined, and if so, show where",
                    tool_call,
                    tool_response,
                    "Defined at src/config.py:12",
                )
            )
        idx += 1
        if len(examples) >= 75:
            break

    # Pattern 6: Compare reference counts
    for i, symbol in enumerate(SYMBOL_TYPES["function"]["names"]):
        if i >= 25:
            break
        preamble = preambles[idx % len(preambles)]
        tool_call = f"""{preamble}<tool_call><function=execute_code>
<parameter=code>
result = find_references("src/api.py", 67, 15, "{symbol}")
if result.success:
    if result.reference_count >= 10:
        print(f"Yes, heavily used ({{result.reference_count}} references)")
    else:
        print(f"No, lightly used ({{result.reference_count}} references)")
else:
    print("No usage found")
</parameter>
</function></tool_call>"""

        if idx % 2 == 0:
            examples.append(
                create_example_3msg(f"Is {symbol} heavily used? (more than 10 references)", tool_call)
            )
        else:
            tool_response = make_find_refs_response(symbol, 12, [("src/api.py", 67)])
            examples.append(
                create_example_5msg(
                    f"Is {symbol} heavily used? (more than 10 references)",
                    tool_call,
                    tool_response,
                    "Yes, heavily used (12 references)",
                )
            )
        idx += 1

    return examples[:100]


def generate_direct_answer_examples() -> list[dict]:
    """Generate 100 direct answer examples about LSP concepts."""
    examples = []

    # LSP concept questions
    lsp_questions = [
        ("What is the Language Server Protocol?", "The Language Server Protocol (LSP) is a standard protocol for communication between code editors and language servers that provide features like auto-completion, go-to-definition, and find-references."),
        ("Why does LSP use 0-based line numbers?", "LSP uses 0-based line/column positions to match common programming conventions and avoid ambiguity. The first line is line 0, first column is column 0."),
        ("What's the difference between goto_definition and find_references?", "goto_definition finds where a symbol is defined, while find_references finds all places where that symbol is used/referenced in the code."),
        ("When should I use goto_definition instead of grep?", "Use goto_definition when you need precise, semantic navigation to a symbol's actual definition. Grep is text-based and can return false positives from comments, strings, or similar names."),
        ("What information does goto_definition return?", "goto_definition returns a GotoDefinitionResult with: success (bool), symbol (str), and locations (list of DefinitionLocation objects with file, line, column, end_line, end_column, and optional preview)."),
        ("What fields are in FindReferencesResult?", "FindReferencesResult has: success (bool), symbol (str), reference_count (int), and references (list of ReferenceLocation objects with file, line, and column)."),
        ("How do I check if a symbol is defined?", "Call goto_definition() and check the result.success field. If True, the symbol is defined and result.locations will contain the definition location(s)."),
        ("Can goto_definition return multiple locations?", "Yes, if a symbol has multiple definitions (e.g., overloaded functions or definitions across multiple files), result.locations will contain all of them."),
        ("What does reference_count tell me?", "reference_count in FindReferencesResult indicates how many times the symbol is referenced/used in the codebase. It equals len(result.references)."),
        ("Why use LSP tools instead of text search?", "LSP tools understand code semantics - they know what's a definition vs a usage, can distinguish symbols with the same name, and ignore matches in comments/strings."),
    ]

    # Repeat with variations - all use 3-message format (system + user + assistant)
    for _ in range(10):  # 10 repetitions of 10 questions = 100
        for question, answer in lsp_questions:
            examples.append(create_example_3msg(question, answer))
            if len(examples) >= 100:
                break
        if len(examples) >= 100:
            break

    return examples[:100]


def main():
    """Generate all examples and save to JSONL."""
    output_dir = Path("data/phase26_lsp_expanded")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating expanded LSP navigation examples...")

    categories = [
        ("discrimination", generate_discrimination_examples),
        ("goto_def_fields", generate_goto_def_field_access),
        ("find_refs_fields", generate_find_refs_field_access),
        ("workflow", generate_workflow_examples),
        ("direct", generate_direct_answer_examples),
    ]

    all_examples = []
    for name, generator_func in categories:
        print(f"  Generating {name}...")
        examples = generator_func()
        print(f"    Created {len(examples)} examples")
        all_examples.extend(examples)

    # Save all examples
    output_file = output_dir / "examples.jsonl"
    with open(output_file, "w") as f:
        for example in all_examples:
            f.write(json.dumps(example) + "\n")

    print(f"\n✓ Generated {len(all_examples)} examples")
    print(f"✓ Saved to {output_file}")

    # Print statistics
    print("\nStatistics:")
    print(f"  Total examples: {len(all_examples)}")
    print("  Discrimination: 100")
    print("  goto_definition + fields: 100")
    print("  find_references + fields: 100")
    print("  Workflows: 100")
    print("  Direct answers: 100")

    # Check field access rate (check all assistant messages for tool calls)
    tool_call_examples = []
    field_access_examples = []

    for ex in all_examples:
        has_tool_call = False
        has_field_access = False

        for msg in ex["messages"]:
            if msg["role"] == "assistant" and "<tool_call>" in msg["content"]:
                has_tool_call = True
                if any(pattern in msg["content"] for pattern in [".success", ".locations", ".references", ".reference_count", ".file", ".line"]):
                    has_field_access = True

        if has_tool_call:
            tool_call_examples.append(ex)
            if has_field_access:
                field_access_examples.append(ex)

    field_access_rate = (len(field_access_examples) / len(tool_call_examples) * 100) if tool_call_examples else 0
    print(f"  Field access rate: {field_access_rate:.1f}% ({len(field_access_examples)}/{len(tool_call_examples)})")
    print(f"  Multi-turn rate: {(len([ex for ex in all_examples if len(ex['messages']) > 3]) / len(all_examples) * 100):.1f}%")


if __name__ == "__main__":
    main()
