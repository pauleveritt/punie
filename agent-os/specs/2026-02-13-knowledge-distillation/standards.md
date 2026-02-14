# Knowledge Distillation Spec - Standards

## Training Data Standards

- **Tool-call format:** Use `"name"` key (not `"tool"`) to match parser
- **Multi-turn examples:** Include user prompt, assistant tool call, tool result, assistant response
- **Direct answers:** No tool calls, answer from base knowledge
- **Balanced composition:** 60-75% with tools, 25-40% without tools
- **Diverse categories:** Concepts, comparisons, best practices, syntax, architecture

## Code Standards

- **Function-based tests:** All tests use functions, never classes
- **Type safety:** Full type annotations, passes `ty` checks
- **Stop sequences:** Always use `"stop_sequences"` key for PydanticAI
- **Configuration:** Use AgentConfig frozen dataclass for consistency

## Training Standards

- **Batch size:** 2 (optimal for 32GB M1 Max)
- **LoRA rank:** 16 (num_layers parameter)
- **Loss tracking:** Monitor train and validation loss
- **Memory limit:** Stay under 19GB peak to avoid OOM
- **Checkpoints:** Save every 150 iterations for recovery

## Testing Standards

- **Discrimination test:** 5 queries (3 direct, 2 tool-calling)
- **Turn counting:** Verify model completes in 1-2 turns (no loops)
- **Stop sequences:** Verify no garbage tokens after `<|im_end|>`
- **Tool format:** Verify correct JSON structure in tool calls

## Project Standards

- Use Astral tools via skills (`astral:ruff`, `astral:ty`)
- Python 3.14 modern syntax
- No auto-commit — always ask before creating commits
- Verify with `uv run pytest` directly
