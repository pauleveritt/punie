# Phase 42: Standards Applied

## agent-verification
All changes are verified by running `uv run pytest tests/` before committing.
Integration tests run with `uv run pytest -m integration` (separate, requires model server).

## function-based-tests
All new test functions are top-level functions, never classes.

```python
# ✅ CORRECT
def test_receive_messages_normal_flow():
    ...

# ❌ WRONG
class TestReceiveMessages:
    def test_normal_flow(self):
        ...
```

## fakes-over-mocks
New tests use `FakeWebSocket` and `FakeClientConnection` from `src/punie/testing/fakes.py`
instead of `unittest.mock.AsyncMock`.

Rationale: Fakes are more readable, easier to extend, and encode protocol behavior.
Mocks require `side_effect` chains that obscure test intent.

```python
# ✅ CORRECT — fake encodes protocol behavior
fake_ws = FakeWebSocket(responses=[
    {"method": "session_update", "params": {"update": {...}}},
    {"id": "req-1", "result": {}},
])
result = await receive_messages(fake_ws, request_id="req-1")

# ❌ WRONG — mock obscures behavior
ws = AsyncMock()
ws.recv.side_effect = [json.dumps({...}), json.dumps({...})]
result = await receive_messages(ws, request_id="req-1")
```

## protocol-first-design
`PunieClient` is defined as a `Protocol` before any implementation. This prevents
the common failure mode of writing code to the concrete implementation rather than
the abstraction.

```python
# ✅ CORRECT — program to the Protocol
async def run_task(client: PunieClient, prompt: str) -> dict:
    await client.connect(...)
    return await client.send_prompt(prompt)

# ❌ WRONG — program to concrete class
async def run_task(client: ToadClient, prompt: str) -> dict:
    ...
```

## timeout-centralization
All timeout values must come from `src/punie/client/timeouts.py`.
No hardcoded floats in client code.

```python
# ✅ CORRECT
from punie.client.timeouts import CLIENT_TIMEOUTS
await asyncio.wait_for(ws.recv(), timeout=CLIENT_TIMEOUTS.streaming_timeout)

# ❌ WRONG
await asyncio.wait_for(ws.recv(), timeout=300.0)  # Where does 300 come from?
```
