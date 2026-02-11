# Integrating an LSP into an Agent Tool Loop

## Overview

Integrating a Language Server Protocol (LSP) server into an AI agent's tool loop gives the agent access to
compiler-grade code intelligence — diagnostics, completions, go-to-definition, references, refactoring, and more —
enabling far more accurate and grounded code manipulation than pure LLM generation alone.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Agent Loop                         │
│                                                      │
│  ┌──────────┐    ┌───────────┐    ┌──────────────┐  │
│  │   LLM    │◄──►│Tool Router│◄──►│ LSP Client   │  │
│  │ (Planner)│    │           │    │  (Tool Impl) │  │
│  └──────────┘    └───────────┘    └──────┬───────┘  │
│                                          │           │
│                                   JSON-RPC / stdio   │
│                                          │           │
│                                   ┌──────▼───────┐   │
│                                   │  LSP Server  │   │
│                                   │ (clangd, rust│   │
│                                   │  -analyzer,  │   │
│                                   │  pyright...) │   │
│                                   └──────────────┘   │
└─────────────────────────────────────────────────────┘
```

---

## Key Research & Prior Art

### 1. **Academic / Papers**

- **"Language Agent Tree Search" (LATS, 2023)** — Uses environment feedback (including compiler/test output) in an
  MCTS-style agent loop. LSP diagnostics fit naturally as a feedback signal.
- **"RepairAgent" (2024)** — Automated program repair agent that uses tools including fault localization; LSP
  diagnostics serve a similar role.
- **"SWE-agent" (Princeton, 2024)** — Designs agent-computer interfaces for software engineering. Shows that *what tools
  you expose* to the agent matters as much as the LLM.
- **"CodeAct" (2024)** — Agents that execute code actions; LSP actions (code actions, quick fixes) map directly.

### 2. **Open-Source Implementations**

| Project              | Approach                                                                                      |
|----------------------|-----------------------------------------------------------------------------------------------|
| **Aider**            | Runs linters/compilers in loop, uses output to self-correct. Not full LSP but same principle. |
| **Continue.dev**     | VS Code extension with LSP access; exposes @codebase context to LLM using LSP indexes.        |
| **Cursor**           | Proprietary; uses LSP for go-to-definition, references to build context for LLM.              |
| **Sourcegraph Cody** | Uses SCIP (LSP-adjacent index) for precise code graph context.                                |
| **lsp-ai**           | An LSP server *itself* that adds AI completions, wrapping another LSP.                        |
| **mentat**           | Code editing agent that can use LSP for context gathering.                                    |
| **Cline / Roo Code** | VS Code agent that accesses workspace diagnostics via the editor's LSP.                       |

### 3. **Key Blog Posts / Discussions**

- Sourcegraph's writing on **"precise code intelligence for AI"** — argues embeddings alone are insufficient;
  symbol-level graph data is critical.
- Cursor's approach: LSP for **"go to definition" chains** to expand context windows intelligently.

---

## LSP Capabilities as Agent Tools

### Tier 1: High-Value Tools (Expose First)

```python
# Tool definitions for the agent
tools = [
    {
        "name": "get_diagnostics",
        "description": "Get compiler errors, warnings, and lints for a file",
        "params": {"file_path": "string"}
    },
    {
        "name": "go_to_definition",
        "description": "Find the definition of a symbol at a given position",
        "params": {"file_path": "string", "line": "int", "character": "int"}
    },
    {
        "name": "find_references",
        "description": "Find all references to a symbol",
        "params": {"file_path": "string", "line": "int", "character": "int"}
    },
    {
        "name": "get_hover_info",
        "description": "Get type info and documentation for a symbol",
        "params": {"file_path": "string", "line": "int", "character": "int"}
    },
    {
        "name": "get_code_actions",
        "description": "Get available quick-fixes and refactorings",
        "params": {"file_path": "string", "range": "Range"}
    },
    {
        "name": "apply_code_action",
        "description": "Apply a specific code action / quick fix",
        "params": {"action_id": "string"}
    },
]
```

### Tier 2: Context-Building Tools

```python
additional_tools = [
    "document_symbols",  # Outline of a file
    "workspace_symbols",  # Search symbols across project
    "completion",  # Get valid completions at a point
    "signature_help",  # Function signature info
    "rename_symbol",  # Safe rename across project
    "call_hierarchy",  # Who calls what
    "type_hierarchy",  # Inheritance chains
    "folding_ranges",  # Understand code structure
    "semantic_tokens",  # Rich token classification
]
```

---

## Implementation Guide

### Step 1: LSP Client Lifecycle Management

```python
import subprocess
import json


