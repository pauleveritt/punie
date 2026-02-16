"""Tests for LSP client using fakes (no unittest.mock).

Following Agent OS standard: use fakes over mocks for testability.
"""

from pathlib import Path

import pytest

from punie.agent.lsp_client import LSPClient, LSPError


class FakeLSPProcess:
    """Fake asyncio subprocess for testing LSP client."""

    def __init__(self, responses: dict[str, dict]):
        """Initialize fake process with canned responses.

        Args:
            responses: Dict mapping method names to response dicts
        """
        self.responses = responses
        self.sent_messages: list[dict] = []
        self.pid = 12345
        self._request_queue: list[dict] = []

    def queue_message(self, message: dict) -> None:
        """Queue a message to be read (for notifications)."""
        self._request_queue.append(message)

    async def write_message(self, data: bytes) -> None:
        """Simulate stdin.write - captures sent messages."""
        # Parse Content-Length header and body
        content = data.decode("utf-8")
        lines = content.split("\r\n")

        # Find body (after empty line)
        body_start = lines.index("") + 1
        body = "\r\n".join(lines[body_start:])

        if body:
            import json

            message = json.loads(body)
            self.sent_messages.append(message)

    async def drain(self) -> None:
        """Simulate stdin.drain."""
        pass

    async def read_message(self) -> bytes:
        """Simulate stdout.read - returns canned responses."""
        import json

        # Check if we have queued messages (notifications)
        if self._request_queue:
            message = self._request_queue.pop(0)
        else:
            # Find the last sent request
            if not self.sent_messages:
                raise RuntimeError("No messages sent yet")

            last_msg = self.sent_messages[-1]
            method = last_msg.get("method")
            request_id = last_msg.get("id")

            # Get canned response for this method
            if method not in self.responses:
                raise ValueError(f"No canned response for method: {method}")

            response = self.responses[method].copy()

            # Add request ID if this is a request (not notification)
            if request_id is not None:
                response["id"] = request_id

            message = response

        body = json.dumps(message)
        content = f"Content-Length: {len(body)}\r\n\r\n{body}"
        return content.encode("utf-8")

    async def readline(self) -> bytes:
        """Simulate stdout.readline for header reading."""
        # This is called during header parsing
        # We'll return the full message in readexactly, so headers are handled there
        raise NotImplementedError("Use readexactly instead")

    async def readexactly(self, n: int) -> bytes:
        """Simulate stdout.readexactly - returns n bytes."""
        data = await self.read_message()
        return data[:n]

    async def wait(self, timeout: float | None = None) -> int:
        """Simulate process.wait."""
        return 0

    def terminate(self) -> None:
        """Simulate process.terminate."""
        pass


class FakeStreamReader:
    """Fake asyncio StreamReader."""

    def __init__(self, responses: list[bytes]):
        self.responses = responses
        self.response_index = 0

    async def readline(self) -> bytes:
        """Read one line."""
        if self.response_index >= len(self.responses):
            return b""
        line = self.responses[self.response_index]
        self.response_index += 1
        return line

    async def readexactly(self, n: int) -> bytes:
        """Read exactly n bytes."""
        if self.response_index >= len(self.responses):
            return b""
        data = self.responses[self.response_index]
        self.response_index += 1
        return data


class FakeStreamWriter:
    """Fake asyncio StreamWriter."""

    def __init__(self):
        self.written: list[bytes] = []

    def write(self, data: bytes) -> None:
        """Write data."""
        self.written.append(data)

    async def drain(self) -> None:
        """Drain (no-op)."""
        pass


def create_lsp_response(method: str, result: dict | list | None) -> dict:
    """Helper to create standard LSP response."""
    return {"jsonrpc": "2.0", "result": result}


def create_lsp_notification(method: str, params: dict) -> dict:
    """Helper to create standard LSP notification."""
    return {"jsonrpc": "2.0", "method": method, "params": params}


def test_file_uri_conversion():
    """Should convert file paths to file:// URIs."""
    client = LSPClient()

    # Relative path should be resolved to absolute
    uri = client._file_uri("src/app.py")
    assert uri.startswith("file:///")
    assert "src/app.py" in uri

    # Absolute path should be preserved
    abs_path = Path("/tmp/test.py").resolve()
    uri = client._file_uri(str(abs_path))
    assert uri == abs_path.as_uri()


def test_to_lsp_position():
    """Should convert 1-based line/col to 0-based LSP Position."""
    client = LSPClient()

    # Line 1, column 1 → 0, 0
    pos = client._to_lsp_position(1, 1)
    assert pos == {"line": 0, "character": 0}

    # Line 10, column 5 → 9, 4
    pos = client._to_lsp_position(10, 5)
    assert pos == {"line": 9, "character": 4}


