# Phase 28: Ask Client Bug Fix

## Issue

After implementing Phase 28 server/client separation, the `punie ask` command would connect to the server and immediately disconnect without displaying any response to the user.

## Root Cause

The client was checking for the wrong field name when processing `session_update` notifications from the server.

**Incorrect code:**
```python
if update.get("type") == "agent_message":
    for block in update.get("content", []):
        # Process blocks...
```

**Problems:**
1. **Wrong field name**: Checked `update.get("type")` instead of `update.get("session_update")`
2. **Wrong field value**: Expected `"agent_message"` instead of `"agent_message_chunk"`
3. **Wrong data structure**: Treated `content` as a list instead of a single ContentBlock

## Protocol Analysis

The ACP schema defines `AgentMessageChunk` as:
```python
class AgentMessageChunk(ContentChunk):
    session_update: Literal["agent_message_chunk"]
    content: Union[TextContentBlock, ImageContentBlock, ...]  # Single block, not list
```

When serialized by the server using `model_dump(mode="json", exclude_none=True)` (without `by_alias=True`), the JSON structure is:
```json
{
  "session_update": "agent_message_chunk",  // snake_case, not camelCase
  "content": {
    "type": "text",
    "text": "Hello world"
  }
}
```

## Solution

Fixed the client code in `src/punie/client/ask_client.py` to:
1. Check the correct field: `update.get("session_update")`
2. Match the correct value: `"agent_message_chunk"`
3. Handle `content` as a single block, not a list

**Correct code:**
```python
if update.get("session_update") == "agent_message_chunk":
    # content is a single ContentBlock, not a list
    content = update.get("content")
    if content and content.get("type") == "text":
        chunk = content["text"]
        print(chunk, end="", flush=True)
        response_text += chunk
```

## Testing

Verified the fix with:
1. **Manual testing**: `uv run punie ask "What are protocols?"` - works correctly
2. **Integration tests**: All 3 tests in `test_server_client_integration.py` pass
3. **Quality checks**: `ruff check` passes with no issues

## Key Learnings

1. **Serialization matters**: Pydantic's `model_dump()` uses snake_case by default; `by_alias=True` is needed for camelCase
2. **Schema alignment**: Client expectations must match server's actual serialization format
3. **ContentChunk vs content blocks**: `AgentMessageChunk.content` is a single block, not a list of blocks
4. **Test with real data**: Serialization testing revealed the mismatch between expected and actual JSON structure

## Files Modified

- `src/punie/client/ask_client.py` - Fixed field name check (lines 81-98)

## Related Documentation

- ACP Schema: `src/punie/acp/schema.py` (AgentMessageChunk at line 2148)
- Server serialization: `src/punie/http/websocket_client.py` (line 161)
- Integration tests: `tests/test_server_client_integration.py`