class LSPClient:
    def __init__(self, cmd: list[str], root_uri: str):
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.request_id = 0
        self._initialize(root_uri)

    def _send(self, method: str, params: dict) -> dict:
        self.request_id += 1
        message = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params,
        }
        body = json.dumps(message)
        header = f"Content-Length: {len(body)}\r\n\r\n"
        self.process.stdin.write(header.encode() + body.encode())
        self.process.stdin.flush()
        return self._receive()

    def _receive(self) -> dict:
        # Read Content-Length header
        header = self.process.stdout.readline().decode()
        content_length = int(header.split(": ")[1])
        self.process.stdout.readline()  # empty line
        body = self.process.stdout.read(content_length).decode()
        return json.loads(body)

    def _initialize(self, root_uri: str):
        self._send("initialize", {
            "processId": None,
            "rootUri": root_uri,
            "capabilities": {
                "textDocument": {
                    "publishDiagnostics": {},
                    "definition": {},
                    "references": {},
                    "hover": {},
                    "codeAction": {},
                    "completion": {},
                }
            }
        })
        self._send("initialized", {})

    def did_open(self, uri: str, language_id: str, text: str):
        self._send("textDocument/didOpen", {
            "textDocument": {
                "uri": uri,
                "languageId": language_id,
                "version": 1,
                "text": text,
            }
        })

    def did_change(self, uri: str, version: int, text: str):
        self._send("textDocument/didChange", {
            "textDocument": {"uri": uri, "version": version},
            "contentChanges": [{"text": text}],
        })

    def get_diagnostics(self, uri: str) -> list:
        # Diagnostics come via notifications — need async handling
        # Some servers support textDocument/diagnostic (pull model, LSP 3.17+)
        return self._send("textDocument/diagnostic", {
            "textDocument": {"uri": uri}
        })

    def goto_definition(self, uri: str, line: int, char: int) -> dict:
        return self._send("textDocument/definition", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": char},
        })

    def find_references(self, uri: str, line: int, char: int) -> dict:
        return self._send("textDocument/references", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": char},
            "context": {"includeDeclaration": True},
        })

    def hover(self, uri: str, line: int, char: int) -> dict:
        return self._send("textDocument/hover", {
            "textDocument": {"uri": uri},
            "position": {"line": line, "character": char},
        })
```

> **Note**: Production implementations should use async I/O (e.g., `pygls`, `asyncio`) and handle notifications,
> progress, and multiplexed responses properly.

### Step 2: Wrapping LSP as Agent Tools

```python
class LSPTools:
    """Wraps LSP client methods as callable tools for the agent."""

    def __init__(self, lsp_client: LSPClient, workspace_root: str):
        self.lsp = lsp_client
        self.root = workspace_root
        self.open_files: dict[str, int] = {}  # uri -> version

    def _ensure_open(self, file_path: str) -> str:
        uri = f"file://{file_path}"
        if uri not in self.open_files:
            with open(file_path) as f:
                text = f.read()
            lang = self._detect_language(file_path)
            self.lsp.did_open(uri, lang, text)
            self.open_files[uri] = 1
        return uri

    def _sync_file(self, file_path: str):
        """Call after the agent edits a file."""
        uri = f"file://{file_path}"
        with open(file_path) as f:
            text = f.read()
        version = self.open_files.get(uri, 0) + 1
        self.open_files[uri] = version
        self.lsp.did_change(uri, version, text)

    def get_diagnostics(self, file_path: str) -> str:
        """Returns formatted diagnostics for agent consumption."""
        uri = self._ensure_open(file_path)
        result = self.lsp.get_diagnostics(uri)
        diagnostics = result.get("result", {}).get("items", [])
        if not diagnostics:
            return "No errors or warnings."

        lines = []
        for d in diagnostics:
            severity = {1: "ERROR", 2: "WARNING", 3: "INFO", 4: "HINT"}
            sev = severity.get(d.get("severity", 3), "INFO")
            pos = d["range"]["start"]
            lines.append(
                f"[{sev}] Line {pos['line'] + 1}: {d['message']}"
            )
        return "\n".join(lines)

    def go_to_definition(self, file_path: str, line: int, character: int) -> str:
        """Returns the definition location and surrounding code."""
        uri = self._ensure_open(file_path)
        result = self.lsp.goto_definition(uri, line - 1, character)
        locations = result.get("result", [])
        if not locations:
            return "No definition found."

        # Handle LocationLink vs Location
        loc = locations[0] if isinstance(locations, list) else locations
        target_uri = loc.get("targetUri", loc.get("uri", ""))
        target_range = loc.get("targetRange", loc.get("range", {}))

        # Read and return surrounding code
        target_path = target_uri.replace("file://", "")
        with open(target_path) as f:
            lines = f.readlines()

        start = max(0, target_range["start"]["line"] - 5)
        end = min(len(lines), target_range["end"]["line"] + 10)

        snippet = "".join(
            f"{i + 1:4d} | {lines[i]}" for i in range(start, end)
        )
        return f"Definition at {target_path}:{target_range['start']['line'] + 1}\n\n{snippet}"