def test_from_lsp_position():
    """Should convert 0-based LSP Position to 1-based line/col."""
    client = LSPClient()

    # 0, 0 → Line 1, column 1
    line, col = client._from_lsp_position({"line": 0, "character": 0})
    assert (line, col) == (1, 1)

    # 9, 4 → Line 10, column 5
    line, col = client._from_lsp_position({"line": 9, "character": 4})
    assert (line, col) == (10, 5)


@pytest.mark.asyncio
async def test_send_message():
    """Should send JSON-RPC message with Content-Length header."""
    client = LSPClient()

    # Create fake process with stdin
    writer = FakeStreamWriter()
    client.process = type("Process", (), {"stdin": writer, "stdout": None, "pid": 123})()  # ty: ignore[invalid-assignment]

    message = {"jsonrpc": "2.0", "method": "test", "params": {}}
    await client._send_message(message)

    # Verify Content-Length header and body
    assert len(writer.written) == 1
    content = writer.written[0].decode("utf-8")
    assert "Content-Length:" in content
    assert '"method":"test"' in content or '"method": "test"' in content


@pytest.mark.asyncio
async def test_read_message():
    """Should read JSON-RPC message with Content-Length header."""
    import json

    client = LSPClient()

    # Create response
    response = {"jsonrpc": "2.0", "id": 1, "result": {"test": "data"}}
    body = json.dumps(response)

    # Create fake process with stdout
    reader = FakeStreamReader([
        b"Content-Length: " + str(len(body)).encode() + b"\r\n",
        b"\r\n",
        body.encode("utf-8"),
    ])
    client.process = type("Process", (), {"stdin": None, "stdout": reader, "pid": 123})()  # ty: ignore[invalid-assignment]

    message = await client._read_message()

    assert message == response


@pytest.mark.asyncio
async def test_send_request_success():
    """Should send request and return response with matching ID."""
    import json

    client = LSPClient()

    # Create fake streams
    writer = FakeStreamWriter()

    # Build response
    response = {"jsonrpc": "2.0", "id": 1, "result": {"success": True}}
    body = json.dumps(response)

    reader = FakeStreamReader([
        b"Content-Length: " + str(len(body)).encode() + b"\r\n",
        b"\r\n",
        body.encode("utf-8"),
    ])

    client.process = type(  # ty: ignore[invalid-assignment]
        "Process", (), {"stdin": writer, "stdout": reader, "pid": 123}
    )()

    result = await client._send_request("test_method", {"param": "value"})

    assert result["id"] == 1
    assert result["result"] == {"success": True}


@pytest.mark.asyncio
async def test_send_request_with_error():
    """Should raise LSPError when server returns error response."""
    import json

    client = LSPClient()

    # Create fake streams
    writer = FakeStreamWriter()

    # Build error response
    response = {
        "jsonrpc": "2.0",
        "id": 1,
        "error": {"code": -32601, "message": "Method not found"},
    }
    body = json.dumps(response)

    reader = FakeStreamReader([
        b"Content-Length: " + str(len(body)).encode() + b"\r\n",
        b"\r\n",
        body.encode("utf-8"),
    ])

    client.process = type(  # ty: ignore[invalid-assignment]
        "Process", (), {"stdin": writer, "stdout": reader, "pid": 123}
    )()

    with pytest.raises(LSPError) as exc_info:
        await client._send_request("invalid_method", {})

    assert "Method not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_send_notification():
    """Should send notification without waiting for response."""
    client = LSPClient()

    # Create fake process with stdin
    writer = FakeStreamWriter()
    client.process = type("Process", (), {"stdin": writer, "stdout": None, "pid": 123})()  # ty: ignore[invalid-assignment]

    await client._send_notification("test_notification", {"data": "value"})

    # Verify message was sent
    assert len(writer.written) == 1
    content = writer.written[0].decode("utf-8")
    assert '"method":"test_notification"' in content or '"method": "test_notification"' in content
    # Notification should have no 'id' field
    assert '"id"' not in content


def test_opened_documents_tracking():
    """Should track opened documents to avoid duplicate didOpen."""
    client = LSPClient()

    uri1 = "file:///path/to/file1.py"
    uri2 = "file:///path/to/file2.py"

    # Initially empty
    assert len(client.opened_documents) == 0

    # Add documents
    client.opened_documents.add(uri1)
    client.opened_documents.add(uri2)

    assert uri1 in client.opened_documents
    assert uri2 in client.opened_documents
    assert len(client.opened_documents) == 2

    # Adding same document again should not duplicate
    client.opened_documents.add(uri1)
    assert len(client.opened_documents) == 2


def test_lsp_client_initialization():
    """Should initialize LSP client with correct defaults."""
    client = LSPClient()

    assert client.process is None
    assert client.next_id == 1
    assert client.root_uri.startswith("file:///")
    assert len(client.opened_documents) == 0
    assert client._initialized is False
