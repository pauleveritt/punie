# T-String DSL for ChatML Training Data — Research Analysis

**Status:** Research Complete
**Date:** 2026-02-15
**Author:** Analysis based on exploration of Punie codebase and tdom processor patterns

## Executive Summary

Punie's training data pipeline has accumulated **4 different tool-call serialization formats** across 25 training phases, with format construction logic scattered across 7+ files representing ~387 lines of duplicated conversion code. Meanwhile, Punie's ecosystem already uses PEP 750 t-strings (tdom) for HTML DSLs.

**Core Question:** Would a t-string-based `chatml()` processor — analogous to tdom's `html()` — provide concrete benefits for Punie's training data pipeline?

**Short Answer:** Yes for architectural coherence and type safety, but a simpler canonical function solves 80% of the same problems. Build when tdom becomes a real dependency or format bugs recur.

## Current State: ChatML Construction in Punie

### The Format Fragmentation Problem

Punie has evolved through 4 distinct tool-call serialization formats:

**Format A — JSON Code Fence** (Phases 1-20)
```python
# tool_calling_templates.py:43
tool_call_response = f'<tool_call>\n{{"name": "{self.tool_name}", "arguments": {self.tool_arguments}}}\n</tool_call>'
```

**Format B — Qwen3 XML** (Phases 21)
```python
# convert_to_xml_format.py:61
return f"<tool_call>\n<function={tool_name}>\n{params_xml}\n</function>\n</tool_call>"
```

**Format C — Code Mode** (Phase 22-24)
```python
# convert_to_code_format.py:123
return f"""<tool_call><function=execute_code>
<parameter=code>
{python_code}
</parameter>
</function></tool_call>"""
```

**Format D — Bare Tool Calls** (Phase 25, attempted)
```python
# Attempted without wrapper tags, caused training failures
result = read_file("test.py")
print(result)
```

### The Duplication Problem

Format construction logic exists in 7+ files with significant overlap:

- `scripts/convert_training_data.py` — Original JSON fence builder
- `scripts/convert_to_xml_format.py` — XML format converter (~245 lines)
- `scripts/convert_to_code_format.py` — Code Mode converter (~258 lines)
- `scripts/merge_phase24_data.py` — Merges with embedded format logic
- `src/punie/training/tool_calling_templates.py` — Template builders (174 lines)
- `src/punie/training/tool_call_parser.py` — Multi-format parser
- Multiple ad-hoc scripts with inline format strings

**Total duplication:** ~387 lines of format construction across conversion scripts alone.

### The Two Serialization Formats Problem

Every ChatML conversation must be serialized into **two different output formats**:

**Format 1: Messages Dict** (for dataset storage)
```python
# dataset.py:32
{"messages": [{"role": "system", "content": "..."}, ...]}
```

**Format 2: Text String** (for mlx_lm.lora training)
```python
{"text": "<|im_start|>system\n...<|im_end|>\n<|im_start|>user\n...<|im_end|>"}
```

This dual-format requirement means every script must:
1. Build the conversation (apply tool-call format)
2. Serialize to messages dict
3. Convert messages dict to text string
4. Write both formats to separate JSONL files

### The Real Bug: Format Mismatches

**Phase 25 Failure** — The training pipeline mixed Format C (Code Mode) with Format D (bare calls) in the same dataset. The model couldn't converge because:
- Training examples used inconsistent token boundaries
- Some examples had `<tool_call>` wrappers, others didn't
- The tokenizer counted different sequence lengths for semantically identical calls

This wasn't a theoretical problem — it caused real training failures and wasted GPU hours.

### The Hardcoded System Prompt Problem

The same system prompt appears verbatim in 8+ files:

```python
system_message = "You are Punie, an AI coding assistant that helps with Python development via PyCharm."
```

Changes to agent personality require hunting through scripts, templates, and conversion tools.

## The T-String DSL Pattern (from tdom)

### What is a T-String Processor?

A t-string processor is a function that consumes a PEP 750 `Template` object and returns domain-specific objects (not strings). The pattern:

1. **Template Evaluation** — `t"string {value}"` → `Template(.strings, .interpolations)`
2. **Static Parsing** — Parse the static skeleton once, cache it
3. **Type-Based Dispatch** — Branch on interpolation type (str, Node, Template, callable)
4. **Custom Format Specs** — `:safe`, `:unsafe` control processing
5. **Domain Objects** — Return structured objects, not concatenated strings

### How tdom's html() Works

From `tdom/processor.py`:

```python
def html(template: Template) -> Node:
    """Parse an HTML t-string, substitute values, and return a tree of Nodes."""
    cachable = CachableTemplate(template)
    t_node = _parse_and_cache(cachable)  # Parse static skeleton once
    return _resolve_t_node(t_node, template.interpolations)  # Substitute values
```

