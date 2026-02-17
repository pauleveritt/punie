"""Runners for ACP server modes.

This module provides:
- run_http(): HTTP/WebSocket server only (recommended for production)
- run_dual(): Dual protocol mode (stdio + HTTP, deprecated)
"""

import asyncio
import logging
from typing import Any

import uvicorn

from punie.acp import Agent, run_agent
from punie.http.types import Host, Port

__all__ = ["run_http", "run_dual"]

logger = logging.getLogger(__name__)


async def run_http(
    agent: Agent,
    app: object,
    *,
    host: Host = Host("127.0.0.1"),
    port: Port = Port(8000),
    log_level: str = "info",
) -> None:
    """Run HTTP/WebSocket server only (no stdio component).

    This is the recommended mode for production. Clients connect via WebSocket
    at ws://host:port/ws. The server runs indefinitely until cancelled.

    Args:
        agent: The ACP agent implementation (not used directly, app has reference).
        app: The ASGI application to serve over HTTP.
        host: HTTP server bind address (default: 127.0.0.1).
        port: HTTP server port (default: 8000).
        log_level: uvicorn log level (default: "info").

    Example:
        from punie.agent import PunieAgent
        from punie.http import create_app, run_http

        agent = PunieAgent(model="local")
        app = create_app(agent)
        await run_http(agent, app, host="0.0.0.0", port=8000)
    """
    config = uvicorn.Config(
        app,  # type: ignore[arg-type]
        host=host,
        port=port,
        log_level=log_level,
        access_log=False,
    )
    server = uvicorn.Server(config)

    logger.info(
        "Starting HTTP server on %s:%s (WebSocket: ws://%s:%s/ws)",
        host,
        port,
        host,
        port,
    )

    try:
        await server.serve()  # Run indefinitely until cancelled
    except Exception:
        logger.exception("HTTP server error")
        raise
    finally:
        logger.info("HTTP server shutdown complete")


async def _cancel_tasks(tasks: set[asyncio.Task[Any]]) -> None:
    """Cancel tasks and wait for them to finish."""
    for task in tasks:
        if not task.done():
            task.cancel()
    for task in tasks:
        if task.cancelled():
            continue
        try:
            await task
        except asyncio.CancelledError:
            pass


async def run_dual(
    agent: Agent,
    app: object,
    *,
    host: Host = Host("127.0.0.1"),
    port: Port = Port(8000),
    log_level: str = "info",
) -> None:
    """Run ACP agent over stdio and HTTP server concurrently.

    .. deprecated::
        Use run_http() for server-only mode. This dual-protocol mode is kept
        for backward compatibility but will be removed in a future version.

    This function runs both protocols in the same asyncio event loop using
    asyncio.wait(FIRST_COMPLETED). When either protocol terminates (e.g.,
    stdin closes), the other is cancelled for clean shutdown.

    Args:
        agent: The ACP agent implementation to run over stdio.
        app: The ASGI application to serve over HTTP.
        host: HTTP server host (default: 127.0.0.1).
        port: HTTP server port (default: 8000).
        log_level: uvicorn log level (default: "info").

    Example:
        from punie.acp import Agent
        from punie.http import create_app, run_dual

        agent = MyAgent()
        app = create_app()
        await run_dual(agent, app, port=8000)
    """
    config = uvicorn.Config(
        app,  # type: ignore[arg-type]
        host=host,
        port=port,
        log_level=log_level,
        access_log=False,
    )
    server = uvicorn.Server(config)

    acp_task = asyncio.create_task(run_agent(agent), name="acp-stdio")
    http_task = asyncio.create_task(server.serve(), name="http-server")
    all_tasks = {acp_task, http_task}

    logger.info("Starting dual protocol: ACP stdio + HTTP on %s:%s", host, port)

    try:
        done, pending = await asyncio.wait(
            all_tasks,
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in done:
            exc = task.exception() if not task.cancelled() else None
            if exc:
                logger.error("%s failed: %s", task.get_name(), exc)
            else:
                logger.info("%s completed normally", task.get_name())

        await _cancel_tasks(pending)

    except Exception:
        logger.exception("Dual protocol error")
        await _cancel_tasks(all_tasks)
        raise

    logger.info("Dual protocol shutdown complete")