```

### Step 3: The Agent Loop

```python
import openai

SYSTEM_PROMPT = """You are a coding agent with access to LSP tools.

WORKFLOW:
1. Before editing code, use get_diagnostics to understand current state
2. After editing code, ALWAYS use get_diagnostics to verify your changes compile
3. Use go_to_definition and find_references to understand code before modifying it
4. Use hover to check types when uncertain
5. If diagnostics show errors after your edit, fix them before moving on

IMPORTANT: The LSP gives you ground-truth compiler feedback. Trust it over your training data.
"""


def agent_loop(task: str, tools: LSPTools, max_iterations: int = 20):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": task},
    ]

    tool_definitions = [
        {
            "type": "function",
            "function": {
                "name": "get_diagnostics",
                "description": "Get compiler errors/warnings for a file. Call after every edit.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"}
                    },
                    "required": ["file_path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "go_to_definition",
                "description": "Jump to the definition of a symbol. Returns the code at the definition site.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "line": {"type": "integer"},
                        "character": {"type": "integer"}
                    },
                    "required": ["file_path", "line", "character"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "find_references",
                "description": "Find all usages of a symbol across the project.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "line": {"type": "integer"},
                        "character": {"type": "integer"}
                    },
                    "required": ["file_path", "line", "character"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "edit_file",
                "description": "Edit a file. After calling this, diagnostics will be re-checked.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string"},
                        "new_content": {"type": "string"}
                    },
                    "required": ["file_path", "new_content"]
                }
            }
        },
    ]

    for i in range(max_iterations):
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tool_definitions,
        )

        msg = response.choices[0].message
        messages.append(msg)

        if msg.tool_calls is None:
            # Agent is done
            return msg.content

        for tool_call in msg.tool_calls:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            if name == "get_diagnostics":
                result = tools.get_diagnostics(args["file_path"])
            elif name == "go_to_definition":
                result = tools.go_to_definition(
                    args["file_path"], args["line"], args["character"]
                )
            elif name == "find_references":
                result = tools.find_references(
                    args["file_path"], args["line"], args["character"]
                )
            elif name == "edit_file":
                with open(args["file_path"], "w") as f:
                    f.write(args["new_content"])
                tools._sync_file(args["file_path"])
                # Auto-check diagnostics after edit
                diag = tools.get_diagnostics(args["file_path"])
                result = f"File written. Diagnostics:\n{diag}"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })

    return "Max iterations reached."
