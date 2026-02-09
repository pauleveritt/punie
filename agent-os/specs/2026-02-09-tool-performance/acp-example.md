# Using PUNIE_PERF with acp.json

## Example Configuration

To enable performance reporting in ACP mode (PyCharm), add `PUNIE_PERF=1` to the environment variables in your `~/.jetbrains/acp.json`:

```json
{
  "default_mcp_settings": {
    "use_idea_mcp": true,
    "use_custom_mcp": true
  },
  "agent_servers": {
    "punie": {
      "command": "punie",
      "args": [],
      "env": {
        "PUNIE_MODEL": "local",
        "PUNIE_PERF": "1"
      }
    }
  }
}
```

## Usage

With `PUNIE_PERF=1` set in `acp.json`, every prompt execution will:

1. Record timing for all tool calls
2. Generate an HTML performance report
3. Save to `punie-perf-{timestamp}.html` in the workspace directory
4. Print the report path in the agent response

## Disabling

To disable performance reporting:

- Remove the `PUNIE_PERF` entry from `env`, OR
- Set `"PUNIE_PERF": "0"`

## CLI Override

The `--perf` flag on CLI always takes precedence:

```bash
# Force enable even if PUNIE_PERF=0
punie ask "Count files" --perf

# Works without env var
punie ask "Count files" --perf
```

## Report Contents

Each HTML report includes:

- **Summary**: Model name, backend (local/ide), total duration, tool call count
- **Timing Breakdown**: Visual bar showing tool execution vs. model think time
- **Tool Calls Table**: Detailed timing for each tool call, ordered by execution
- **Timestamps**: ISO format for cross-run comparison

## Use Cases

- **Development**: Profile tool performance during local testing
- **Production**: Monitor tool latency in IDE workflow
- **Optimization**: Identify slow tools for performance tuning
- **Comparison**: Compare local vs. IDE backend performance
