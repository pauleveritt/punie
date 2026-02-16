#!/usr/bin/env python3
"""Test LSP tools against real ty language server to verify they actually work.

This is Priority 1b of the Phase 27.5 Deep Audit.
Tests hover, document_symbols, and workspace_symbols against a REAL ty instance.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from punie.agent.lsp_client import LSPClient


async def test_lsp_capabilities():
    """Test if ty supports the LSP capabilities we claim to use."""
    print("=" * 80)
    print("TEST 0: Check LSP capabilities")
    print("=" * 80)

    client = LSPClient()

    try:
        # Start the LSP server
        print("\n📡 Starting ty LSP server...")
        await client.start(str(Path(__file__).parent.parent / "src"))

        print("✅ Server started successfully")

        # Check capabilities
        print("\n🔍 Server capabilities:")
        caps = client.server_capabilities

        if not caps:
            print("  ❌ No capabilities reported!")
            return False

        # Check for the 3 new capabilities
        has_hover = caps.get("hoverProvider")
        has_document_symbols = caps.get("documentSymbolProvider")
        has_workspace_symbols = caps.get("workspaceSymbolProvider")

        print(f"  hoverProvider: {has_hover}")
        print(f"  documentSymbolProvider: {has_document_symbols}")
        print(f"  workspaceSymbolProvider: {has_workspace_symbols}")

        # Also check existing ones
        has_definition = caps.get("definitionProvider")
        has_references = caps.get("referencesProvider")

        print(f"  definitionProvider (existing): {has_definition}")
        print(f"  referencesProvider (existing): {has_references}")

        # Verdict
        print("\n📊 VERDICT:")
        all_supported = all([has_hover, has_document_symbols, has_workspace_symbols])

        if all_supported:
            print("  ✅ All 3 new LSP capabilities are supported by ty")
        else:
            print("  ⚠️  Some LSP capabilities are MISSING from ty:")
            if not has_hover:
                print("     - hoverProvider: NOT SUPPORTED")
            if not has_document_symbols:
                print("     - documentSymbolProvider: NOT SUPPORTED")
            if not has_workspace_symbols:
                print("     - workspaceSymbolProvider: NOT SUPPORTED")

            print("\n  💥 CRITICAL: lsp_client.start() will CRASH if it requires these!")
            print("     Check src/punie/agent/lsp_client.py start() method")

        return all_supported

    except Exception as e:
        print(f"\n❌ Failed to start LSP server: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        try:
            await client.stop()
        except:
            pass


async def test_hover():
    """Test hover against a real file."""
    print("\n" + "=" * 80)
    print("TEST 1: hover() - Real LSP call")
    print("=" * 80)

    client = LSPClient()

    try:
        await client.start(str(Path(__file__).parent.parent / "src"))

        # Test on a real file - monty_runner.py, line 20, symbol "LSPClient"
        test_file = str(Path(__file__).parent.parent / "src" / "punie" / "agent" / "monty_runner.py")
        print(f"\n📁 Test file: {test_file}")
        print("   Symbol: LSPClient (import at top of file)")

        # Try to hover over the LSPClient import
        result = await client.hover(test_file, line=20, column=30, symbol="LSPClient")

        print("\n✅ Result:")
        print(f"  success: {result.success}")
        print(f"  symbol: {result.symbol}")
        print(f"  type_info: {result.type_info}")
        print(f"  docstring: {result.docstring[:200] if result.docstring else None}...")

        if not result.success:
            print("\n⚠️  Hover FAILED!")
            print("  This could mean:")
            print("    1. ty doesn't support hover")
            print("    2. The line/column are wrong")
            print("    3. The file isn't indexed yet")

        return result.success

    except Exception as e:
        print(f"\n❌ Hover call crashed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        try:
            await client.stop()
        except:
            pass


async def test_document_symbols():
    """Test document_symbols against a real file."""
    print("\n" + "=" * 80)
    print("TEST 2: document_symbols() - Real LSP call")
    print("=" * 80)

    client = LSPClient()

    try:
        await client.start(str(Path(__file__).parent.parent / "src"))

        # Test on a real file - typed_tools.py (has many symbols)
        test_file = str(Path(__file__).parent.parent / "src" / "punie" / "agent" / "typed_tools.py")
        print(f"\n📁 Test file: {test_file}")

        result = await client.document_symbols(test_file)

        print("\n✅ Result:")
        print(f"  success: {result.success}")
        print(f"  symbol_count: {result.symbol_count}")

        print("\n📝 Sample symbols (first 10):")
        for i, symbol in enumerate(result.symbols[:10]):
            print(f"  {i+1}. {symbol.name} ({symbol.kind}) - line {symbol.line}")
            if symbol.children:
                print(f"     {len(symbol.children)} children")

        if not result.success:
            print("\n⚠️  document_symbols FAILED!")

        return result.success

    except Exception as e:
        print(f"\n❌ document_symbols call crashed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        try:
            await client.stop()
        except:
            pass


async def test_workspace_symbols():
    """Test workspace_symbols - the MOST LIKELY TO FAIL."""
    print("\n" + "=" * 80)
    print("TEST 3: workspace_symbols() - Real LSP call (HIGH RISK)")
    print("=" * 80)

    client = LSPClient()

    try:
        await client.start(str(Path(__file__).parent.parent / "src"))

        print("\n🔍 Searching for: 'LSPClient'")

        result = await client.workspace_symbols("LSPClient")

        print("\n✅ Result:")
        print(f"  success: {result.success}")
        print(f"  symbol_count: {result.symbol_count}")

        print("\n📝 Sample symbols (first 5):")
        for i, symbol in enumerate(result.symbols[:5]):
            print(f"  {i+1}. {symbol.name} ({symbol.kind})")
            print(f"     {symbol.location.file}:{symbol.location.line}")

        if not result.success:
            print("\n⚠️  workspace_symbols FAILED!")
            print("  This is EXPECTED - the audit plan noted that workspace_symbols")
            print("  may not be supported by ty at all.")

        return result.success

    except Exception as e:
        print(f"\n❌ workspace_symbols call crashed: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        try:
            await client.stop()
        except:
            pass


async def main():
    """Run all LSP tool tests."""
    print("🔍 Phase 27.5 Deep Audit - Priority 1b: Real LSP Tools Test")
    print("Testing LSP tools against REAL ty language server\n")

    # Test 0: Check capabilities first
    caps_ok = await test_lsp_capabilities()

    if not caps_ok:
        print("\n" + "=" * 80)
        print("⚠️  WARNING: Not all capabilities are supported!")
        print("=" * 80)
        print("Proceeding with functional tests anyway to see what actually works...")

    # Test 1-3: Try the actual calls
    hover_ok = await test_hover()
    doc_symbols_ok = await test_document_symbols()
    workspace_symbols_ok = await test_workspace_symbols()

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"{'✅' if hover_ok else '❌'} hover: {'Working' if hover_ok else 'NOT working'}")
    print(f"{'✅' if doc_symbols_ok else '❌'} document_symbols: {'Working' if doc_symbols_ok else 'NOT working'}")
    print(f"{'✅' if workspace_symbols_ok else '❌'} workspace_symbols: {'Working' if workspace_symbols_ok else 'NOT working'}")

    all_ok = hover_ok and doc_symbols_ok and workspace_symbols_ok

    if all_ok:
        print("\n✅ VERDICT: All LSP tools work against real ty!")
    else:
        print("\n⚠️  VERDICT: Some LSP tools DO NOT WORK against real ty")
        print("   These tools have NEVER been tested end-to-end until now.")
        print("   The training data and stubs claim they work, but they don't.")


if __name__ == "__main__":
    asyncio.run(main())
