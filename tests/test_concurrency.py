"""ACP concurrency tests.

Tests for concurrent operations and free-threading safety.
"""

import asyncio

import pytest


@pytest.mark.thread_unsafe
async def test_concurrent_file_reads(connect, client):
    """Test 7: Concurrent file operations via asyncio.gather.

    Proves free-threading safety: parallel reads should not interfere.
    """
    # Pre-populate files
    for i in range(5):
        client.files[f"/test/file{i}.txt"] = f"Content {i}"

    client_conn, _ = connect()

    # Define concurrent read operation
    async def read_one(i: int):
        return await client_conn.read_text_file(
            session_id="sess", path=f"/test/file{i}.txt"
        )

    # Execute 5 reads in parallel
    results = await asyncio.gather(*(read_one(i) for i in range(5)))

    # Verify all reads succeeded with correct content
    for i, res in enumerate(results):
        assert res.content == f"Content {i}"
