"""Memory monitoring utilities for model loading.

Provides memory snapshot and availability checks to warn users before
loading models that may exceed available memory.
"""

import os
import resource
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class MemorySnapshot:
    """Point-in-time memory usage measurement.

    Uses resource.getrusage() for RSS (Resident Set Size) metrics.
    macOS reports in bytes; Linux reports in KB.
    """

    rss_bytes: int  # Resident Set Size (actual RAM used)
    rss_mb: float  # RSS in megabytes
    peak_rss_bytes: int  # Peak RSS (max RSS since process start)
    peak_rss_mb: float  # Peak RSS in megabytes


def get_memory_snapshot() -> MemorySnapshot:
    """Get current process memory usage via resource.getrusage().

    Uses stdlib resource module (no extra dependency).
    macOS getrusage reports in bytes; Linux reports in KB.

    Returns:
        MemorySnapshot with current memory usage

    Example:
        >>> snapshot = get_memory_snapshot()
        >>> snapshot.rss_mb > 0  # Should have positive memory usage
        True
        >>> snapshot.rss_bytes == int(snapshot.rss_mb * 1024 * 1024)
        True
    """
    usage = resource.getrusage(resource.RUSAGE_SELF)

    # macOS reports ru_maxrss in bytes; Linux reports in KB
    if sys.platform == "darwin":
        rss_bytes = usage.ru_maxrss
        peak_rss_bytes = usage.ru_maxrss
    else:
        rss_bytes = usage.ru_maxrss * 1024
        peak_rss_bytes = usage.ru_maxrss * 1024

    return MemorySnapshot(
        rss_bytes=rss_bytes,
        rss_mb=rss_bytes / (1024 * 1024),
        peak_rss_bytes=peak_rss_bytes,
        peak_rss_mb=peak_rss_bytes / (1024 * 1024),
    )


def check_memory_available(
    model_size_mb: float,
    safety_margin_mb: float = 1024.0,
) -> tuple[bool, MemorySnapshot]:
    """Check if enough memory is available before model loading.

    Simple heuristic: current RSS + model_size + safety_margin < total system RAM.
    Uses os.sysconf for total RAM on macOS/Linux.

    Args:
        model_size_mb: Estimated model size in megabytes
        safety_margin_mb: Safety margin in megabytes (default: 1GB)

    Returns:
        Tuple of (available: bool, current_snapshot: MemorySnapshot)

    Example:
        >>> available, snapshot = check_memory_available(4096.0)
        >>> if not available:
        ...     print(f"Warning: May not have enough memory (current: {snapshot.rss_mb:.1f} MB)")
    """
    snapshot = get_memory_snapshot()

    # Get total system RAM via sysconf (Unix-only)
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        total_ram_mb = (pages * page_size) / (1024 * 1024)
    except (ValueError, OSError):
        # If sysconf fails, assume we have enough memory (don't block)
        return True, snapshot

    # Simple heuristic: current + model + margin < total
    required_mb = snapshot.rss_mb + model_size_mb + safety_margin_mb
    available = required_mb < total_ram_mb

    return available, snapshot


# Model size estimates for memory checks (in megabytes)
MODEL_SIZES_MB: dict[str, float] = {
    "3B-4bit": 2048.0,  # ~2GB for 3B parameter model at 4-bit quantization
    "7B-4bit": 4096.0,  # ~4GB for 7B parameter model at 4-bit quantization
    "14B-4bit": 8192.0,  # ~8GB for 14B parameter model at 4-bit quantization
}


def estimate_model_size(model_name: str) -> float:
    """Estimate model size from name.

    Looks for patterns like "3B", "7B", "14B" in model name.
    Falls back to 4096MB (7B default) if no pattern matches.

    Args:
        model_name: HuggingFace model name (e.g., "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")

    Returns:
        Estimated model size in megabytes

    Example:
        >>> estimate_model_size("mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")
        4096.0
        >>> estimate_model_size("mlx-community/Qwen2.5-Coder-3B-Instruct-4bit")
        2048.0
    """
    model_name_upper = model_name.upper()

    # Check for parameter count patterns
    if "3B" in model_name_upper:
        return MODEL_SIZES_MB["3B-4bit"]
    if "7B" in model_name_upper:
        return MODEL_SIZES_MB["7B-4bit"]
    if "14B" in model_name_upper:
        return MODEL_SIZES_MB["14B-4bit"]

    # Default to 7B size
    return MODEL_SIZES_MB["7B-4bit"]
