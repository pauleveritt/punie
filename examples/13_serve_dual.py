"""Example: Dual-protocol serve mode.

Demonstrates how `punie serve` runs both ACP stdio and HTTP
protocols concurrently for development and testing.
"""

import asyncio

from punie.agent import PunieAgent
from punie.http.app import create_app


async def main():
    print("=== Creating agent and HTTP app ===")
    PunieAgent(model="test", name="dual-agent")
    create_app()

    print("\n=== Starting dual protocol mode ===")
    print("ACP stdio: Ready for PyCharm connection")
    print("HTTP: http://127.0.0.1:8000")
    print("Endpoints: /health, /echo")

    # In real usage, this runs until interrupted
    # For demo, we just show the setup
    print(
        "\n(In production: await run_dual(agent, app, Host('127.0.0.1'), Port(8000), 'info'))"
    )


if __name__ == "__main__":
    asyncio.run(main())
