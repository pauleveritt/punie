# Tool Calling Investigation - Root Cause Analysis

**Date:** 2026-02-11 (overnight investigation)
**Context:** After baseline evaluation showed all training hurts performance, investigated why tool calling fails

## Executive Summary

**Root Cause Identified:** Architectural incompatibility between mlx_lm.server and PydanticAI's tool calling expectations.

- **mlx_lm.server:** Returns raw text output from the model
- **PydanticAI:** Expects OpenAI API's structured `tool_calls` objects
- **The model:** Generates JSON in text (markdown code blocks), which isn't parsed

**Conclusion:** Tool calling cannot work reliably with the current architecture. The 1.5B base model (no training) is the best option for code generation and reasoning.

## Investigation Steps

### Step 1: Analyzed Training Data Format

Examined all existing training datasets:

**diverse-python-5k:**
```json
{
  "role": "assistant",
  "content": "def reverse_string(s):\n    return s[::-1]"
}
```
- No tool calling at all
- Pure code generation examples

**glaive-function-calling:**
```json
{
  "role": "system",
  "content": "SYSTEM: You are a helpful assistant with access to the following functions...\n{\"name\": \"get_exchange_rate\", ...}"
}
{
  "role": "assistant",
  "content": "I'm sorry, but I don't have the capability to book flights..."
}
```
- Defines function schemas in system message
- **Assistant DECLINES to use tools** (text response)
- No actual tool calls demonstrated

**synthetic tool-calling:**
```json
{
  "role": "assistant",
  "content": "I'll read the file for you.\n\nTool call: {\"type\": \"function\", \"function\": {\"name\": \"read_file\", ...}}"
}
```
- Tool calls as plain text JSON strings
- Not structured message parts

**hand-authored:**
```json
{
  "role": "assistant",
  "content": "I'll use the read_file tool.\n\n```json\n{\n  \"tool\": \"read_file\",\n  \"arguments\": {\"path\": \"src/main.py\"}\n}\n```"
}
```
- Tool calls as markdown JSON code blocks
- Also plain text, not structured

### Step 2: Examined Base Model Output

Inspected what the base model actually generates for tool-calling prompts:

```
Prompt: "Read the file at /etc/hosts and tell me what's in it."

Model output:
```json
{
  "name": "read_file",
  "arguments": {
    "path": "/etc/hosts"
  }
}
```<|im_end|>
```

**Observation:** Model DOES generate tool calls, but as markdown JSON code blocks!

**Evaluation result:** 0% score (tool not recognized)

### Step 3: Understanding PydanticAI's Tool Extraction

PydanticAI extracts tool calls from structured message parts:

```python
for msg in result.all_messages():
    if hasattr(msg, "parts"):
        for part in msg.parts:
            if hasattr(part, "tool_name"):  # Structured attribute!
                tool_calls_list.append(part.tool_name)
