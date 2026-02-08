# Architecture: Init Command

## Component Structure

```
src/punie/cli.py
├── resolve_punie_command() -> tuple[str, list[str]]
├── generate_acp_config(command, args, env) -> dict
├── merge_acp_config(existing, punie_entry) -> dict
└── @app.command() def init(...)
```

## Pure Functions (Testable)

### `resolve_punie_command() -> tuple[str, list[str]]`

**Purpose:** Detect how to invoke Punie

**Logic:**
1. Try `shutil.which("punie")`
2. If found → `(path, [])`
3. If not found → `("uvx", ["punie"])`

**Returns:** `(command: str, args: list[str])`

**Examples:**
```python
# System install
("/usr/local/bin/punie", [])

# uvx fallback
("uvx", ["punie"])
```

### `generate_acp_config(command: str, args: list[str], env: dict[str, str]) -> dict`

**Purpose:** Build ACP JSON structure for Punie

**Logic:**
1. Construct agent_servers.punie entry
2. Merge command + args (e.g., uvx invocation)
3. Add env dict if provided
4. Include default_mcp_settings

**Returns:** Complete acp.json dict

**Example:**
```python
{
    "default_mcp_settings": {
        "use_idea_mcp": True,
        "use_custom_mcp": True
    },
    "agent_servers": {
        "punie": {
            "command": "/usr/local/bin/punie",
            "args": [],
            "env": {"PUNIE_MODEL": "claude-sonnet-4-5-20250929"}
        }
    }
}
```

### `merge_acp_config(existing: dict, punie_entry: dict) -> dict`

**Purpose:** Preserve other agents when updating config

**Logic:**
1. Start with existing config
2. Ensure `agent_servers` key exists
3. Update/add `punie` entry
4. Add `default_mcp_settings` if missing
5. Return new dict (no mutation)

**Returns:** Merged config dict

## Typer Command

### `@app.command() def init(...)`

**Parameters:**
- `--model` (optional): Pre-set PUNIE_MODEL in env
- `--output` (optional): Override path (default `~/.jetbrains/acp.json`)

**Flow:**
1. Resolve Punie command
2. Build env dict from `--model` flag
3. Generate base config
4. Load existing config if present
5. Merge configs
6. Write to output path
7. Print confirmation message

**Output:**
```
✓ Created ~/.jetbrains/acp.json
  Command: /usr/local/bin/punie
  Model: claude-sonnet-4-5-20250929 (from --model)
```

## File Format

**~/.jetbrains/acp.json:**
```json
{
  "default_mcp_settings": {
    "use_idea_mcp": true,
    "use_custom_mcp": true
  },
  "agent_servers": {
    "punie": {
      "command": "/path/to/punie",
      "args": [],
      "env": {}
    },
    "other-agent": {
      "command": "/path/to/other",
      "args": ["--flag"],
      "env": {"KEY": "value"}
    }
  }
}
```

## Dependencies

- `json` (stdlib): Parse/generate JSON
- `shutil` (stdlib): `which()` for executable detection
- `pathlib` (stdlib): Path manipulation
- `typer` (existing): CLI framework