**Key insight:** The processor parses the static structure once (cached via `@lru_cache`), then substitutes interpolated values on each call. This makes repeated calls fast.

### Type-Based Dispatch Example

From `tdom/processor.py:258`:

```python
def _node_from_value(value: object) -> Node:
    """Convert an arbitrary value to a Node based on its runtime type."""
    match value:
        case str():
            return Text(value)
        case Node():
            return value  # Already a Node
        case Template():
            return html(value)  # Recursive template processing
        case False | None:
            return Fragment(children=[])  # Omit falsey values
        case Iterable():
            children = [_node_from_value(v) for v in value]
            return Fragment(children=children)
        case c if callable(c):
            return _node_from_value(c())  # Invoke zero-arg callables
        case _:
            return Text(str(value))  # Fallback: stringify
```

This pattern allows:
- `{user_message}` (str) → escaped text
- `{tool_call}` (ToolCall object) → serialized with format spec
- `{template}` (nested Template) → recursive processing
- `{None}` → omitted from output

### Custom Format Specs

From `tdom/processor.py:60`:

```python
def _format_safe(value: object, format_spec: str) -> str:
    """Use Markup() to mark a value as safe HTML."""
    assert format_spec == "safe"
    return Markup(value)

def _format_unsafe(value: object, format_spec: str) -> str:
    """Convert a value to a plain string, forcing it to be treated as unsafe."""
    assert format_spec == "unsafe"
    return str(value)

CUSTOM_FORMATTERS = (("safe", _format_safe), ("unsafe", _format_unsafe))
```

This allows inline control over escaping:
- `{raw_html:safe}` → no escaping
- `{user_input:unsafe}` → force escape

**For ChatML:** Format specs could control tool-call serialization:
- `{tool_call:json}` → JSON fence format
- `{tool_call:xml}` → Qwen3 XML format
- `{tool_call:code}` → Code Mode format

## What a chatml() Processor Would Look Like

### The Core API

```python
from string.templatelib import Template

# Domain types
@dataclass(frozen=True)
class ToolCall:
    name: str
    arguments: dict[str, Any]

@dataclass(frozen=True)
class ToolResponse:
    content: str

# The processor
def chatml(template: Template) -> ChatMLConversation:
    """Parse a ChatML t-string, substitute values, and return a ChatMLConversation."""
    cachable = CachableTemplate(template)
    t_conversation = _parse_and_cache(cachable)
    return _resolve_t_conversation(t_conversation, template.interpolations)
```

### Example Usage

```python
# Define tools and data
call = ToolCall(name="read_file", arguments={"path": "test.py"})
result = ToolResponse(content="def hello(): pass")
query = "What's in test.py?"
answer = "The file contains a hello() function."

# Build conversation with type-safe interpolations
conversation = chatml(t"""
    <|im_start|>system\n{SYSTEM_PROMPT}<|im_end|>
    <|im_start|>user\n{query}<|im_end|>
    <|im_start|>assistant\n{call:code}<|im_end|>
    <|im_start|>user\n{result}<|im_end|>
    <|im_start|>assistant\n{answer}<|im_end|>
""")

# Dual output formats
conversation.to_text()          # → {"text": "<|im_start|>system\n..."} for mlx_lm
conversation.to_messages_dict() # → {"messages": [...]} for dataset_io
```

### Type-Based Dispatch for Tool Calls

```python
def _message_from_value(value: object, format_spec: str = "") -> str:
    """Convert a value to ChatML message content based on its type."""
    match value:
        case str():
            return value  # Plain text
        case ToolCall():
            return _format_tool_call(value, format_spec or "json")
        case ToolResponse():
            return f"Tool result: {value.content}"
        case Template():
            return chatml(value).to_text()["text"]  # Nested template
        case Iterable():
            parts = [_message_from_value(v, format_spec) for v in value]
            return "\n".join(parts)
        case _:
            return str(value)

def _format_tool_call(call: ToolCall, format_spec: str) -> str:
    """Format a ToolCall based on the format spec."""
    match format_spec:
        case "json":
            args_json = json.dumps(call.arguments)
            return f'<tool_call>\n{{"name": "{call.name}", "arguments": {args_json}}}\n</tool_call>'
        case "xml":
            params = "\n".join(
                f"<parameter={k}>\n{v}\n</parameter>"
                for k, v in call.arguments.items()
            )
            return f"<tool_call>\n<function={call.name}>\n{params}\n</function>\n</tool_call>"
        case "code":
            args_str = ", ".join(f"{k}={v!r}" for k, v in call.arguments.items())
            code = f'result = {call.name}({args_str})\nprint(result)'
            return f"<tool_call><function=execute_code>\n<parameter=code>\n{code}\n</parameter>\n</function></tool_call>"
        case _:
            raise ValueError(f"Unknown tool call format: {format_spec}")
```

