# Toad Integration Guide

Guide for integrating Punie's WebSocket client with the Toad browser UI frontend.

## Overview

This guide shows how to add WebSocket transport to Toad's Agent class, enabling the Toad UI to connect to Punie server without subprocess overhead.

**Architecture:**
```
[Toad UI] ←→ [WebSocket] ←→ [Punie Server] ←→ [Model]
```

**Benefits over stdio/subprocess:**
- No process management (spawn, kill, cleanup)
- Persistent connection (faster subsequent prompts)
- Built-in reconnection support (5-minute grace period)
- Cleaner error handling
- Network-transparent (can run server remotely)

## Quick Start

### 1. Install Required Dependencies

Punie's WebSocket client is already included in the Punie package:

```bash
# In your Toad project
uv add "punie[client]"
```

### 2. Import the Client Utilities

```python
from punie.client import create_toad_session, send_prompt_stream
```

### 3. Create Agent Wrapper

See `examples/toad_websocket_agent.py` for a complete reference implementation:

```python
from examples.toad_websocket_agent import ToadWebSocketAgent

# Create agent
agent = ToadWebSocketAgent(
    server_url="ws://localhost:8000/ws",
    project_root="/path/to/project"
)

# Connect and use
await agent.connect()
await agent.send_prompt("What is dependency injection?")
await agent.disconnect()
```

## Integration with Toad

### Current Architecture (stdio/subprocess)

**File:** `toad/acp/agent.py`

Current Toad agent uses `asyncio.create_subprocess_exec`:

```python
class Agent:
    async def start(self):
        """Start agent subprocess."""
        self._process = await asyncio.create_subprocess_exec(
            agent_cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Initialize ACP protocol over stdin/stdout...

    async def send_prompt(self, prompt):
        """Send prompt via stdin."""
        # Write to process.stdin...

    async def stop(self):
        """Kill agent process."""
        self._process.kill()
        await self._process.wait()
```

### Proposed Architecture (WebSocket transport)

**Step 1: Add transport configuration**

Add configuration field to choose between stdio and WebSocket:

```python
# In toad/config.py or agent data model
class AgentConfig:
    transport: Literal["stdio", "websocket"] = "stdio"
    server_url: str | None = None  # For WebSocket transport
    command: list[str] | None = None  # For stdio transport
```

**Step 2: Add WebSocket connection setup**

Modify `Agent.start()` to support both transports:

```python
from punie.client import create_toad_session

class Agent:
    def __init__(self, config: AgentConfig):
        self.config = config
        self._process = None  # For stdio transport
        self._websocket = None  # For WebSocket transport
        self._session_id = None

    async def start(self):
        """Start agent (either subprocess or WebSocket connection)."""
        if self.config.transport == "websocket":
            # WebSocket transport
            self._websocket, self._session_id = await create_toad_session(
                self.config.server_url,
                str(self.config.project_root)
            )
            logger.info(f"Connected via WebSocket: {self._session_id}")

        else:
            # stdio transport (existing code)
            self._process = await asyncio.create_subprocess_exec(
                *self.config.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
            )
            # Initialize ACP over stdio...
```

**Step 3: Add WebSocket prompt sending**

Modify `Agent.send_prompt()` to use appropriate transport:

```python
from punie.client import send_prompt_stream

class Agent:
    async def send_prompt(self, prompt: str, on_update: Callable):
        """Send prompt via configured transport."""
        if self.config.transport == "websocket":
            # WebSocket transport
            result = await send_prompt_stream(
                self._websocket,
                self._session_id,
                prompt,
                on_update
            )
            return result

        else:
            # stdio transport (existing code)
            # Write to process.stdin...
```

**Step 4: Add WebSocket cleanup**

Modify `Agent.stop()` to clean up appropriate transport:

```python
class Agent:
    async def stop(self):
        """Stop agent (cleanup subprocess or WebSocket)."""
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
            self._session_id = None

        elif self._process:
            self._process.kill()
            await self._process.wait()
            self._process = None
```

### Complete Integration Pattern

**File:** `toad/acp/agent.py` (modified)

```python
from __future__ import annotations

import asyncio
import logging
from typing import Callable, Literal

from punie.client import create_toad_session, send_prompt_stream

logger = logging.getLogger(__name__)


class AgentConfig:
    """Agent configuration."""
    transport: Literal["stdio", "websocket"]
    server_url: str | None = None  # For WebSocket
    command: list[str] | None = None  # For stdio
    project_root: str


class Agent:
    """Toad agent with pluggable transport."""

    def __init__(self, config: AgentConfig):
        self.config = config
        self._process = None
        self._websocket = None
        self._session_id = None

    async def start(self) -> None:
        """Start agent with configured transport."""
        if self.config.transport == "websocket":
            self._websocket, self._session_id = await create_toad_session(
                self.config.server_url,
                self.config.project_root
            )
        else:
            self._process = await asyncio.create_subprocess_exec(
                *self.config.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
            )
            # Initialize ACP over stdio...

    async def send_prompt(
        self,
        prompt: str,
        on_update: Callable[[str, dict], None]
    ) -> dict:
        """Send prompt via configured transport."""
        if self.config.transport == "websocket":
            return await send_prompt_stream(
                self._websocket,
                self._session_id,
                prompt,
                on_update
            )
        else:
            # stdio transport...
            pass

    async def stop(self) -> None:
        """Stop agent and clean up."""
        if self._websocket:
            await self._websocket.close()
        elif self._process:
            self._process.kill()
            await self._process.wait()
```

