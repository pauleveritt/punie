# Phase 5.2: `punie init` Command

**Date:** 2026-02-08
**Status:** In Progress
**Phase:** 5.2

## Purpose

Add `punie init` subcommand to generate JetBrains ACP configuration file (`~/.jetbrains/acp.json`) that enables PyCharm to launch Punie as an AI coding agent.

## Context

Phase 5.1 completed basic CLI with bare `punie` running ACP stdio. Now we need:
- Subcommand to generate PyCharm discovery configuration
- Intelligent detection of Punie executable (system vs uvx)
- Config merging to preserve other agents
- Environment variable injection for model selection

## Key Design Decision

**Subcommands can write to stdout freely** — unlike bare `punie` which reserves stdout for ACP JSON-RPC protocol, `punie init` is a normal CLI command that generates files and prints user-facing messages.

## Goals

1. Generate valid `acp.json` with Punie agent entry
2. Detect Punie executable location (system PATH or uvx fallback)
3. Merge with existing config to preserve other agents
4. Support `--model` flag to pre-configure PUNIE_MODEL
5. Support `--output` flag to override config path
6. Provide clear user feedback on what was generated

## Non-Goals

- PyCharm plugin integration (handled by JetBrains)
- Model validation or download
- Interactive configuration wizard
- Migration from old config formats

## Success Criteria

- `punie init` generates valid acp.json
- Config includes correct Punie command path
- Existing agents preserved when merging
- Tests cover pure functions and CLI integration
- Documentation in examples and evolution.md
