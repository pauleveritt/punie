# Toad Quickstart

Quick guide to running Toad with Punie's WebSocket integration.

## Prerequisites

1. **Punie repo**: This repo (`~/projects/pauleveritt/punie`)
2. **Toad repo**: Cloned at `~/PycharmProjects/toad`
3. **Dependencies installed**: Run `uv sync` in Punie repo
4. **Punie agent installed**: Agent config copied to Toad (done automatically below)

## Setup (One-Time)

Install the Punie agent configuration in Toad:

```bash
cp docs/punie-agent.toml ~/PycharmProjects/toad/src/toad/data/agents/punie.toml
```

This registers "Punie (Local)" as an available agent in Toad.

## Quick Start

### One Command (Recommended)

```bash
just toad-dev
```

This intelligently:
- ✅ Detects if Punie server is already running
- ✅ Skips startup if running (connects to existing server)
- ✅ Starts servers if not running (~15s for model load)
- ✅ Launches Toad UI with WebSocket connection

### Manual Control

```bash
# Terminal 1: Start Punie server
just serve

# Terminal 2: Start Toad UI
just toad-start
```

## How It Works

### Server Detection Logic

`just toad-dev` now includes smart detection:

```bash
# Check if Punie server is running on port 8000
if lsof -ti:8000 > /dev/null 2>&1; then
    # Server running → skip startup, just connect Toad
else
    # Server not running → start fresh
fi
```

**Benefits:**
- No duplicate MLX servers (prevents 60GB memory issues)
- Faster iteration (no model reload if server running)
- Servers persist after Toad exits (keeps model in memory)

### Server Lifecycle

```
┌─────────────────────────────────────────────────────┐
│                  First Run                          │
│                                                     │
│  just toad-dev                                      │
│  ├─ No server running → starts MLX + Punie        │
│  ├─ Model loads (~15s, 20GB memory)                │
│  └─ Toad connects via WebSocket                    │
│                                                     │
│  Press Ctrl+D to exit Toad                         │
│  → Servers keep running in background               │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              Subsequent Runs                        │
│                                                     │
│  just toad-dev                                      │
│  ├─ Server already running → skip startup          │
│  └─ Toad connects immediately (~1s)                 │
│                                                     │
│  Press Ctrl+D to exit Toad                         │
│  → Servers keep running in background               │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                   Cleanup                           │
│                                                     │
│  just stop-all                                      │
│  ├─ Stops Punie server (port 8000)                 │
│  ├─ Stops all MLX servers (port 5001)              │
│  └─ Handles multiple orphaned processes            │
└─────────────────────────────────────────────────────┘
```

## Troubleshooting

### Multiple Large Processes (60GB memory)

**Problem:** You ran `just toad-dev` multiple times without stopping servers, creating orphaned MLX processes.

**Solution:**
```bash
# Stop all servers (kills all MLX processes on port 5001)
just stop-all

# Start fresh
just toad-dev
```

**Prevention:** The improved `just toad-dev` detects running servers and skips startup, preventing this issue.

### Server Won't Start

**Check logs:**
```bash
# Punie server log
tail -f punie-server.log

# MLX server log
tail -f mlx-server.log
```

**Check ports:**
```bash
# See what's running
lsof -ti:5001  # MLX server
lsof -ti:8000  # Punie server
```

**Force cleanup:**
```bash
# Kill all processes on ports
just stop-all

# Start fresh
just toad-dev
```

### Connection Failed

**Symptom:** Toad shows "Connection failed" or "Could not connect to Punie server"

**Checks:**
1. Is Punie server running? `lsof -ti:8000`
2. Is MLX server running? `lsof -ti:5001`
3. Check logs: `tail -f punie-server.log mlx-server.log`

**Fix:**
```bash
# Restart servers
just stop-all
just serve

# In another terminal
just toad-start
```

## Commands Reference

### Development

| Command | Description | Time |
|---------|-------------|------|
| `just toad-dev` | Start Toad + servers (smart detection) | ~15s first run, ~1s subsequent |
| `just toad-start` | Start Toad only (requires running server) | ~1s |
| `just serve` | Start MLX + Punie servers (foreground) | ~15s |

### Server Management

| Command | Description |
|---------|-------------|
| `just mlx-start` | Start MLX server only (port 5001) |
| `just server-start` | Start Punie server only (port 8000, requires MLX) |
| `just mlx-stop` | Stop all MLX servers (handles orphaned processes) |
| `just server-stop` | Stop Punie server |
| `just stop-all` | Stop all servers (MLX + Punie) |

### Status Checking

```bash
# See running servers
lsof -ti:5001  # MLX server PIDs
lsof -ti:8000  # Punie server PID

# Check memory usage
ps aux | grep mlx_lm | grep -v grep

# View logs
tail -f punie-server.log mlx-server.log
```

## Architecture

### WebSocket Subclass Approach

Punie integrates with Toad **without forking** using a subclass:

```
┌─────────────────────────────────────────────────────┐
│              Toad (Unmodified)                      │
│  ~/PycharmProjects/toad                             │
│  └─ toad.acp.agent.Agent (stdio transport)         │
└─────────────────────────────────────────────────────┘
                        ↑
                        │ extends
                        │
┌─────────────────────────────────────────────────────┐
│         Punie WebSocket Extension                   │
│  ~/projects/pauleveritt/punie                       │
│  ├─ WebSocketToadAgent (WebSocket transport)       │
│  └─ run_toad_websocket.py (monkey-patches Agent)   │
└─────────────────────────────────────────────────────┘
```

**How it works:**
1. `run_toad_websocket.py` imports Toad
2. Defines `WebSocketToadAgent(toad.acp.agent.Agent)` subclass
3. Monkey-patches: `toad.acp.agent.Agent = WebSocketToadAgent`
4. Runs `toad.cli.main()` - Toad UI uses WebSocket!

**Benefits:**
- ✅ Toad repo stays pristine (no fork needed)
- ✅ Updates to Toad? Just `uv sync`
- ✅ All Toad UI, messages, logic reused (100%)
- ✅ Only 3 methods overridden: `run()`, `send()`, `stop()`

See: [`docs/toad-websocket-subclass.md`](toad-websocket-subclass.md) for details

## Next Steps

1. **Test the integration**: Run `just toad-dev` and ask Punie a question
2. **Explore the code**: See `scripts/run_toad_websocket.py` for implementation
3. **Read the guide**: See `docs/toad-websocket-subclass.md` for architecture details

## Related Documentation

- [`toad-websocket-subclass.md`](toad-websocket-subclass.md) - Architecture and implementation
- [`toad-integration-guide.md`](toad-integration-guide.md) - For Toad developers
- [`toad-client-guide.md`](toad-client-guide.md) - WebSocket client API reference
- [`client-setup-guide.md`](client-setup-guide.md) - All client types

## Changelog

### 2026-02-17: Smart Server Detection

**Improvements:**
- `just toad-dev` detects running servers and skips startup
- `just mlx-stop` handles multiple orphaned processes
- Prevents 60GB memory issues from duplicate MLX servers
- Faster iteration (no model reload if server running)

**Migration:** No changes needed - existing commands work better!
