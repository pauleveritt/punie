"""LSP client for ty server navigation (goto_definition, find_references).

This module provides a minimal async LSP client that connects to ty server
via stdio transport. It's designed specifically for Phase 26 navigation tools.

The client lifecycle is managed as a module-level singleton:
- First call to get_lsp_client() starts ty server and performs initialize handshake
- Subsequent calls return the same client instance
- Client stays alive for the duration of the process (no explicit shutdown needed)

Example:
    client = await get_lsp_client()
    response = await client.goto_definition("src/app.py", 10, 5)
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Module-level singleton
_lsp_client: LSPClient | None = None


class LSPError(Exception):
    """Base exception for LSP client errors."""

    pass


class LSPClient:
    """Minimal async LSP client for ty server navigation.

    Handles:
    - initialize/shutdown lifecycle
    - textDocument/didOpen lazy loading
    - textDocument/definition (goto definition)
    - textDocument/references (find references)
    - textDocument/hover (hover info)
    - textDocument/documentSymbol (document symbols)
    - workspace/symbol (workspace symbols)

    Protocol details:
    - Uses stdio transport (stdin/stdout)
    - Handles notifications (textDocument/publishDiagnostics) before responses
    - Converts paths to file:// URIs
    - Converts 1-based line/column to 0-based LSP positions
    """

    def __init__(self):
        self.process: asyncio.subprocess.Process | None = None
        self.next_id = 1
        self.root_uri = Path.cwd().as_uri()
        self.opened_documents: set[str] = set()  # Track opened files
        self._read_lock = asyncio.Lock()  # Serialize reads
        self._initialized = False

    async def start(self) -> None:
        """Start ty server and perform initialize handshake."""
        if self._initialized:
            return

        logger.info("Starting ty server...")

        # Start ty server subprocess
        self.process = await asyncio.create_subprocess_exec(
            "ty",
            "server",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        if not self.process.stdin or not self.process.stdout:
            raise LSPError("Failed to create stdin/stdout pipes")

        logger.info(f"ty server started (PID: {self.process.pid})")

        # Send initialize request
        response = await self._send_request(
            "initialize",
            {
                "processId": None,
                "rootUri": self.root_uri,
                "capabilities": {
                    "textDocument": {
                        "definition": {"dynamicRegistration": False},
                        "references": {"dynamicRegistration": False},
                        "hover": {"dynamicRegistration": False},
                        "documentSymbol": {"dynamicRegistration": False},
                    },
                    "workspace": {
                        "symbol": {"dynamicRegistration": False},
                    },
                },
            },
        )

        # Verify capabilities
        capabilities = response.get("result", {}).get("capabilities", {})
        if not capabilities.get("definitionProvider"):
            raise LSPError("ty server does not support definitionProvider")
        if not capabilities.get("referencesProvider"):
            raise LSPError("ty server does not support referencesProvider")
        if not capabilities.get("hoverProvider"):
            raise LSPError("ty server does not support hoverProvider")
        if not capabilities.get("documentSymbolProvider"):
            raise LSPError("ty server does not support documentSymbolProvider")
        if not capabilities.get("workspaceSymbolProvider"):
            raise LSPError("ty server does not support workspaceSymbolProvider")

        logger.debug(f"Server capabilities: {capabilities}")

        # Send initialized notification
        await self._send_notification("initialized", {})

        self._initialized = True
        logger.info("LSP client initialized")

    async def shutdown(self) -> None:
        """Shutdown ty server gracefully."""
        if not self._initialized or not self.process:
            return

        logger.info("Shutting down ty server...")

        try:
            await self._send_request("shutdown", None)
            await self._send_notification("exit", {})
        except Exception as e:
            logger.warning(f"Error during shutdown (non-fatal): {e}")

        if self.process:
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
                logger.info("ty server stopped")
            except asyncio.TimeoutError:
                logger.warning("ty server did not stop within 5s, terminating")
                self.process.terminate()

        self._initialized = False

    async def open_document(self, file_path: str) -> None:
        """Send textDocument/didOpen notification (lazy, first-access only).

        Args:
            file_path: Absolute or relative path to file

        Note:
            Tracks opened documents to avoid sending multiple didOpen for same file.
        """
        uri = self._file_uri(file_path)

        if uri in self.opened_documents:
            return  # Already opened

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = path.read_text()

        await self._send_notification(
            "textDocument/didOpen",
            {
                "textDocument": {
                    "uri": uri,
                    "languageId": "python",
                    "version": 1,
                    "text": content,
                }
            },
        )

        self.opened_documents.add(uri)
        logger.debug(f"Opened document: {uri}")

    async def goto_definition(
        self, file_path: str, line: int, column: int
    ) -> dict[str, Any]:
        """Send textDocument/definition request.

        Args:
            file_path: File path
            line: Line number (1-based)
            column: Column number (1-based)

        Returns:
            LSP response dict with 'result' field (Location[] | null)

        Note:
            Automatically opens document if not already opened.
        """
        await self.open_document(file_path)

        uri = self._file_uri(file_path)
        position = self._to_lsp_position(line, column)

        logger.info(f"LSP: goto_definition({file_path}:{line}:{column})")

        response = await self._send_request(
            "textDocument/definition",
            {
                "textDocument": {"uri": uri},
                "position": position,
            },
        )

        logger.debug(f"Definition response: {response}")
        return response

    async def find_references(
        self, file_path: str, line: int, column: int
    ) -> dict[str, Any]:
        """Send textDocument/references request.

        Args:
            file_path: File path
            line: Line number (1-based)
            column: Column number (1-based)

        Returns:
            LSP response dict with 'result' field (Location[] | null)

        Note:
            Automatically opens document if not already opened.
        """
        await self.open_document(file_path)

        uri = self._file_uri(file_path)
        position = self._to_lsp_position(line, column)

        logger.info(f"LSP: find_references({file_path}:{line}:{column})")

        response = await self._send_request(
            "textDocument/references",
            {
                "textDocument": {"uri": uri},
                "position": position,
                "context": {"includeDeclaration": True},
            },
        )

        logger.debug(f"References response: {response}")
        return response

    async def hover(
        self, file_path: str, line: int, column: int
    ) -> dict[str, Any]:
        """Send textDocument/hover request.

        Args:
            file_path: File path
            line: Line number (1-based)
            column: Column number (1-based)

        Returns:
            LSP response dict with 'result' field (Hover | null)

        Note:
            Automatically opens document if not already opened.
        """
        await self.open_document(file_path)

        uri = self._file_uri(file_path)
        position = self._to_lsp_position(line, column)

        logger.info(f"LSP: hover({file_path}:{line}:{column})")

        response = await self._send_request(
            "textDocument/hover",
            {
                "textDocument": {"uri": uri},
                "position": position,
            },
        )

        logger.debug(f"Hover response: {response}")
        return response

    async def document_symbols(self, file_path: str) -> dict[str, Any]:
        """Send textDocument/documentSymbol request.

        Args:
            file_path: File path

        Returns:
            LSP response dict with 'result' field (DocumentSymbol[] | SymbolInformation[] | null)

        Note:
            Automatically opens document if not already opened.
        """
        await self.open_document(file_path)

        uri = self._file_uri(file_path)

        logger.info(f"LSP: document_symbols({file_path})")

        response = await self._send_request(
            "textDocument/documentSymbol",
            {
                "textDocument": {"uri": uri},
            },
        )

        logger.debug(f"Document symbols response: {response}")
        return response

    async def workspace_symbols(self, query: str) -> dict[str, Any]:
        """Send workspace/symbol request.

        Args:
            query: Search query string

        Returns:
            LSP response dict with 'result' field (SymbolInformation[] | WorkspaceSymbol[] | null)

        Note:
            Does not require document to be opened.
        """
        logger.info(f"LSP: workspace_symbols(query={query})")

        response = await self._send_request(
            "workspace/symbol",
            {
                "query": query,
            },
        )

        logger.debug(f"Workspace symbols response: {response}")
        return response

    def _file_uri(self, file_path: str) -> str:
        """Convert file path to LSP file:// URI.

        Args:
            file_path: Absolute or relative file path

        Returns:
            file:// URI (always absolute)
        """
        return Path(file_path).resolve().as_uri()

    def _to_lsp_position(self, line: int, column: int) -> dict[str, int]:
        """Convert 1-based line/column to LSP 0-based Position.

        Args:
            line: Line number (1-based, human-readable)
            column: Column number (1-based, human-readable)

        Returns:
            LSP Position dict with 0-based line and character
        """
        return {"line": line - 1, "character": column - 1}

    def _from_lsp_position(self, pos: dict[str, int]) -> tuple[int, int]:
        """Convert LSP 0-based Position to 1-based line/column.

        Args:
            pos: LSP Position dict with 'line' and 'character'

        Returns:
            Tuple of (line, column) in 1-based indexing
        """
        return (pos["line"] + 1, pos["character"] + 1)

    async def _send_message(self, message: dict) -> None:
        """Send JSON-RPC message with Content-Length header.

        Args:
            message: JSON-RPC message dict
        """
        if not self.process or not self.process.stdin:
            raise LSPError("LSP server not started")

        body = json.dumps(message)
        content = f"Content-Length: {len(body)}\r\n\r\n{body}"

        logger.debug(f"→ {message.get('method', 'response')} (id={message.get('id', 'N/A')})")

        self.process.stdin.write(content.encode("utf-8"))
        await self.process.stdin.drain()

    async def _read_message(self, timeout: float = 10.0) -> dict:
        """Read JSON-RPC message with Content-Length header.

        Args:
            timeout: Read timeout in seconds

        Returns:
            JSON-RPC message dict

        Note:
            Uses lock to serialize reads (prevent interleaving).
        """
        async with self._read_lock:
            if not self.process or not self.process.stdout:
                raise LSPError("LSP server not started")

            # Read headers
            headers: dict[str, str] = {}
            while True:
                line = await asyncio.wait_for(
                    self.process.stdout.readline(), timeout=timeout
                )
                line_str = line.decode("utf-8")

                if line_str == "\r\n":
                    break  # End of headers

                if ":" in line_str:
                    key, value = line_str.split(":", 1)
                    headers[key.strip()] = value.strip()

            # Read body
            content_length = int(headers.get("Content-Length", 0))
            if content_length == 0:
                raise LSPError("No Content-Length header in LSP message")

            body_bytes = await asyncio.wait_for(
                self.process.stdout.readexactly(content_length), timeout=timeout
            )
            body = body_bytes.decode("utf-8")
            message = json.loads(body)

            logger.debug(f"← {message.get('method', 'response')} (id={message.get('id', 'N/A')})")

            return message

    async def _send_request(self, method: str, params: dict | None) -> dict:
        """Send JSON-RPC request and wait for response.

        Args:
            method: LSP method name
            params: Request params (or None)

        Returns:
            Response message dict

        Note:
            Handles notifications that may arrive before the response.
            Keeps reading until we get a message with matching ID.
        """
        request_id = self.next_id
        self.next_id += 1

        await self._send_message(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )

        # Read messages until we get response with matching ID
        # (server may send notifications in between)
        max_attempts = 10
        for attempt in range(max_attempts):
            message = await self._read_message()

            # Check if this is the response we're waiting for
            if message.get("id") == request_id:
                # Check for error
                if "error" in message:
                    error = message["error"]
                    raise LSPError(f"LSP error: {error.get('message', error)}")
                return message

            # This is a notification or unrelated message, continue reading
            logger.debug(f"Received notification while waiting for id={request_id}, continuing...")

        raise LSPError(f"No response with id={request_id} after {max_attempts} attempts")

    async def _send_notification(self, method: str, params: dict) -> None:
        """Send JSON-RPC notification (no response expected).

        Args:
            method: LSP method name
            params: Notification params
        """
        await self._send_message(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            }
        )


async def get_lsp_client() -> LSPClient:
    """Get or create the module-level LSP client singleton.

    Returns:
        Initialized LSPClient instance

    Note:
        First call starts ty server. Subsequent calls return same instance.
    """
    global _lsp_client

    if _lsp_client is None:
        _lsp_client = LSPClient()
        await _lsp_client.start()

    return _lsp_client