```

---

## Design Patterns & Best Practices

### 1. **Diagnostic Feedback Loop** (Most Important)

```
Agent edits file → didChange notification → LSP re-analyzes → 
Agent reads diagnostics → Agent fixes errors → repeat until clean
```

This is the single highest-value pattern. It gives the agent a "compiler in the loop."

### 2. **Context Expansion via Definition Chasing**

```
Agent sees unknown function call → go_to_definition → 
reads definition + docstring → now has accurate type/behavior info → 
generates correct usage
```

This replaces RAG for code — it's *precise* rather than *approximate*.

### 3. **Reference-Aware Refactoring**

```
Agent wants to rename/modify function → find_references → 
understands all call sites → modifies all consistently → 
diagnostics confirm no breakage
```

### 4. **Type-Guided Generation**

```
Agent uses hover/completion to discover:
- What methods are available on an object
- What arguments a function expects
- What type a variable actually is (not what LLM guesses)
```

### 5. **Auto-Diagnostic After Every Edit**

Always automatically run diagnostics after file modifications. Don't wait for the agent to remember to check.

---

## Challenges & Solutions

| Challenge                                                              | Solution                                                                                                                   |
|------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| **LSP startup is slow** (esp. rust-analyzer, clangd on large projects) | Pre-warm the server; keep it running across agent invocations; use `workspace/didChangeWatchedFiles` sparingly             |
| **Diagnostics are async** (push model via `publishDiagnostics`)        | Use pull diagnostics (3.17+), or implement notification listener with timeout, or wait/poll                                |
| **Position tracking after edits**                                      | Re-sync the full document after each edit; use `textDocument/didChange` with full content (not incremental) for simplicity |
| **Large diagnostic output**                                            | Summarize/filter: show only errors first, then warnings. Truncate to stay within context window                            |
| **Multi-file consistency**                                             | Track which files are open; after cross-file edits, re-check diagnostics on all affected files                             |
| **Agent misuses tools**                                                | Strong system prompt instructions; auto-inject diagnostics; limit tool set to what's needed                                |
| **LSP server crashes**                                                 | Implement restart logic with exponential backoff; re-open tracked files                                                    |
| **Position encoding**                                                  | Be explicit about UTF-16 offsets (LSP default) vs UTF-8; many bugs here                                                    |

---

## Advanced Patterns

### Semantic Code Graph as Context

```python
def build_context_for_function(tools: LSPTools, file: str, line: int, char: int):
    """Build a rich context window by chasing the dependency graph."""
    context_parts = []

    # 1. Get the function definition
    definition = tools.go_to_definition(file, line, char)
    context_parts.append(f"## Definition\n{definition}")

    # 2. Get type info
    hover = tools.hover(file, line, char)
    context_parts.append(f"## Type Info\n{hover}")

    # 3. Find all references (usage examples)
    refs = tools.find_references(file, line, char)
    context_parts.append(f"## Usage Examples\n{refs}")

    # 4. Get call hierarchy (what does this function call?)
    # callees = tools.outgoing_calls(file, line, char)

    return "\n\n".join(context_parts)
```

### LSP-Augmented RAG

Instead of naive embedding search:

1. Use `workspace/symbol` to find relevant symbols by name
2. Use `textDocument/documentSymbol` for file outlines
3. Chase definitions/references for precise expansion
4. Fall back to embedding search only for natural language concepts

### Incremental Verification Pipeline

```python
def verified_edit_loop(agent, tools, file_path, edit_description):
    """Keep editing until diagnostics are clean."""
    for attempt in range(5):
        # Agent makes edit
        agent.edit(file_path, edit_description)
        tools._sync_file(file_path)

        # Check diagnostics
        diagnostics = tools.get_diagnostics(file_path)

        if "ERROR" not in diagnostics:
            return True  # Clean!

        # Feed errors back to agent
        edit_description = f"""
        Your previous edit introduced errors:
        {diagnostics}
        
        Please fix these errors.
        """

    return False  # Failed after max attempts
```

---

## Recommended Libraries

| Language   | LSP Client Library                                        |
|------------|-----------------------------------------------------------|
| Python     | `pygls`, `lsprotocol`, `pylsp-client`                     |
| TypeScript | `vscode-languageclient`, `vscode-languageserver-protocol` |
| Rust       | `tower-lsp`, `lsp-types`                                  |
| Go         | `go.lsp.dev/protocol`                                     |

For the LSP servers themselves:

- **Python**: `pyright`, `pylsp`, `ruff-lsp`
- **TypeScript/JS**: `typescript-language-server`, `vtsls`
- **Rust**: `rust-analyzer`
- **C/C++**: `clangd`
- **General**: `tree-sitter` (not LSP but useful for structural parsing)

---

## Evaluation / Metrics

When benchmarking LSP-augmented agents vs. vanilla:

1. **SWE-bench** — Track pass@1 improvement with LSP tools
2. **Error rate after edits** — How often does first edit compile cleanly?
3. **Context relevance** — Are the right files/symbols being retrieved? (Compare vs. embedding search)
4. **Tool call efficiency** — How many LSP calls per task? (Cost/latency)
5. **Hallucination rate** — Does the agent invent non-existent APIs less often?

---

## TL;DR

The highest-impact integration points are:

1. **`publishDiagnostics` / pull diagnostics** → Compiler-in-the-loop after every edit
2. **`textDocument/definition`** → Precise context expansion (replaces fuzzy RAG for code)
3. **`textDocument/references`** → Safe cross-file modifications
4. **`textDocument/hover`** → Type grounding to prevent hallucination
5. **`textDocument/codeAction`** → Let the LSP server fix what it can automatically

The agent should **never** submit a final answer if diagnostics show errors it hasn't attempted to resolve.