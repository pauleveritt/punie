#!/usr/bin/env python
"""Spike to probe ty server LSP capabilities.

This script validates that ty server supports the LSP methods needed for Phase 26:
- textDocument/definition (goto definition)
- textDocument/references (find references)

Uses raw JSON-RPC over stdin/stdout (no library dependencies).

Usage:
    uv run python scripts/spike_ty_lsp.py
"""

import json
import subprocess
import sys
import time
from pathlib import Path


class LSPClient:
    """Minimal LSP client using subprocess stdio transport."""

    def __init__(self):
        self.process: subprocess.Popen | None = None
        self.next_id = 1
        self.root_uri = Path.cwd().as_uri()

    def start(self) -> None:
        """Start ty server as subprocess."""
        print("🚀 Starting ty server...")
        self.process = subprocess.Popen(
            ["ty", "server"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,  # Binary mode for precise control
        )
        print(f"✓ ty server started (PID: {self.process.pid})")

    def _send_message(self, message: dict) -> None:
        """Send JSON-RPC message with Content-Length header."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("LSP server not started")

        body = json.dumps(message)
        content = f"Content-Length: {len(body)}\r\n\r\n{body}"

        print(f"\n→ Sending: {message.get('method', 'response')} (id={message.get('id', 'N/A')})")
        print(f"  Body: {body[:200]}..." if len(body) > 200 else f"  Body: {body}")

        self.process.stdin.write(content.encode("utf-8"))
        self.process.stdin.flush()

    def _read_message(self, timeout: float = 10.0) -> dict:
        """Read JSON-RPC message with Content-Length header."""
        if not self.process or not self.process.stdout:
            raise RuntimeError("LSP server not started")

        start = time.time()

        # Read headers
        headers = {}
        while True:
            if time.time() - start > timeout:
                raise TimeoutError(f"Timeout reading headers after {timeout}s")

            line = self.process.stdout.readline().decode("utf-8")
            if line == "\r\n":
                break  # End of headers

            if ":" in line:
                key, value = line.split(":", 1)
                headers[key.strip()] = value.strip()

        # Read body
        content_length = int(headers.get("Content-Length", 0))
        if content_length == 0:
            raise ValueError("No Content-Length header")

        body = self.process.stdout.read(content_length).decode("utf-8")
        message = json.loads(body)

        print(f"\n← Received: {message.get('method', 'response')} (id={message.get('id', 'N/A')})")
        print(f"  Body: {body[:200]}..." if len(body) > 200 else f"  Body: {body}")

        return message

    def _send_request(self, method: str, params: dict) -> dict:
        """Send request and wait for response.

        Note: Server may send notifications before the response.
        Keep reading until we get a message with matching ID.
        """
        request_id = self.next_id
        self.next_id += 1

        self._send_message(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params,
            }
        )

        # Read messages until we get the response with matching ID
        # (server may send notifications in between)
        max_attempts = 10
        for attempt in range(max_attempts):
            message = self._read_message()

            # Check if this is a notification (no id) or a different response
            if message.get("id") == request_id:
                return message

            # This is a notification or unrelated message, keep reading
            print("  (Received notification/other message, continuing...)")

        raise ValueError(f"No response with id={request_id} after {max_attempts} attempts")


    def _send_notification(self, method: str, params: dict) -> None:
        """Send notification (no response expected)."""
        self._send_message(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params,
            }
        )

    def initialize(self) -> dict:
        """Send initialize request."""
        print("\n" + "=" * 80)
        print("STEP 1: Initialize handshake")
        print("=" * 80)

        response = self._send_request(
            "initialize",
            {
                "processId": None,
                "rootUri": self.root_uri,
                "capabilities": {
                    "textDocument": {
                        "definition": {"dynamicRegistration": False},
                        "references": {"dynamicRegistration": False},
                    }
                },
            },
        )

        # Send initialized notification
        self._send_notification("initialized", {})

        return response

    def open_document(self, file_path: str) -> None:
        """Send textDocument/didOpen notification."""
        print("\n" + "=" * 80)
        print(f"STEP 2: Open document: {file_path}")
        print("=" * 80)

        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        content = path.read_text()
        uri = path.resolve().as_uri()

        self._send_notification(
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

    def goto_definition(self, file_path: str, line: int, column: int) -> dict:
        """Send textDocument/definition request."""
        print("\n" + "=" * 80)
        print(f"STEP 3: goto_definition at {file_path}:{line}:{column}")
        print("=" * 80)

        uri = Path(file_path).resolve().as_uri()

        start = time.time()
        response = self._send_request(
            "textDocument/definition",
            {
                "textDocument": {"uri": uri},
                "position": {
                    "line": line - 1,  # LSP uses 0-based
                    "character": column - 1,
                },
            },
        )
        elapsed = time.time() - start

        print(f"\n⏱️  Latency: {elapsed:.3f}s")
        return response

    def find_references(self, file_path: str, line: int, column: int) -> dict:
        """Send textDocument/references request."""
        print("\n" + "=" * 80)
        print(f"STEP 4: find_references at {file_path}:{line}:{column}")
        print("=" * 80)

        uri = Path(file_path).resolve().as_uri()

        start = time.time()
        response = self._send_request(
            "textDocument/references",
            {
                "textDocument": {"uri": uri},
                "position": {
                    "line": line - 1,  # LSP uses 0-based
                    "character": column - 1,
                },
                "context": {"includeDeclaration": True},
            },
        )
        elapsed = time.time() - start

        print(f"\n⏱️  Latency: {elapsed:.3f}s")
        return response

    def shutdown(self) -> None:
        """Shutdown LSP server gracefully."""
        print("\n" + "=" * 80)
        print("STEP 5: Shutdown")
        print("=" * 80)

        # Note: ty server expects null params for shutdown, not {}
        try:
            self._send_request("shutdown", None)  # type: ignore
        except Exception as e:
            print(f"⚠️  Shutdown error (non-fatal): {e}")

        self._send_notification("exit", {})

        if self.process:
            self.process.wait(timeout=5)
            print("✓ ty server stopped")


def analyze_capabilities(response: dict) -> None:
    """Analyze server capabilities from initialize response."""
    print("\n" + "=" * 80)
    print("SERVER CAPABILITIES ANALYSIS")
    print("=" * 80)

    result = response.get("result", {})
    capabilities = result.get("capabilities", {})

    print("\n📋 Capabilities:")
    print(f"  - definitionProvider: {capabilities.get('definitionProvider', False)}")
    print(f"  - referencesProvider: {capabilities.get('referencesProvider', False)}")
    print(f"  - hoverProvider: {capabilities.get('hoverProvider', False)}")
    print(f"  - renameProvider: {capabilities.get('renameProvider', False)}")
    print(f"  - documentSymbolProvider: {capabilities.get('documentSymbolProvider', False)}")

    # Check if we have what we need for Phase 26
    has_definition = capabilities.get("definitionProvider", False)
    has_references = capabilities.get("referencesProvider", False)

    print("\n✅ Phase 26 Requirements:")
    print(f"  - goto_definition: {'✓ SUPPORTED' if has_definition else '✗ NOT SUPPORTED'}")
    print(f"  - find_references: {'✓ SUPPORTED' if has_references else '✗ NOT SUPPORTED'}")

    if has_definition and has_references:
        print("\n🎉 SUCCESS: ty server supports all Phase 26 navigation methods!")
    else:
        print("\n❌ FAILURE: ty server missing required capabilities")
        print("   Consider using basedpyright server instead")


def analyze_definition_response(response: dict) -> None:
    """Analyze textDocument/definition response."""
    print("\n" + "=" * 80)
    print("DEFINITION RESPONSE ANALYSIS")
    print("=" * 80)

    result = response.get("result")

    if result is None:
        print("❌ Result: null (symbol not found)")
        return

    if isinstance(result, dict):
        # Single Location
        print("✓ Result: Single Location")
        print(f"  URI: {result.get('uri', 'N/A')}")
        print(f"  Range: {result.get('range', 'N/A')}")
    elif isinstance(result, list):
        # Array of Locations
        print(f"✓ Result: Array of {len(result)} Locations")
        for i, loc in enumerate(result):
            print(f"  [{i}] URI: {loc.get('uri', 'N/A')}")
            print(f"      Range: {loc.get('range', 'N/A')}")
    else:
        print(f"❌ Unexpected result type: {type(result)}")


def analyze_references_response(response: dict) -> None:
    """Analyze textDocument/references response."""
    print("\n" + "=" * 80)
    print("REFERENCES RESPONSE ANALYSIS")
    print("=" * 80)

    result = response.get("result")

    if result is None:
        print("❌ Result: null (no references found)")
        return

    if isinstance(result, list):
        print(f"✓ Result: Array of {len(result)} Locations")
        for i, loc in enumerate(result[:5]):  # Show first 5
            print(f"  [{i}] URI: {loc.get('uri', 'N/A')}")
            print(f"      Range: {loc.get('range', 'N/A')}")
        if len(result) > 5:
            print(f"  ... and {len(result) - 5} more")
    else:
        print(f"❌ Unexpected result type: {type(result)}")


def main():
    """Run spike to test ty server LSP capabilities."""
    print("=" * 80)
    print("SPIKE: ty server LSP capabilities")
    print("=" * 80)

    # Find a real Python file to test with
    test_file = Path("src/punie/agent/typed_tools.py")
    if not test_file.exists():
        print(f"❌ Test file not found: {test_file}")
        print("   This spike must be run from project root")
        sys.exit(1)

    client = LSPClient()

    try:
        # Step 1: Start server and initialize
        client.start()
        init_response = client.initialize()
        analyze_capabilities(init_response)

        # Step 2: Open a document
        client.open_document(str(test_file))

        # Step 3: Test goto_definition on a known symbol
        # Line 36: class TypeCheckResult(BaseModel):
        # Try to go to definition of "BaseModel" at column 24
        def_response = client.goto_definition(str(test_file), 36, 24)
        analyze_definition_response(def_response)

        # Step 4: Test find_references on a known symbol
        # Line 54: def parse_ty_output(output: str) -> TypeCheckResult:
        # Try to find references to "parse_ty_output" at column 9
        ref_response = client.find_references(str(test_file), 54, 9)
        analyze_references_response(ref_response)

        print("\n" + "=" * 80)
        print("SPIKE COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        # Always try to shutdown cleanly
        try:
            client.shutdown()
        except Exception:
            pass


if __name__ == "__main__":
    main()
