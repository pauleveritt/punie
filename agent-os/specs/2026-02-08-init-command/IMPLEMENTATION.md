# Implementation Plan: Init Command

## Changes to `src/punie/cli.py`

### Imports to Add

```python
import json
import shutil
from pathlib import Path
```

### Pure Functions

```python
def resolve_punie_command() -> tuple[str, list[str]]:
    """
    Detect how to invoke Punie executable.

    Returns:
        (command, args) tuple:
        - If punie on PATH: ("/path/to/punie", [])
        - Otherwise: ("uvx", ["punie"])
    """
    punie_path = shutil.which("punie")
    if punie_path:
        return (punie_path, [])
    return ("uvx", ["punie"])


def generate_acp_config(
    command: str,
    args: list[str],
    env: dict[str, str]
) -> dict:
    """
    Generate JetBrains ACP configuration for Punie.

    Args:
        command: Executable path or "uvx"
        args: Arguments list (e.g., ["punie"] for uvx)
        env: Environment variables dict

    Returns:
        Complete acp.json structure
    """
    return {
        "default_mcp_settings": {
            "use_idea_mcp": True,
            "use_custom_mcp": True,
        },
        "agent_servers": {
            "punie": {
                "command": command,
                "args": args,
                "env": env,
            }
        },
    }


def merge_acp_config(existing: dict, punie_config: dict) -> dict:
    """
    Merge Punie config into existing ACP config.

    Preserves other agents and settings. Does not mutate inputs.

    Args:
        existing: Current acp.json content
        punie_config: New Punie configuration

    Returns:
        Merged configuration dict
    """
    import copy
    merged = copy.deepcopy(existing)

    # Ensure agent_servers exists
    if "agent_servers" not in merged:
        merged["agent_servers"] = {}

    # Update/add punie entry
    merged["agent_servers"]["punie"] = punie_config["agent_servers"]["punie"]

    # Add default_mcp_settings if missing
    if "default_mcp_settings" not in merged:
        merged["default_mcp_settings"] = punie_config["default_mcp_settings"]

    return merged
```

### Typer Command

```python
@app.command()
def init(
    model: str | None = typer.Option(
        None,
        "--model",
        help="Pre-configure PUNIE_MODEL environment variable",
    ),
    output: Path = typer.Option(
        Path.home() / ".jetbrains" / "acp.json",
        "--output",
        help="Output path for acp.json",
    ),
) -> None:
    """
    Generate JetBrains ACP configuration for Punie.

    Creates ~/.jetbrains/acp.json to enable PyCharm agent discovery.
    Merges with existing config to preserve other agents.
    """
    # Resolve Punie executable
    command, args = resolve_punie_command()

    # Build environment
    env = {}
    if model:
        env["PUNIE_MODEL"] = model

    # Generate base config
    punie_config = generate_acp_config(command, args, env)

    # Merge with existing if present
    if output.exists():
        try:
            existing = json.loads(output.read_text())
            final_config = merge_acp_config(existing, punie_config)
        except (json.JSONDecodeError, KeyError) as e:
            typer.secho(
                f"Warning: Could not parse existing {output}, overwriting",
                fg=typer.colors.YELLOW,
            )
            final_config = punie_config
    else:
        final_config = punie_config

    # Write config
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(final_config, indent=2) + "\n")

    # User feedback
    typer.secho(f"✓ Created {output}", fg=typer.colors.GREEN)
    typer.echo(f"  Command: {command}")
    if args:
        typer.echo(f"  Args: {' '.join(args)}")
    if env:
        for key, value in env.items():
            typer.echo(f"  {key}: {value}")
```

## Example File

**`examples/12_init_config.py`:**

```python
"""Example: ACP config generation for PyCharm integration.

Demonstrates how `punie init` detects the Punie executable
and generates ~/.jetbrains/acp.json for agent discovery.
"""

import json
from punie.cli import resolve_punie_command, generate_acp_config

def main():
    print("=== Detecting Punie executable ===")
    command, args = resolve_punie_command()
    print(f"Command: {command}")
    print(f"Args: {args}")

    print("\n=== Generating basic config ===")
    config = generate_acp_config(command, args, {})
    print(json.dumps(config, indent=2))

    print("\n=== Config with model pre-set ===")
    config_with_model = generate_acp_config(
        command,
        args,
        {"PUNIE_MODEL": "claude-sonnet-4-5-20250929"}
    )
    print(json.dumps(config_with_model, indent=2))

if __name__ == "__main__":
    main()
```

## Manual Testing

```bash
# Generate default config
uv run punie init --output /tmp/acp.json
cat /tmp/acp.json

# With model flag
uv run punie init --model claude-opus-4 --output /tmp/acp.json

# Help text
uv run punie init --help

# Main help shows init
uv run punie --help
```

## Files Modified

- `src/punie/cli.py` — add 3 functions + 1 command
- `tests/test_cli.py` — add 13 tests
- `examples/12_init_config.py` — new example

## Dependencies

None — uses stdlib only (json, shutil, pathlib)
