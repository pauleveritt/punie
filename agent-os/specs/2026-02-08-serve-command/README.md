# Phase 5.4: `punie serve` Command

**Date:** 2026-02-08
**Status:** In Progress
**Phase:** 5.4

## Purpose

Add `punie serve` subcommand to run Punie agent with both ACP stdio and HTTP protocols concurrently using existing dual-protocol infrastructure.

## Context

Phase 5.1 completed basic CLI with bare `punie` running ACP stdio only. Now we need:
- Subcommand to run dual-protocol mode (ACP stdio + HTTP)
- Reuse existing infrastructure from `punie.http` module
- Support same model/name/logging flags as main command
- Add HTTP-specific flags (host, port)

## Key Design Decision

**Subcommands can write to stdout freely** — unlike bare `punie` which reserves stdout for ACP JSON-RPC protocol, `punie serve` setup/startup messages can use stdout before the agent starts.

## Existing Infrastructure (No Changes Needed)

All components already exist and tested:
- `PunieAgent(model, name)` — agent adapter
- `create_app()` — Starlette app with /health, /echo
- `run_dual(agent, app, host, port, log_level)` — concurrent stdio + HTTP
- `Host`, `Port` NewTypes — type-safe network config

## Goals

1. Add `punie serve` command wrapping `run_dual()`
2. Support all existing flags (--model, --name, --log-dir, --log-level)
3. Add HTTP-specific flags (--host, --port)
4. Reuse logging setup from main command
5. Provide clear startup messages

## Non-Goals

- Changing existing HTTP infrastructure
- Adding new HTTP endpoints
- WebSocket support (future)
- TLS/SSL configuration (future)

## Success Criteria

- `punie serve` runs dual protocols successfully
- All flags work correctly
- Tests cover async helper and CLI integration
- Documentation in examples and evolution.md