## Testing

### 1. Start Punie Server

```bash
# In Punie repo
uv run punie serve
```

Server runs on `http://localhost:8000` with WebSocket endpoint at `ws://localhost:8000/ws`.

### 2. Test Example Agent

```bash
# In Punie repo
uv run python examples/toad_websocket_agent.py "What is dependency injection?"
```

Expected output:
```
Prompt: What is dependency injection?

⏳ Working...
Dependency injection is a design pattern...

Received 5 updates
```

### 3. Verify Streaming

The example demonstrates streaming by printing text chunks as they arrive:

```python
def on_update(update_type, content):
    if update_type == "agent_message_chunk":
        text = content.get("content", {}).get("text", "")
        print(text, end="", flush=True)

await agent.send_prompt("Hello", on_update)
```

### 4. Verify Tool Execution Visibility

Send a prompt that triggers tools:

```python
await agent.send_prompt("Find all Python files in src/")
updates = agent.get_updates()

# Check for tool_call updates
tool_calls = [u for u in updates if u[0] == "tool_call"]
assert len(tool_calls) > 0
```

## Error Handling

### Connection Failures

```python
try:
    await agent.connect()
except ConnectionError as e:
    logger.error(f"Failed to connect to Punie server: {e}")
    # Fallback to stdio transport or notify user
```

### Timeout (5 minutes default)

```python
try:
    result = await agent.send_prompt(prompt, on_update)
except RuntimeError as e:
    if "No response from server" in str(e):
        logger.error("Prompt timed out after 5 minutes")
        # Notify user or retry
```

### Disconnect During Streaming

```python
try:
    result = await agent.send_prompt(prompt, on_update)
except ConnectionError as e:
    logger.error(f"Connection lost: {e}")
    # Attempt reconnection or fallback to stdio
```

## Reconnection Support

Punie server supports session resumption within 5 minutes:

```python
# After disconnect, reconnect and resume
try:
    await agent.connect()  # Creates new session
except ConnectionError:
    # Connection failed, server may be down
    pass
```

**Note:** Current implementation creates a new session on reconnect. Future versions may add explicit resume support.

## Migration Path

### Phase 1: Add WebSocket Support
1. Add `transport` configuration field
2. Implement WebSocket connection setup
3. Add transport selection logic to `start()`, `send_prompt()`, `stop()`
4. Keep stdio transport as default

### Phase 2: Test in Parallel
1. Test WebSocket transport with Punie server
2. Compare performance and reliability with stdio
3. Verify all Toad features work with WebSocket

### Phase 3: Switch Default
1. Make WebSocket the default transport
2. Keep stdio as fallback for local testing
3. Update Toad UI configuration

### Phase 4: Remove stdio (Optional)
1. Once WebSocket is proven stable, consider removing stdio
2. Simplifies codebase and maintenance

## Configuration Examples

### Development (stdio)

```python
config = AgentConfig(
    transport="stdio",
    command=["punie", "ask"],
    project_root="/workspace"
)
```

### Production (WebSocket)

```python
config = AgentConfig(
    transport="websocket",
    server_url="ws://localhost:8000/ws",
    project_root="/workspace"
)
```

### Remote Server

```python
config = AgentConfig(
    transport="websocket",
    server_url="wss://punie.example.com/ws",  # Secure WebSocket
    project_root="/workspace"
)
```

## Next Steps

1. **Implement WebSocket transport in Toad** - Follow integration pattern above
2. **Test with example agent** - Verify streaming and tool execution work
3. **Add configuration UI** - Let users choose transport and server URL
4. **Monitor performance** - Compare WebSocket vs stdio for speed and reliability
5. **Plan migration** - Gradual rollout of WebSocket as default

## Related Documentation

- [Toad Client Guide](toad-client-guide.md) - Complete API reference
- [Client Setup Guide](client-setup-guide.md) - Overview of all client types
- [WebSocket API](websocket-api.md) - ACP protocol details
- [Example Agent](../examples/toad_websocket_agent.py) - Reference implementation

## Support

For issues or questions:
- **Punie issues:** https://github.com/punie/punie/issues
- **Toad issues:** (Your Toad repo issue tracker)
- **API documentation:** See `docs/toad-client-guide.md`
