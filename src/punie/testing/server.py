"""TCP loopback server for ACP testing.

Provides LoopbackServer for in-process ACP protocol testing.
"""

import asyncio
import contextlib

__all__ = ["LoopbackServer"]


class LoopbackServer:
    """TCP loopback server for in-process ACP testing.

    Creates two (StreamReader, StreamWriter) pairs connected via localhost.
    One pair for server side, one pair for client side.
    """

    __test__ = False  # Prevent pytest collection

    def __init__(self) -> None:
        self._server: asyncio.AbstractServer | None = None
        self._server_reader: asyncio.StreamReader | None = None
        self._server_writer: asyncio.StreamWriter | None = None
        self._client_reader: asyncio.StreamReader | None = None
        self._client_writer: asyncio.StreamWriter | None = None

    async def __aenter__(self):
        async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
            self._server_reader = reader
            self._server_writer = writer

        self._server = await asyncio.start_server(handle, host="127.0.0.1", port=0)
        host, port = self._server.sockets[0].getsockname()[:2]
        self._client_reader, self._client_writer = await asyncio.open_connection(
            host, port
        )

        # Wait until server side is set
        for _ in range(100):
            if self._server_reader and self._server_writer:
                break
            await asyncio.sleep(0.01)
        assert self._server_reader and self._server_writer
        assert self._client_reader and self._client_writer
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._client_writer:
            self._client_writer.close()
            with contextlib.suppress(Exception):
                await self._client_writer.wait_closed()
        if self._server_writer:
            self._server_writer.close()
            with contextlib.suppress(Exception):
                await self._server_writer.wait_closed()
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    @property
    def server_writer(self) -> asyncio.StreamWriter:
        assert self._server_writer is not None
        return self._server_writer

    @property
    def server_reader(self) -> asyncio.StreamReader:
        assert self._server_reader is not None
        return self._server_reader

    @property
    def client_writer(self) -> asyncio.StreamWriter:
        assert self._client_writer is not None
        return self._client_writer

    @property
    def client_reader(self) -> asyncio.StreamReader:
        assert self._client_reader is not None
        return self._client_reader
