# Toad WebSocket Subclass

How Punie provides WebSocket support for Toad without forking the Toad repo.

## Overview

Instead of modifying Toad's codebase, we created a **subclass** in the Punie repo that extends Toad's `Agent` class to add WebSocket support. This keeps Toad pristine while enabling WebSocket integration.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Toad (Unmodified)                  │
│  ~/PycharmProjects/toad                             │
│                                                     │
│  ├─ toad.cli.main()        (UI logic)               │
│  ├─ toad.acp.agent.Agent   (stdio transport)       │
│  └─ toad.acp.protocol      (ACP protocol)          │
└─────────────────────────────────────────────────────┘
                        ↑
                        │ extends
                        │
┌─────────────────────────────────────────────────────┐
│              Punie WebSocket Extension              │
│  ~/projects/pauleveritt/punie                       │
│                                                     │
│  ├─ WebSocketToadAgent     (WebSocket transport)   │
│  │   extends: toad.acp.agent.Agent                 │
│  │   overrides: send(), run(), stop()              │
│  │   reuses: All UI, messages, JSON-RPC            │
│  │                                                  │
│  └─ run_toad_websocket.py  (Launcher)              │
│      - Monkey-patches Agent class                  │
│      - Runs toad.cli.main()                        │
└─────────────────────────────────────────────────────┘
```

## How It Works

### 1. Subclass Override

**File:** `src/punie/toad/websocket_agent.py`

```python
from toad.acp.agent import Agent as ToadAgent
from punie.client.toad_client import create_toad_session

class WebSocketToadAgent(ToadAgent):
    """Extends Toad's Agent with WebSocket support."""

    def __init__(self, ..., server_url="ws://localhost:8000/ws"):
        super().__init__(...)
        self.server_url = server_url
        self._websocket = None

    async def run(self):
        # Connect via WebSocket instead of subprocess
        self._websocket, self._session_id = await create_toad_session(...)
        # Reuse parent's ACP initialization
        await self.acp_initialize()
        await self.acp_new_session()

    def send(self, request):
        # Send via WebSocket instead of stdin
        await self._websocket.send(request.body_json)

    async def stop(self):
        # Close WebSocket instead of killing process
        await self._websocket.close()
```

### 2. Monkey Patch

**File:** `scripts/run_toad_websocket.py`

```python
import toad.cli
from punie.toad import WebSocketToadAgent

# Replace Toad's Agent class with our WebSocket version
toad.acp.agent.Agent = WebSocketToadAgent

# Run Toad's normal CLI
# Toad UI now uses WebSocket transport!
toad.cli.main()
```

### 3. Launcher

**Command:** `just toad-dev`

```bash
# Starts Punie server + Toad with WebSocket
just serve &
python scripts/run_toad_websocket.py
```

## What Gets Reused

**From Toad** (100% unmodified):
- ✅ UI components (Textual widgets, screens)
- ✅ Message handling (UserMessage, Update, ToolCall, etc.)
- ✅ JSON-RPC infrastructure (Server, Request, Response)
- ✅ ACP protocol logic (initialize, new_session, prompt)
- ✅ Database, logging, configuration
- ✅ All domain logic

**What We Override** (3 methods):
- `run()` - Connect via WebSocket instead of subprocess
- `send()` - Send via WebSocket instead of stdin
- `stop()` - Close WebSocket instead of kill process

## Benefits

**1. No Fork Required**
- Toad repo stays pristine
- No merge conflicts when Toad updates
- Clean separation of concerns

**2. Transparent Integration**
- Toad UI doesn't know it's using WebSocket
- All messages, UI, logic work unchanged
- Drop-in replacement for stdio agent

**3. Easy Maintenance**
- Updates to Toad? Just `uv sync`
- Updates to WebSocket? Edit one file
- Single source of truth for each concern

**4. Testing Both Transports**
- stdio: `uv run toad` (original)
- WebSocket: `just toad-start` (subclass)
- Same UI, different transport

## File Structure

```
punie/
├─ src/punie/toad/
│  ├─ __init__.py              # Exports WebSocketToadAgent
│  └─ websocket_agent.py       # Subclass (254 lines)
│
├─ scripts/
│  └─ run_toad_websocket.py    # Launcher with monkey-patch
│
└─ docs/
   └─ toad-websocket-subclass.md  # This file
```

## Usage

### Quick Start

```bash
# One command - starts both
just toad-dev
```

### Manual Control

```bash
# Terminal 1: Start Punie server
just serve

# Terminal 2: Start Toad with WebSocket
just toad-start
```

### Compare Transports

```bash
# Original stdio (from Toad repo)
cd ~/PycharmProjects/toad
uv run toad

# WebSocket (from Punie repo)
cd ~/projects/pauleveritt/punie
just toad-start
```

## Technical Details

### WebSocket Connection Lifecycle

1. **Connect**: `create_toad_session()` establishes WebSocket
2. **Handshake**: `acp_initialize()` performs ACP protocol handshake
3. **Session**: `acp_new_session()` creates server-side session
4. **Ready**: Toad UI becomes active
5. **Prompts**: User interactions flow via WebSocket
6. **Close**: `stop()` closes WebSocket cleanly

### Message Flow

```
User types in Toad UI
       ↓
Toad calls agent.send_prompt(prompt)
       ↓
WebSocketToadAgent.send(request)
       ↓
WebSocket.send(JSON-RPC message)
       ↓
Punie Server receives and processes
       ↓
Server sends session_update notifications
       ↓
WebSocket.recv() in listen loop
       ↓
agent.server.receive(message)
       ↓
rpc_session_update() called (from parent)
       ↓
post_message(Update(...))
       ↓
Toad UI updates (streaming text)
```

### Error Handling

**Connection failures:**
```python
try:
    websocket, session_id = await create_toad_session(...)
except Exception as e:
    self.post_message(AgentFail("Connection failed", str(e)))
```

**Disconnect during operation:**
```python
try:
    await websocket.recv()
except ConnectionError:
    self.post_message(AgentFail("Connection lost", ...))
```

**Graceful shutdown:**
```python
async def stop(self):
    await super().stop()  # Database updates
    await self._websocket.close()  # WebSocket cleanup
```

## Comparison to Integration Guide

**Integration guide approach** (`docs/toad-integration-guide.md`):
- Modify Toad's agent.py directly
- Add transport config to Toad
- Changes live in Toad repo

**Subclass approach** (this document):
- Extend Toad's Agent class
- No changes to Toad repo
- Changes live in Punie repo

**Why subclass wins:**
- No fork required ✅
- Toad stays pristine ✅
- Easier updates ✅
- Can test both transports ✅

## Future

**When Toad adds native WebSocket:**
- Remove subclass
- Use Toad's built-in WebSocket
- Our integration becomes configuration

**Until then:**
- Subclass provides WebSocket now
- Zero changes to Toad
- Clean, maintainable solution

## Related

- [Toad Client Guide](toad-client-guide.md) - WebSocket client API
- [Toad Integration Guide](toad-integration-guide.md) - Direct modification approach
- [Toad Quickstart](toad-quickstart.md) - How to run Toad
- [WebSocket Agent](../src/punie/toad/websocket_agent.py) - Implementation
