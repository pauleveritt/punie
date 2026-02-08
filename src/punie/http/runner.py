"""Dual-protocol runner for ACP stdio and HTTP server.

This module provides the run_dual() function that runs both ACP stdio
and HTTP server concurrently in the same asyncio event loop.
"""

import asyncio
import logging
from typing import Any

import uvicorn

from punie.acp import Agent, run_agent
from punie.http.types import Host, Port

logger = logging.getLogger(__name__)


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