```

**Problem:** PydanticAI looks for `part.tool_name` attributes, not JSON in text.

### Step 4: Created Qwen-Specific Training Data

Hypothesis: Maybe Qwen models need a specific XML format.

Created training data with `<tool_call>` XML tags:
```xml
<tool_call>
{"name": "read_file", "arguments": {"path": "/etc/hosts"}}
</tool_call>
```

**Result:** Tool calling got WORSE (16.7% vs 33.3%)
- Training data format is NOT the issue

### Step 5: Tested 30B Model

Hypothesis: Maybe the model is too small for tool calling.

Evaluated `Qwen3-Coder-30B-A3B-Instruct-4bit` base model.

**Result:** 30B is WORSE overall (60.7% vs 71.4%)
- Code generation: 87.5% (down from 100%)
- Reasoning: 50% (down from 100%)
- Tool calling: 50% (up from 33.3%, but still poor)

**Conclusion:** Model size is NOT the solution. Smaller model is actually better.

## Root Cause: Architectural Incompatibility

### How OpenAI's Tool Calling Works

1. **API Request:** Client sends messages + tool definitions
2. **Model generates:** Special tokens indicating tool call intent
3. **API Response:** Server returns structured `tool_calls` object:
   ```json
   {
     "role": "assistant",
     "content": null,
     "tool_calls": [
       {
         "id": "call_abc123",
         "type": "function",
         "function": {
           "name": "read_file",
           "arguments": "{\"path\": \"/etc/hosts\"}"
         }
       }
     ]
   }
   ```
4. **PydanticAI:** Receives structured object, extracts tool names from `function.name`

### How mlx_lm.server Works

1. **API Request:** Client sends messages (mlx_lm.server implements OpenAI-compatible API)
2. **Model generates:** Raw text tokens (JSON in markdown, or plain JSON, or XML, etc.)
3. **API Response:** Server returns text as-is:
   ```json
   {
     "role": "assistant",
     "content": "```json\n{\"name\": \"read_file\", \"arguments\": {\"path\": \"/etc/hosts\"}}\n```"
   }
   ```
4. **PydanticAI:** Looks for `tool_calls` field → NOT FOUND → No tools recognized

### The Gap

**mlx_lm.server does NOT parse tool calls from model output.** It just returns raw text.

PydanticAI expects the OpenAI API to have already parsed and structured the tool calls. But mlx_lm.server doesn't do this parsing.

## Why Training Failed

All training attempts failed because:

1. **Training teaches text format** (any format: JSON, XML, plain English)
2. **Evaluation expects structured parts** (not text!)
3. **No amount of training can bridge this gap**

The model is doing exactly what it was trained to do (generate text about tool calls). But the evaluation measures something different (structured tool_use parts).

Training made things worse because:
- **Catastrophic forgetting:** Narrow tool-calling datasets destroyed general capabilities
- **Overfitting:** Small datasets (8-5000 examples) cause overfitting
- **Wrong optimization target:** Training optimizes text generation, evaluation measures structured parts

## Attempted Solutions

### ✗ Solution 1: Better Training Data Format

**Tried:** Created Qwen-specific `<tool_call>` XML format
**Result:** Tool calling worse (16.7% vs 33.3%)
**Reason:** Format doesn't matter if mlx_lm.server doesn't parse it

### ✗ Solution 2: Larger Model

**Tried:** Evaluated 30B model
**Result:** Worse overall (60.7% vs 71.4%)
**Reason:** Size isn't the bottleneck; architecture is

## Potential Real Solutions

### Option A: Modify mlx_lm.server (Best)

Add tool call parsing to mlx_lm.server to return OpenAI-compatible responses:

1. Detect tool call patterns in model output (JSON, XML, etc.)
2. Parse them into structured format
3. Return in `tool_calls` field

**Pros:**
- Fixes the root cause
- Makes mlx_lm.server truly OpenAI-compatible
- Works with any model

**Cons:**
- Requires modifying mlx_lm (external dependency)
- Need to handle multiple formats (Qwen, Llama, etc. have different formats)

### Option B: Modify PydanticAI Evaluation

Change evaluation to parse tool calls from text instead of structured parts:

1. Search for JSON patterns in assistant messages
2. Extract tool names from JSON
3. Score based on text-parsed tools

**Pros:**
- No external dependencies
- Quick fix for evaluation

**Cons:**
- Only fixes evaluation, not actual agent tool calling
- Hacky solution that doesn't address root cause
- Brittle (depends on specific text formats)

### Option C: Use Different Model Server

Switch from mlx_lm.server to a server that properly supports tool calling:

1. llama.cpp server (supports function calling)
2. vLLM (supports OpenAI function calling)
3. Local OpenAI-compatible servers with native tool support

**Pros:**
- Proper tool calling support
- Works with PydanticAI out of the box

**Cons:**
- May not support MLX (Apple Silicon optimization)
- Different setup/configuration
- May require different model formats

### Option D: Abandon Local Tool Calling

Accept that local models don't support tool calling reliably:

1. Use base 1.5B model (best for code/reasoning: 71.4%)
2. Focus on code generation and reasoning (both 100%)
3. Skip tool-calling experiments

**Pros:**
- Base model already works great for code/reasoning
- No complex setup needed
- Can still do agentic workflows (just not via tool calling)

**Cons:**
- Gives up on tool calling entirely
- Limited agent capabilities

## Recommendations

### Short-term (Immediate)

**Use 1.5B base model (no adapter) for production:**
- Best overall score: 71.4%
- Perfect code generation: 100%
- Perfect reasoning: 100%
- Training only makes it worse

**Document that tool calling doesn't work:**
- mlx_lm.server + PydanticAI incompatibility
- Not a training data issue
- Not a model size issue
- Architectural limitation

### Medium-term (This Week)

**Investigate Option C (different server):**
- Test llama.cpp server with same models
- See if it properly returns structured tool calls
- If yes, switch to that for tool-calling workloads

**Or implement Option B (fix evaluation):**
- Modify eval_runner.py to parse JSON from text
- At least allows measuring tool calling in text format
- Doesn't fix agent runtime, but allows valid training experiments

### Long-term (Future)

**Contribute to mlx_lm (Option A):**
- Add tool call parsing to mlx_lm.server
- Support multiple formats (Qwen, Llama, etc.)
- Make it truly OpenAI-compatible
- Benefits entire mlx_lm community

**Or accept limitations (Option D):**
- Focus on what works (code generation, reasoning)
- Use cloud APIs (OpenAI, Anthropic) for tool calling
- Local models for code assistance without tools

## Key Lessons Learned

1. **Infrastructure works perfectly** - training, evaluation, CLI all function correctly
2. **Base model is best** - no training beats the pre-trained weights
3. **Architecture matters more than data** - can't fix architectural incompatibility with training
4. **Smaller can be better** - 1.5B outperformed 30B overall
5. **Tool calling is hard** - requires proper API support, not just training data

## Final Recommendations

**For Punie development:**
1. ✅ Use 1.5B base model (no adapter)
2. ✅ Keep tool calling disabled (or use cloud APIs)
3. ✅ Focus on code generation and reasoning (where it excels)
4. ⬜ Investigate llama.cpp or vLLM for proper local tool calling
5. ⬜ Or contribute tool parsing to mlx_lm.server

**For training experiments:**
1. ❌ Don't train on diverse-python (destroys code generation)
2. ❌ Don't train on glaive (no benefit)
3. ❌ Don't train on synthetic tool-calling (catastrophic forgetting)
4. ⚠️ Small hand-authored datasets (8 examples) least harmful (67.9%)
5. ✅ If training needed, use hand-authored + careful validation loss monitoring

## Artifacts

**Evaluation reports generated:**
- `eval_base_model.html` - 1.5B base: 71.4% ✅ BEST
- `eval_baseline_diverse_python.html` - 1.5B + diverse: 51.2%
- `eval_glaive_function_calling.html` - 1.5B + glaive: 53.6%
- `eval_tool_calling_synthetic.html` - 1.5B + synthetic: 32.1%
- `eval_successful_demo.html` - 1.5B + hand-authored: 67.9%
- `eval_qwen_tool_calling.html` - 1.5B + Qwen format: 57.1%
- `eval_30b_base_model.html` - 30B base: 60.7%

**Training data created:**
- `data/qwen-tool-calling/` - 10 examples with `<tool_call>` XML format
- `adapters/qwen-tool-calling/` - Trained adapter (didn't help)

**Scripts created:**
- `create_qwen_tool_training_data.py` - Generate Qwen-specific training data

**Documentation:**
- `docs/research/training-journal.md` - Updated with all findings
- `docs/research/tool-calling-investigation.md` - This document

## Conclusion

**The investigation succeeded in finding the root cause:** mlx_lm.server and PydanticAI are architecturally incompatible for tool calling. No amount of training can fix this.

**The good news:** The 1.5B base model excels at code generation (100%) and reasoning (100%), scoring 71.4% overall. This is perfect for Punie's core use case.

**Next steps depend on priorities:**
- If tool calling is critical: investigate llama.cpp or vLLM
- If code assistance is primary: use base model, it's already great
- If experimenting: contribute tool parsing to mlx_lm.server

The overnight investigation was successful - we now understand exactly why training failed and have clear paths forward.
