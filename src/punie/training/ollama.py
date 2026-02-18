"""Ollama server process lifecycle management."""

import asyncio
import os
import signal
import subprocess
from dataclasses import dataclass, field
from types import TracebackType

import httpx


@dataclass
class OllamaProcess:
    """Manages ollama subprocess lifecycle.

    Similar to ServerProcess but for Ollama's API:
    - Default port: 11434
    - Health endpoint: /api/tags
    - Model pulling: ollama pull <model> (run once, shows progress)
    """

    model: str  # e.g., "devstral", "qwen3:30b-a3b"
    port: int = 11434
    host: str = "127.0.0.1"
    _process: subprocess.Popen[bytes] | None = field(default=None, init=False)

    @property
    def is_running(self) -> bool:
        """Check if the ollama process is currently running."""
        return self._process is not None and self._process.poll() is None

    @property
    def base_url(self) -> str:
        """Return the base URL for ollama API."""
        return f"http://{self.host}:{self.port}"

    async def health_check(self) -> bool:
        """Check if ollama server is healthy by querying /api/tags endpoint.

        Returns True if server responds successfully, False otherwise.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/tags",
                    timeout=5.0,
                )
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    async def ensure_model_pulled(self) -> None:
        """Ensure model is available (pull if needed).

        Runs `ollama pull <model>` which is idempotent:
        - If model exists locally: exits immediately
        - If model needs download: shows progress

        Raises:
            subprocess.CalledProcessError: If pull command fails (check=True)
        """
        print(f"Ensuring model {self.model} is available...")
        subprocess.run(
            ["ollama", "pull", self.model],
            capture_output=False,  # Show progress to user
            check=True,
        )

    async def start(self, timeout: float = 120.0) -> None:
        """Start the ollama subprocess and wait for it to be ready.

        Args:
            timeout: Maximum seconds to wait for server to become healthy

        Raises:
            RuntimeError: If server is already running
            TimeoutError: If server doesn't become healthy within timeout
            subprocess.CalledProcessError: If server fails to start
        """
        if self.is_running:
            raise RuntimeError("Ollama server is already running")

        # Ensure model is available before starting server
        await self.ensure_model_pulled()

        # Set OLLAMA_HOST environment variable to control port
        env = os.environ.copy()
        env["OLLAMA_HOST"] = f"{self.host}:{self.port}"

        # Start ollama serve subprocess
        self._process = subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        # Poll /api/tags until ready or timeout
        start_time = asyncio.get_event_loop().time()
        while True:
            # Check if process died
            if self._process.poll() is not None:
                _, stderr = self._process.communicate()
                raise subprocess.CalledProcessError(
                    self._process.returncode or 1,
                    ["ollama", "serve"],
                    stderr=stderr,
                )

            # Check if server is healthy
            if await self.health_check():
                print(f"Ollama server ready at {self.base_url}")
                return

            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                await self.stop()
                raise TimeoutError(
                    f"Ollama server did not become healthy within {timeout}s"
                )

            # Wait a bit before next check
            await asyncio.sleep(0.5)

    async def stop(self, timeout: float = 10.0) -> None:
        """Stop the ollama process gracefully (SIGTERM), then forcefully (SIGKILL).

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

    async def __aenter__(self) -> "OllamaProcess":
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
