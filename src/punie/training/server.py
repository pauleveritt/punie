"""Server process lifecycle management for mlx_lm.server."""

import asyncio
import signal
import subprocess
from dataclasses import dataclass, field
from types import TracebackType

import httpx

from punie.training.server_config import ServerConfig


def build_server_command(config: ServerConfig) -> list[str]:
    """Build the mlx_lm.server command with all arguments.

    Pure function - easily tested without launching a server.

    Note: config.stop_sequences is NOT added as a CLI flag because mlx_lm.server
    handles stop sequences at the API request level (per-request via the "stop"
    parameter in chat completion requests), not as server-level configuration.
    """
    cmd = [
        "python",
        "-m",
        "mlx_lm",
        "server",
        "--model",
        config.model_path,
        "--port",
        str(config.port),
        "--host",
        config.host,
    ]

    if config.adapter_path:
        cmd.extend(["--adapter-path", config.adapter_path])

    if config.temp is not None:
        cmd.extend(["--temp", str(config.temp)])

    if config.top_p is not None:
        cmd.extend(["--top-p", str(config.top_p)])

    if config.max_tokens is not None:
        cmd.extend(["--max-tokens", str(config.max_tokens)])

    if config.chat_template_args is not None:
        cmd.extend(["--chat-template-args", config.chat_template_args])

    if config.draft_model is not None:
        cmd.extend(["--draft-model", config.draft_model])

    if config.num_draft_tokens is not None:
        cmd.extend(["--num-draft-tokens", str(config.num_draft_tokens)])

    return cmd


@dataclass
class ServerProcess:
    """Manages mlx_lm.server subprocess lifecycle.

    Non-frozen dataclass (like LocalClient pattern) that manages state.
    Can be used as an async context manager.
    """

    config: ServerConfig
    _process: subprocess.Popen[bytes] | None = field(default=None, init=False)

    @property
    def is_running(self) -> bool:
        """Check if the server process is currently running."""
        return self._process is not None and self._process.poll() is None

    async def health_check(self) -> bool:
        """Check if server is healthy by querying /v1/models endpoint.

        Returns True if server responds successfully, False otherwise.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.config.base_url}/models",
                    timeout=5.0,
                )
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def start(self, timeout: float = 60.0) -> None:
        """Start the mlx_lm.server subprocess and wait for it to be ready.

        Args:
            timeout: Maximum seconds to wait for server to become healthy

        Raises:
            RuntimeError: If server is already running
            TimeoutError: If server doesn't become healthy within timeout
            subprocess.CalledProcessError: If server fails to start
        """
        if self.is_running:
            raise RuntimeError("Server is already running")

        cmd = build_server_command(self.config)

        # Start the subprocess
        self._process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        # Poll /v1/models until ready or timeout
        start_time = asyncio.get_event_loop().time()
        while True:
            # Check if process died
            if self._process.poll() is not None:
                _, stderr = self._process.communicate()
                raise subprocess.CalledProcessError(
                    self._process.returncode or 1,
                    cmd,
                    stderr=stderr,
                )

            # Check if server is healthy
            if await self.health_check():
                return

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                await self.stop()
                raise TimeoutError(
                    f"Server did not become healthy within {timeout}s"
                )

            # Wait a bit before next check
            await asyncio.sleep(0.5)

    async def stop(self, timeout: float = 10.0) -> None:
        """Stop the server process gracefully (SIGTERM), then forcefully (SIGKILL).

        Args:
            timeout: Maximum seconds to wait for graceful shutdown

        This method is idempotent - safe to call multiple times.
        """
        if not self._process:
            return

        # Already stopped
        if self._process.poll() is not None:
            self._process = None
            return

        # Try graceful shutdown with SIGTERM
        try:
            self._process.send_signal(signal.SIGTERM)

            # Wait for process to exit
            start_time = asyncio.get_event_loop().time()
            while self._process.poll() is None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    # Timeout - force kill
                    self._process.kill()
                    self._process.wait()
                    break
                await asyncio.sleep(0.1)

        finally:
            self._process = None

    async def __aenter__(self) -> "ServerProcess":
        """Async context manager entry - start the server."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit - stop the server."""
        await self.stop()
