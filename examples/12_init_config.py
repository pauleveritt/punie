"""Example: ACP config generation for PyCharm integration.

Demonstrates how `punie init` detects the Punie executable
and generates ~/.jetbrains/acp.json for agent discovery.
"""

import json

from punie.cli import generate_acp_config, resolve_punie_command


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
        command, args, {"PUNIE_MODEL": "claude-sonnet-4-5-20250929"}
    )
    print(json.dumps(config_with_model, indent=2))


if __name__ == "__main__":
    main()
