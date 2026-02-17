"""HTTP application endpoints for Punie.

This module provides a minimal HTTP API with health check and echo endpoints
to demonstrate dual-protocol (ACP + HTTP) operation, plus WebSocket support
for multi-client ACP connections.
"""

from typing import TYPE_CHECKING

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, WebSocketRoute
from starlette.websockets import WebSocket

from punie.http.websocket import websocket_endpoint

if TYPE_CHECKING:
    from punie.agent.adapter import PunieAgent


async def health(request: Request) -> JSONResponse:
    """Health check endpoint.

    Returns:
        JSON response with status "ok" and 200 status code.
    """
    return JSONResponse({"status": "ok"})


async def echo(request: Request) -> JSONResponse:
    """Echo endpoint that returns the request body.

    Accepts JSON request body and returns it wrapped in an "echo" key.

    Returns:
        JSON response with the request body under "echo" key.
    """
    body = await request.json()
    return JSONResponse({"echo": body})


def create_app(agent: PunieAgent) -> Starlette:
    """Create and configure the HTTP application.

    This factory creates a Starlette ASGI application with HTTP endpoints
    and WebSocket support for multi-client ACP connections.

    Args:
        agent: PunieAgent instance to handle WebSocket connections.

    Returns:
        Configured Starlette application.
    """

    async def ws_handler(websocket: WebSocket) -> None:
        """WebSocket route handler that captures agent from closure."""
        await websocket_endpoint(websocket, agent)

    return Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Route("/echo", echo, methods=["POST"]),
            WebSocketRoute("/ws", ws_handler),  # WebSocket endpoint
        ],
    )