### The ChatMLConversation Object

```python
@dataclass(frozen=True)
class ChatMLConversation:
    """A structured ChatML conversation with dual-format serialization."""

    messages: tuple[ChatMessage, ...]

    def to_messages_dict(self) -> dict:
        """Serialize to messages dict format for dataset storage."""
        return {
            "messages": [
                {"role": msg.role, "content": msg.content}
                for msg in self.messages
            ]
        }

    def to_text(self) -> dict:
        """Serialize to text format for mlx_lm.lora training."""
        parts = []
        for msg in self.messages:
            parts.append(f"<|im_start|>{msg.role}\n{msg.content}<|im_end|>")
        return {"text": "\n".join(parts)}
```

## What It Solves vs. What It Doesn't

### ✅ What It Solves

**1. Format Duplication**
- Single source of truth for each format (`:json`, `:xml`, `:code`)
- Eliminates 387+ lines of conversion scripts
- Changes to formats happen in one place

**2. Format Mismatches**
- Type system prevents mixing formats in same conversation
- Format spec is explicit at call site: `{call:code}`
- Compiler catches format errors before training

**3. Dual Serialization**
- `ChatMLConversation` object encapsulates both formats
- `.to_text()` and `.to_messages_dict()` methods eliminate manual conversion
- Same object can be serialized for both mlx_lm and dataset storage

**4. System Prompt Centralization**
- `SYSTEM_PROMPT` constant defined once
- Interpolated everywhere: `{SYSTEM_PROMPT}`
- Personality changes require one-line edits

**5. Type Safety**
- `ToolCall` objects can't be constructed with wrong types
- Format specs are validated at runtime
- Structured data prevents copy-paste errors

**6. Architectural Coherence**
- tdom for UI + chatml for AI = unified t-string ecosystem
- Same mental model: `html()` and `chatml()` are sibling processors
- Composition: `{nested_template}` works for both HTML and ChatML

### ❌ What It Does NOT Solve

**1. Token Compatibility Across Model Families**
- Different models use different special tokens
- Qwen: `<|im_start|>`, Llama: `<|begin_of_text|>`, GPT: no special tokens
- A t-string DSL doesn't abstract token boundaries — it's still model-specific

**2. Pipeline Orchestration**
- Converting between formats still requires running the processor
- Scripts still need to read JSONL, apply processor, write output
- Reduces duplication but doesn't eliminate the conversion step

**3. Training Data Quality**
- Doesn't validate that tool calls make semantic sense
- Doesn't detect hallucinated tool names
- Doesn't ensure tool arguments match tool schemas

**4. Performance Bottlenecks**
- Training speed is GPU-bound, not format-bound
- Conversion scripts run once offline — they're not a real bottleneck
- The 387 lines of duplication are painful for maintenance, not runtime

### Comparison with Simpler Alternatives

**Alternative 1: Single Canonical build_chatml() Function**

```python
def build_chatml(
    messages: Sequence[ChatMessage],
    tool_format: Literal["json", "xml", "code"] = "json"
) -> dict:
    """Build ChatML conversation with specified tool format."""
    # ... implementation ...
    return {"text": text, "messages": messages}
```

**Pros:**
- Solves format duplication (~80% of the problem)
- Solves dual serialization
- Solves system prompt centralization
- No new dependencies (no PEP 750)
- Simpler mental model for contributors

**Cons:**
- Loses inline template visualization
- Loses type-based dispatch on interpolated values
- Loses format specs (`:json`, `:xml`, `:code`)
- Not architecturally coherent with tdom

**Alternative 2: Ad-Hoc String Concatenation (Current State)**

**Pros:**
- Zero abstraction — straightforward for simple cases
- No dependencies

**Cons:**
- Format duplication (387+ lines)
- Format mismatches cause real bugs (Phase 25)
- Dual serialization requires manual conversion
- System prompt hardcoded in 8+ files

### Decision Matrix

| Solution                  | Format Dedup | Type Safety | Dual Output | Architectural Coherence | Complexity |
|---------------------------|--------------|-------------|-------------|-------------------------|------------|
| **T-String chatml()**     | ✅ Excellent  | ✅ Excellent | ✅ Built-in  | ✅ Perfect (w/ tdom)     | Medium     |
| **Canonical function**    | ✅ Good       | ⚠️ Moderate  | ✅ Built-in  | ❌ None                  | Low        |
| **Current (ad-hoc)**      | ❌ None       | ❌ None      | ❌ Manual    | ❌ None                  | High (distributed) |

