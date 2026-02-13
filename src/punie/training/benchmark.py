"""Training speed benchmarking for LoRA fine-tuning."""

import asyncio
import json
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BenchmarkResult:
    """Results from a training speed benchmark run."""

    model_path: str
    seconds_per_iter: float
    total_seconds: float
    num_iters: int
    peak_memory_gb: float | None  # From psutil if available


def create_dummy_dataset(directory: Path, num_examples: int = 5) -> None:
    """Create a tiny training dataset for benchmarking.

    Writes train/valid/test JSONL files with simple chat-completion examples.
    This is NOT for actual training - just for measuring training speed.

    Args:
        directory: Output directory for dataset files
        num_examples: Number of examples per split (default: 5, very small)
    """
    directory.mkdir(parents=True, exist_ok=True)

    # Simple chat-completion examples for benchmarking
    example_template = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is 2+2?"},
            {"role": "assistant", "content": "2+2 equals 4."},
        ]
    }

    # Write same example multiple times (content doesn't matter for benchmarking)
    for split in ["train", "valid", "test"]:
        output_file = directory / f"{split}.jsonl"
        with output_file.open("w") as f:
            for _ in range(num_examples):
                f.write(json.dumps(example_template) + "\n")


async def run_training_benchmark(
    model_path: str,
    num_iters: int = 10,
    data_dir: Path | None = None,
) -> BenchmarkResult:
    """Run a training speed benchmark with mlx_lm.lora.

    Creates a dummy dataset, runs LoRA training for a small number of iterations,
    and measures wall-clock time per iteration.

    Args:
        model_path: Model to benchmark (e.g., "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit")
        num_iters: Number of training iterations (default: 10, should be quick)
        data_dir: Optional directory with existing dataset. If None, creates dummy data in temp dir.

    Returns:
        BenchmarkResult with timing and memory measurements

    Raises:
        subprocess.CalledProcessError: If training fails
        FileNotFoundError: If mlx_lm is not installed
    """
    # Create or use existing dataset
    if data_dir is None:
        import tempfile

        temp_dir = Path(tempfile.mkdtemp())
        data_dir = temp_dir / "benchmark_data"
        create_dummy_dataset(data_dir, num_examples=5)

    # Build training command (matches train_runner.py format)
    cmd = [
        "python",
        "-m",
        "mlx_lm",
        "lora",
        "--model",
        model_path,
        "--train",
        "--data",
        str(data_dir),
        "--iters",
        str(num_iters),
        "--adapter-path",
        tempfile.mkdtemp(),  # Throw-away output (auto-cleaned by OS)
    ]

    # Run training and measure time
    start_time = time.perf_counter()

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise subprocess.CalledProcessError(
            proc.returncode or 1,
            cmd,
            output=stdout,
            stderr=stderr,
        )

    end_time = time.perf_counter()
    total_seconds = end_time - start_time
    seconds_per_iter = total_seconds / num_iters

    # Try to get memory info (optional)
    peak_memory_gb: float | None = None
    try:
        import psutil

        process = psutil.Process()
        peak_memory_gb = process.memory_info().rss / (1024**3)
    except ImportError:
        pass

    return BenchmarkResult(
        model_path=model_path,
        seconds_per_iter=seconds_per_iter,
        total_seconds=total_seconds,
        num_iters=num_iters,
        peak_memory_gb=peak_memory_gb,
    )
