# Troubleshooting Tool Calling with Local MLX Models

This guide helps diagnose and fix issues when the MLX model outputs raw JSON instead of calling tools properly.

## Symptoms

When you ask the agent to perform a task (e.g., "how many Python files are in the project"), the model responds with raw JSON like:

```json
{
  "name": "read_file",
  "arguments": {
    "path": "path/to/your/project"
  }
}
```

Instead of actually calling the tool.

## Root Causes

1. **Chat template doesn't support tools** - The tokenizer's chat template may not properly format tool calling instructions
2. **Model not trained for tool calling** - Some model variants (especially heavily quantized) may lose tool calling ability
3. **Wrong tool format** - The model expects a different tool calling format than what we're providing
4. **Tools not being passed** - The toolset may be empty due to configuration issues

## Diagnostic Steps

### Step 1: Check PyCharm Logs

Look for these diagnostic messages in PyCharm's agent logs:

```
=== MLX Generation Diagnostics ===
Model: mlx-community/Qwen2.5-Coder-7B-Instruct-4bit
Number of messages: 2
Number of tools: 7
Tool names: ['read_file', 'write_file', 'run_command', ...]
```

**If you see `Number of tools: 0`**, the problem is with tool discovery, not the model. See the "Empty Toolset" troubleshooting section.

### Step 2: Check Chat Template Support

Look for this message:

```
✓ Chat template appears to support Qwen-style <tool_call> tags
```

**If you see a warning instead:**
```
⚠️  Tool calling may not work: Chat template does not contain tool/function markers
```

This means the tokenizer doesn't have the right chat template. Try:
1. Use a non-quantized model
2. Update to the latest mlx-lm version
3. Try a different model variant

### Step 3: Check Raw Model Output

Look for:
```
Raw model output length: 150 chars
Raw output:
================================================================================
{
  "name": "read_file",
  "arguments": {"path": "..."}
}
================================================================================
```

**If you see raw JSON without `<tool_call>` tags**, the model doesn't understand the expected format.

Then check for:
```
⚠️  Model output looks like tool call JSON but missing <tool_call> tags!
    This suggests the model doesn't understand the expected format.
```

### Step 4: Check Parsed Tool Calls

Look for:
```
Parsing output for tool calls...
Parsed result: 0 tool calls, 150 chars of text
```

**If "0 tool calls" but the raw output contains JSON**, the model is outputting the wrong format.

## Solutions

### Solution 1: Try a Non-Quantized Model

Quantization (especially 4-bit) can affect the model's ability to follow tool calling instructions precisely.

```bash
# Download non-quantized version
punie download-model mlx-community/Qwen2.5-Coder-7B-Instruct

# Configure to use it
uv run punie init --model local:mlx-community/Qwen2.5-Coder-7B-Instruct

# Restart PyCharm's agent connection
```

### Solution 2: Try a Larger Model

The 7B model may struggle with tool calling. Try the 14B model:

```bash
punie download-model mlx-community/Qwen2.5-Coder-14B-Instruct-4bit
uv run punie init --model local:mlx-community/Qwen2.5-Coder-14B-Instruct-4bit
```

### Solution 3: Update mlx-lm

Newer versions may have improved chat templates:

```bash
uv pip install --upgrade mlx-lm
```

### Solution 4: Check Model Memory

If the model is running out of memory, it may produce degraded output:

```bash
# Check available memory
vm_stat

# Try a smaller model
punie download-model mlx-community/Qwen2.5-Coder-3B-Instruct-4bit
uv run punie init --model local:mlx-community/Qwen2.5-Coder-3B-Instruct-4bit
```

### Solution 5: Use Cloud Models (Temporary Workaround)

If local models continue to have issues, use a cloud model while debugging:

```bash
# Use OpenAI
export OPENAI_API_KEY="your-key"
uv run punie init --model openai:gpt-4o

# Or use Anthropic
export ANTHROPIC_API_KEY="your-key"
uv run punie init --model anthropic:claude-3-5-sonnet-20241022
```

## Expected Tool Call Format

The MLX models should output tool calls like this:

```
I'll help you count the Python files. Let me search the project.

<tool_call>{"name": "run_command", "arguments": {"command": "find", "args": [".", "-name", "*.py", "-type", "f"]}}</tool_call>
```

The `<tool_call>` tags are critical - without them, the parser cannot extract the tool calls.

## Verifying the Fix

After applying a solution, test with a simple query:

```
How many Python files are in the project?
```

You should see:
1. The agent calls `run_command` with `find` command
2. Gets back a list of files
3. Responds with the count

If you still see raw JSON output, try the next solution.

## Reporting Issues

If none of these solutions work, report an issue with:

1. The full diagnostic output from PyCharm logs
2. The model name and variant you're using
3. Your mlx-lm version (`uv pip show mlx-lm`)
4. Your system RAM and whether the model is swapping to disk
5. The exact query that's failing