## Connection to Broader Vision

### The Training Data Flywheel

Punie's competitive advantage comes from **tight iteration loops**:

1. **Generate synthetic examples** (from tools/docs)
2. **Fine-tune Qwen** (with mlx_lm.lora)
3. **Evaluate tool-calling accuracy** (on holdout set)
4. **Refine prompts/formats** based on errors
5. **Repeat**

A `chatml()` DSL accelerates Step 4 by making format changes fast and safe. This compounds over dozens of training cycles.

### Architectural Coherence: tdom + chatml

Punie's ecosystem already uses tdom for UI generation:

```python
# Today: HTML with tdom
ui = html(t"<div class='message'>{user_input}</div>")

# Tomorrow: ChatML with chatml
training_example = chatml(t"""
    <|im_start|>user\n{user_input}<|im_end|>
    <|im_start|>assistant\n{tool_call:json}<|im_end|>
""")
```

**Mental model unification:** Both are t-string processors that parse static skeletons, dispatch on types, and return structured objects. Contributors learn the pattern once.

### Structured ChatMLConversation Objects Enable Tooling

Once conversations are first-class objects (not raw strings), we can build:

- **Validators:** Check that tool names match tool registry
- **Analyzers:** Count tool-call frequency per dataset
- **Transformers:** Swap formats without string regexes
- **Inspectors:** Pretty-print conversations for debugging

Current string-based approach makes these tools brittle (regex parsing).

## Recommendation

### When to Build This

**Build when:**
1. **tdom enters Punie as a real dependency** — Right now, tdom is referenced but not imported. Once Punie uses tdom for UI, adding `chatml()` creates architectural coherence.
2. **Format bugs recur** — If Phase 26-27 hit another format mismatch, the pain justifies the abstraction.
3. **Multi-model support lands** — If Punie must support Llama, Qwen, and GPT token formats, format specs become essential.

**Don't build now because:**
1. **Phase 25 bug is fixed** — The immediate pain is resolved.
2. **Phase 26-27 work is urgent** — Training quality improvements have higher ROI.
3. **tdom is not yet a dependency** — Adding PEP 750 machinery just for training data is premature.

### Minimum Viable Version

If/when built, start with:

1. **Core processor:** `chatml(template: Template) -> ChatMLConversation`
2. **Two format specs:** `:json` (current), `:code` (Phase 22+)
3. **Dual serialization:** `.to_text()` and `.to_messages_dict()`
4. **Type dispatch for:** `str`, `ToolCall`, `ToolResponse`, `Template`

**Defer:**
- XML format (Phase 21 is archived)
- Custom validators (build when needed)
- Multi-model token boundaries (YAGNI)

### Migration Path

**Phase 1:** Build `chatml()` processor + unit tests
**Phase 2:** Refactor `tool_calling_templates.py` to use `chatml()`
**Phase 3:** Replace conversion scripts with `chatml()` calls
**Phase 4:** Deprecate old format builders
**Phase 5:** Remove duplication (~387 lines deleted)

## Appendix: Code References

### Files with Format Construction Logic

- `punie/scripts/convert_training_data.py` — JSON fence format
- `punie/scripts/convert_to_xml_format.py` — 245 lines, XML format
- `punie/scripts/convert_to_code_format.py` — 258 lines, Code Mode format
- `punie/scripts/merge_phase24_data.py` — Merges with embedded format
- `punie/src/punie/training/tool_calling_templates.py` — 174 lines, templates
- `punie/src/punie/training/tool_call_parser.py` — Multi-format parser
- `punie/src/punie/training/dataset.py` — Data types (66 lines)

### T-String Processor Reference

- `tdom/processor.py` — 453 lines, full implementation of `html()` processor
  - Lines 448-452: Main `html()` entry point
  - Lines 258-288: Type-based dispatch (`_node_from_value`)
  - Lines 60-79: Custom format specs (`:safe`, `:unsafe`)
  - Lines 46-48: LRU cache for parsed templates

### Bug Citations

- **Phase 25 Format Mismatch** — Mixed Format C (Code Mode with `<tool_call>` wrapper) and Format D (bare Python calls). Model couldn't converge due to inconsistent token boundaries. Training failed after 2 hours.

## Related Work

- **PEP 750** — Specification for Template Strings (t-strings)
- **tdom** — HTML DSL using t-strings, processor pattern reference
- **mlx_lm.lora** — Fine-tuning library consuming `{"text": "..."}` format
- **Qwen3-Coder** — Model family with XML-based tool-calling syntax
- **Phase 25 Retrospective** — Training failure analysis (to be written)

---

**Status:** Research complete. Recommendation: defer until tdom dependency lands or format bugs recur. Focus on Phase 26-27 training quality improvements.
