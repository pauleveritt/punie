#!/usr/bin/env python3
"""Compare 5-bit vs 6-bit Phase 26 models with isolated runs.

Runs each model in a separate process to avoid memory contamination.
Measures:
- Warm-up time (first query)
- Steady-state average (Q2-Q5)
- Memory usage
- Accuracy

Addresses Finding 5d: Previous benchmarks ran multiple models in same session,
causing memory pressure and thermal effects.
"""

import json
import subprocess
import sys
from pathlib import Path


def run_single_model_benchmark(model_path: str) -> dict | None:
    """Run benchmark for a single model in isolated process.

    Args:
        model_path: Path to model directory

    Returns:
        Benchmark results dict or None if failed
    """
    print(f"\nBenchmarking {model_path} in isolated process...")
    print("-" * 80)

    # Run benchmark_phases.py with just this model
    # Use a temporary script that benchmarks a single model
    script = f"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import after path setup
from scripts.benchmark_phases import benchmark_model
import mlx.core as mx

result = benchmark_model("{model_path}", verbose=True)

# Clear memory
mx.metal.clear_cache()

# Print result as JSON
import json
print("\\n__RESULT_START__")
print(json.dumps(result))
print("__RESULT_END__")
"""

    try:
        result = subprocess.run(
            ["uv", "run", "python", "-c", script],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes max
        )

        # Extract JSON result
        output = result.stdout
        if "__RESULT_START__" in output and "__RESULT_END__" in output:
            start = output.index("__RESULT_START__") + len("__RESULT_START__")
            end = output.index("__RESULT_END__")
            json_str = output[start:end].strip()
            return json.loads(json_str)
        else:
            print("Error: Could not parse result from output")
            print(f"stdout: {output}")
            print(f"stderr: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        print("Error: Benchmark timed out after 5 minutes")
        return None
    except Exception as e:
        print(f"Error running benchmark: {e}")
        return None


def print_comparison(result_5bit: dict, result_6bit: dict) -> None:
    """Print detailed comparison between 5-bit and 6-bit models."""
    print("\n" + "="*80)
    print("5-BIT VS 6-BIT COMPARISON")
    print("="*80)
    print()

    # Table header
    print(f"{'Metric':<25} {'5-bit':<15} {'6-bit':<15} {'Difference':<15}")
    print("-" * 80)

    # Disk size
    disk_5 = result_5bit["disk_size_gb"]
    disk_6 = result_6bit["disk_size_gb"]
    disk_diff = ((disk_5 - disk_6) / disk_6 * 100)
    print(f"{'Disk size (GB)':<25} {disk_5:>13.2f}  {disk_6:>13.2f}  {disk_diff:>+13.1f}%")

    # Memory
    mem_5 = result_5bit["memory_gb"]
    mem_6 = result_6bit["memory_gb"]
    mem_diff = ((mem_5 - mem_6) / mem_6 * 100)
    print(f"{'Memory (GB)':<25} {mem_5:>13.2f}  {mem_6:>13.2f}  {mem_diff:>+13.1f}%")

    # Load time
    load_5 = result_5bit["load_time_s"]
    load_6 = result_6bit["load_time_s"]
    load_diff = ((load_5 - load_6) / load_6 * 100)
    print(f"{'Load time (s)':<25} {load_5:>13.2f}  {load_6:>13.2f}  {load_diff:>+13.1f}%")

    # Warm-up time
    warmup_5 = result_5bit["warmup_time_s"]
    warmup_6 = result_6bit["warmup_time_s"]
    warmup_diff = ((warmup_5 - warmup_6) / warmup_6 * 100)
    print(f"{'Warm-up time (s)':<25} {warmup_5:>13.2f}  {warmup_6:>13.2f}  {warmup_diff:>+13.1f}%")

    # Steady-state (the key metric!)
    steady_5 = result_5bit["steady_state_avg_s"]
    steady_6 = result_6bit["steady_state_avg_s"]
    steady_diff = ((steady_5 - steady_6) / steady_6 * 100)
    is_significant = abs(steady_diff) > 5  # More than 5% difference
    marker = " ⚠ SIGNIFICANT" if is_significant else " ≈ EQUIVALENT"
    print(f"{'Steady-state avg (s)':<25} {steady_5:>13.2f}  {steady_6:>13.2f}  {steady_diff:>+13.1f}%{marker}")

    # Accuracy
    acc_5 = result_5bit["accuracy_pct"]
    acc_6 = result_6bit["accuracy_pct"]
    acc_diff = acc_5 - acc_6
    print(f"{'Accuracy (%)':<25} {acc_5:>13.0f}  {acc_6:>13.0f}  {acc_diff:>+13.0f} pts")

    print("-" * 80)
    print()

    # Summary
    print("SUMMARY:")
    print()
    print("Size advantage:")
    print(f"  5-bit is {abs(disk_diff):.1f}% {'smaller' if disk_diff < 0 else 'larger'} on disk")
    print(f"  5-bit uses {abs(mem_diff):.1f}% {'less' if mem_diff < 0 else 'more'} memory")
    print()

    print("Speed analysis:")
    print(f"  Warm-up: 5-bit is {abs(warmup_diff):.1f}% {'faster' if warmup_diff < 0 else 'slower'} (one-time cost)")
    print(f"  Steady-state: 5-bit is {abs(steady_diff):.1f}% {'faster' if steady_diff < 0 else 'slower'} (per-query)")
    if not is_significant:
        print("  ✓ Steady-state speeds are statistically equivalent (within 5%)")
    else:
        print("  ⚠ Steady-state speeds differ by more than 5% - investigate")
    print()

    print("Quality:")
    if acc_diff == 0:
        print(f"  ✓ Accuracy is identical ({acc_5:.0f}%)")
    elif abs(acc_diff) <= 4:  # 1 query difference in 25-query test
        print(f"  ≈ Accuracy difference is {abs(acc_diff):.0f} points (not statistically significant in n=25)")
    else:
        print(f"  ⚠ Accuracy differs by {abs(acc_diff):.0f} points - investigate")
    print()

    print("RECOMMENDATION:")
    if not is_significant and disk_diff < 0:
        print("  ✓ Deploy 5-bit: Smaller size, equivalent speed/quality")
    elif not is_significant and disk_diff > 0:
        print("  ✓ Deploy 6-bit: Equivalent speed/quality, if size isn't critical")
    elif is_significant and steady_diff < 0:
        print("  ✓ Deploy 5-bit: Significantly faster")
    elif is_significant and steady_diff > 0:
        print("  ⚠ Consider 6-bit: Significantly faster than 5-bit")
    else:
        print("  ⚠ Results inconclusive - run more tests")
    print()


def main():
    """Compare 5-bit vs 6-bit models."""
    model_5bit = "fused_model_qwen3_phase26_5bit"
    model_6bit = "fused_model_qwen3_phase26_6bit"

    # Check both exist
    if not Path(model_5bit).exists():
        print(f"Error: {model_5bit} not found")
        sys.exit(1)
    if not Path(model_6bit).exists():
        print(f"Error: {model_6bit} not found")
        sys.exit(1)

    print("="*80)
    print("5-BIT VS 6-BIT ISOLATED BENCHMARK")
    print("="*80)
    print()
    print("Running each model in a separate process to avoid memory contamination.")
    print("This ensures fair comparison of warm-up and steady-state performance.")
    print()

    # Benchmark 5-bit
    result_5bit = run_single_model_benchmark(model_5bit)
    if not result_5bit or "error" in result_5bit:
        print("Error: 5-bit benchmark failed")
        sys.exit(1)

    # Benchmark 6-bit
    result_6bit = run_single_model_benchmark(model_6bit)
    if not result_6bit or "error" in result_6bit:
        print("Error: 6-bit benchmark failed")
        sys.exit(1)

    # Print comparison
    print_comparison(result_5bit, result_6bit)

    # Save results
    output = {
        "5bit": result_5bit,
        "6bit": result_6bit,
    }

    output_file = Path("logs/phase26_5bit_vs_6bit_comparison.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w") as f:
        json.dump(output, f, indent=2)

    print(f"Full results saved to: {output_file}")


if __name__ == "__main__":
    main()
