#!/usr/bin/env python3
"""Quick test: Does ty support the LSP capabilities we require?

This is the CRITICAL test from Phase 27.5 Deep Audit Priority 1b.
If ty doesn't support hover/documentSymbol/workspaceSymbol, then lsp_client.start()
will CRASH (lines 110-115), breaking ALL LSP tools including the working ones!
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path


async def test_ty_capabilities():
    """Send initialize request to ty and check what it actually supports."""
    print("🔍 Testing: Does ty support the 3 new LSP capabilities?")
    print("=" * 80)

    # Start ty server
    print("\n📡 Starting ty server...")
    process = await asyncio.create_subprocess_exec(
        "ty",
        "server",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    if not process.stdin or not process.stdout:
        print("❌ Failed to create stdin/stdout pipes")
        return False

    print(f"✅ ty server started (PID: {process.pid})")

    # Send initialize request
    print("\n📤 Sending initialize request...")

    root_uri = Path.cwd().as_uri()
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "processId": None,
            "rootUri": root_uri,
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
    }

    message = json.dumps(request)
    content = f"Content-Length: {len(message)}\r\n\r\n{message}".encode()

    process.stdin.write(content)
    await process.stdin.drain()

    # Read response
    print("📥 Reading response...")

    # Read headers
    header = b""
    while not header.endswith(b"\r\n\r\n"):
        byte = await process.stdout.read(1)
        header += byte

    # Parse Content-Length
    header_str = header.decode()
    content_length = int(header_str.split("Content-Length: ")[1].split("\r\n")[0])

    # Read body
    body = await process.stdout.read(content_length)
    response = json.loads(body.decode())

    # Check capabilities
    print("\n✅ Got initialize response!")

    capabilities = response.get("result", {}).get("capabilities", {})

    print("\n🔍 Server capabilities:")
    print(json.dumps(capabilities, indent=2)[:1000])  # First 1000 chars

    # Check the 5 required capabilities
    has_definition = capabilities.get("definitionProvider")
    has_references = capabilities.get("referencesProvider")
    has_hover = capabilities.get("hoverProvider")
    has_document_symbols = capabilities.get("documentSymbolProvider")
    has_workspace_symbols = capabilities.get("workspaceSymbolProvider")

    print("\n📊 Required capabilities check:")
    print(f"  {'✅' if has_definition else '❌'} definitionProvider (existing): {has_definition}")
    print(f"  {'✅' if has_references else '❌'} referencesProvider (existing): {has_references}")
    print(f"  {'✅' if has_hover else '❌'} hoverProvider (NEW): {has_hover}")
    print(f"  {'✅' if has_document_symbols else '❌'} documentSymbolProvider (NEW): {has_document_symbols}")
    print(f"  {'✅' if has_workspace_symbols else '❌'} workspaceSymbolProvider (NEW): {has_workspace_symbols}")

    # Verdict
    print("\n" + "=" * 80)

    all_supported = all(
        [has_definition, has_references, has_hover, has_document_symbols, has_workspace_symbols]
    )

    if all_supported:
        print("✅ VERDICT: ty supports ALL required capabilities!")
        print("   LSPClient.start() will NOT crash")
    else:
        print("💥 CRITICAL: ty is MISSING required capabilities!")
        print("\n   Impact: LSPClient.start() will crash (lines 110-115):")
        print("   ```python")
        if not has_hover:
            print('   if not capabilities.get("hoverProvider"):')
            print('       raise LSPError("ty server does not support hoverProvider")')
        if not has_document_symbols:
            print('   if not capabilities.get("documentSymbolProvider"):')
            print('       raise LSPError("ty server does not support documentSymbolProvider")')
        if not has_workspace_symbols:
            print('   if not capabilities.get("workspaceSymbolProvider"):')
            print('       raise LSPError("ty server does not support workspaceSymbolProvider")')
        print("   ```")
        print("\n   This breaks ALL LSP tools, including the working goto_definition!")

    # Cleanup
    try:
        # Send shutdown
        shutdown_request = {"jsonrpc": "2.0", "id": 2, "method": "shutdown", "params": None}
        message = json.dumps(shutdown_request)
        content = f"Content-Length: {len(message)}\r\n\r\n{message}".encode()
        process.stdin.write(content)
        await process.stdin.drain()

        # Send exit
        await asyncio.sleep(0.1)
        process.terminate()
        await process.wait()
        print("\n✅ ty server shut down")
    except Exception as e:
        print(f"\n⚠️  Error during cleanup: {e}")

    return all_supported


async def main():
    try:
        result = await test_ty_capabilities()
        sys.exit(0 if result else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
