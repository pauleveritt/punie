# Punie the tiny Python agent

Imagine a tiny Python coding agent:

- Runs with local models
- Integrates into PyCharm via ACP
- Shifts more of the work of tools to the IDE via ACP
- Integrate an HTTP loop into the agent making it easy to add custom UX to interact
    - Speed up the "human-in-the-loop" with a custom UI
    - Track multiple agents running at once
- Embrace domain-specific customization to speed up agent and human performance

## Performance ideas

Punie aims to be fast even on lower-end hardware. How? We'd like to investigate:

- Very targeted, slim models (perhaps tuned even further, for special tasks in Python)
- Move more of the work to the "deterministic" side:
    - Use default IDE machinery as "tools" in the agent
    - Easy to add even more IDE functions via IDE plugins
    - Extensive use of Python linters, formatters, and type checkers
    - Perhaps extend *those* by making it easy to add custom policies as "skills" but on the deterministic side
    - Explore Pydantic Monty for tool-running
- Use free-threaded Python (if possible) to tap into more cores

## Research

- The [Agent Client Protocol](https://agentclientprotocol.com/get-started/introduction) home page describes ACP
- The ACP Python SDK has been vendored into `src/punie/acp/` for modification and Pydantic AI integration
- [Pydantic AI](~/PycharmProjects/pydantic-ai) is a local checkout of the Pydantic AI project, including a docs
  directory

## Task plan

- Get a good project setup: examples, tests, docs that match existing projects (svcs-di, tdom-svcs) and skills
- Add docs with deep research on python-sdk and Pydantic AI, to let the agent refer to later
- Get a good pytest setup that proves the existing python-sdk works correctly
- Refactor into a test-driven project
    - Copy the existing python-sdk into this project
    - Make sure it works
    - Refactor the tests to be more granular and pluggable
    - Mock the model calls
- Introduce an HTTP server into the asyncio loop (aiohttp, Starlette, etc.)
- Minimal transition to a Pydantic AI project
- Gradually port the python-sdk "tools" into Pydantic AI tools
- Convert to a best-practices Pydantic AI project