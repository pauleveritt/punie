"""Free-threading safety tests for Python 3.14.2t.

These tests verify that Punie's critical dependencies (Pydantic, ACP models)
are safe under Python 3.14.2t's free-threaded mode with the GIL disabled.

Tests use ThreadPoolExecutor with synchronized starts (via Barrier) and
aggressive context switching to maximize contention and catch race conditions.

Test strategy follows py-free-threading.github.io/testing/ guidelines:
- Use threading.Barrier for synchronized thread starts
- Set sys.setswitchinterval(0.000001) to force frequent context switches
- Run operations across 10+ threads with many iterations
- Verify both correctness and absence of crashes/hangs

These tests work standalone OR with --parallel-threads for N×M contention.
"""

import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import pytest

from acp.schema import InitializeResponse, ToolCallLocation


def _run_threaded(fn: Callable[[int], None], num_threads: int = 10) -> None:
    """Execute fn(thread_index) across num_threads with synchronized starts.

    Args:
        fn: Function taking thread_index (0..num_threads-1) as argument
        num_threads: Number of threads to spawn (default 10)

    This helper:
    1. Creates a Barrier so all threads start simultaneously
    2. Sets aggressive context switching (1µs) to maximize race conditions
    3. Runs fn in ThreadPoolExecutor
    4. Collects exceptions and re-raises the first one
    5. Restores original switch interval

    Pattern from: https://py-free-threading.github.io/testing/
    """
    barrier = threading.Barrier(num_threads)
    original_interval = sys.getswitchinterval()
    sys.setswitchinterval(0.000001)  # Force context switches every 1µs

    def wrapped(thread_idx: int) -> None:
        barrier.wait()  # Synchronize all threads
        fn(thread_idx)

    try:
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(wrapped, i) for i in range(num_threads)]
            # Collect exceptions
            exceptions = []
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    exceptions.append(e)
            if exceptions:
                raise exceptions[0]
    finally:
        sys.setswitchinterval(original_interval)


@pytest.mark.freethreaded
def test_pydantic_model_create_parallel():
    """Test 1: InitializeResponse construction across threads.

    Proves Pydantic model instantiation is thread-safe under 3.14t.
    Each thread creates 50 models to stress allocation/validation.
    """

    def create_models(_thread_idx: int):
        for i in range(50):
            model = InitializeResponse(
                protocol_version=1,
                agent_capabilities=None,
                auth_methods=[],
            )
            assert model.protocol_version == 1

    _run_threaded(create_models, num_threads=10)


@pytest.mark.freethreaded
def test_pydantic_model_dump_parallel():
    """Test 2: model_dump() and model_validate() roundtrip across threads.

    Proves Pydantic serialization/deserialization is thread-safe.
    Critical for ACP message encoding/decoding.
    """
    # Pre-create model outside threads (shared immutable read)
    model = InitializeResponse(
        protocol_version=1,
        agent_capabilities=None,
        auth_methods=[],
    )

    def dump_and_validate(_thread_idx: int):
        for i in range(50):
            data = model.model_dump()
            reconstructed = InitializeResponse.model_validate(data)
            assert reconstructed.protocol_version == 1

    _run_threaded(dump_and_validate, num_threads=10)


@pytest.mark.freethreaded
def test_pydantic_model_validate_parallel():
    """Test 3: model_validate() from dict across threads.

    Proves Pydantic validation from raw data is thread-safe.
    Each thread validates from its own dict to test independent operations.
    """
    data = {
        "protocol_version": 1,
        "agent_capabilities": None,
        "auth_methods": [],
    }

    def validate_from_dict(_thread_idx: int):
        for i in range(50):
            model = InitializeResponse.model_validate(data)
            assert model.protocol_version == 1

    _run_threaded(validate_from_dict, num_threads=10)


@pytest.mark.freethreaded
def test_shared_list_append_parallel():
    """Test 4: Python list.append thread-safety under 3.14t.

    Proves built-in list operations are safe under per-object locking.
    10 threads × 100 appends = 1000 elements total.
    """
    shared_list = []

    def append_items(thread_idx: int):
        for i in range(100):
            shared_list.append((thread_idx, i))

    _run_threaded(append_items, num_threads=10)

    # Verify all 1000 items present
    assert len(shared_list) == 1000
    # Verify all thread indices represented
    thread_ids = {item[0] for item in shared_list}
    assert thread_ids == set(range(10))


@pytest.mark.freethreaded
def test_shared_dict_update_parallel():
    """Test 5: Python dict.__setitem__ thread-safety under 3.14t.

    Proves built-in dict operations are safe under per-object locking.
    10 threads × 100 updates = 1000 unique keys.
    """
    shared_dict = {}

    def update_dict(thread_idx: int):
        for i in range(100):
            key = f"thread_{thread_idx}_item_{i}"
            shared_dict[key] = (thread_idx, i)

    _run_threaded(update_dict, num_threads=10)

    # Verify all 1000 keys present
    assert len(shared_dict) == 1000
    # Verify sample values correct
    assert shared_dict["thread_0_item_0"] == (0, 0)
    assert shared_dict["thread_9_item_99"] == (9, 99)


@pytest.mark.freethreaded
def test_tool_call_location_create_parallel():
    """Test 6: ToolCallLocation model creation across threads.

    Proves ACP's ToolCallLocation (critical for PyCharm integration)
    is thread-safe under parallel construction.
    """

    def create_locations(thread_idx: int):
        for i in range(50):
            location = ToolCallLocation(
                path=f"/project/file_{thread_idx}_{i}.py",
            )
            assert location.path == f"/project/file_{thread_idx}_{i}.py"

    _run_threaded(create_locations, num_threads=10)
