"""HTTP application endpoints for Punie.

This module provides a minimal HTTP API with health check and echo endpoints
to demonstrate dual-protocol (ACP + HTTP) operation.
"""

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route


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


def create_app() -> Starlette:
    """Create and configure the HTTP application.

    This factory creates a Starlette ASGI application with minimal
    endpoints for testing dual-protocol operation.

    Returns:
        Configured Starlette application.
    """
    return Starlette(
        routes=[
            Route("/health", health, methods=["GET"]),
            Route("/echo", echo, methods=["POST"]),
        ],
    )
