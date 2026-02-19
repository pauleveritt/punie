#!/usr/bin/env python3
"""Select the best LoRA checkpoint based on validation loss.

Parses training log for 'Val loss X.XXX' entries, finds the iteration with
lowest val loss, maps to the nearest saved checkpoint, and copies it to
adapters.safetensors (backing up the original final checkpoint).

Usage:
    uv run python scripts/select_best_checkpoint.py \\
        --log logs/phase44_training.log \\
        --adapter-dir adapters_phase44 \\
        --save-every 100
"""

import argparse
import re
import shutil
import sys
from pathlib import Path


def parse_val_losses(log_path: Path) -> list[tuple[int, float]]:
    """Parse training log and return list of (iteration, val_loss) pairs."""
    # Matches lines like:
    #   Iter 100: Val loss 0.234, Val took 5.432s.
    #   Iter 200: Val loss 0.187, ...
    pattern = re.compile(r"Iter\s+(\d+):\s+Val loss\s+([\d.]+)")
    results = []
    for line in log_path.read_text().splitlines():
        m = pattern.search(line)
        if m:
            iteration = int(m.group(1))
            val_loss = float(m.group(2))
            results.append((iteration, val_loss))
    return results


def find_best_iteration(val_losses: list[tuple[int, float]]) -> tuple[int, float]:
    """Return the (iteration, val_loss) with the lowest val_loss."""
    return min(val_losses, key=lambda x: x[1])


def nearest_checkpoint(iteration: int, save_every: int) -> int:
    """Round iteration down to nearest saved checkpoint multiple."""
    # Checkpoints are saved at multiples of save_every.
    # Round down to the nearest multiple (the last checkpoint before this iteration).
    return (iteration // save_every) * save_every


def find_checkpoint_file(adapter_dir: Path, checkpoint_iter: int) -> Path | None:
    """Find the checkpoint file for a given iteration."""
    # mlx_lm saves checkpoints as: adapters/0000100_adapters.safetensors
    # or sometimes: adapters/adapters_100.safetensors
    # Try multiple naming conventions.
    candidates = [
        adapter_dir / f"{checkpoint_iter:07d}_adapters.safetensors",
        adapter_dir / f"adapters_{checkpoint_iter}.safetensors",
        adapter_dir / f"{checkpoint_iter}_adapters.safetensors",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def main() -> int:
    p = argparse.ArgumentParser(description="Select best LoRA checkpoint by val loss")
    p.add_argument("--log", required=True, help="Path to training log file")
    p.add_argument("--adapter-dir", required=True, help="Adapter directory")
    p.add_argument("--save-every", type=int, default=100, help="Checkpoint save interval")
    p.add_argument("--dry-run", action="store_true", help="Show what would be done without copying")
    args = p.parse_args()

    log_path = Path(args.log)
    adapter_dir = Path(args.adapter_dir)

    if not log_path.exists():
        print(f"ERROR: Log file not found: {log_path}")
        return 1
    if not adapter_dir.exists():
        print(f"ERROR: Adapter directory not found: {adapter_dir}")
        return 1

    # Parse validation losses from log
    val_losses = parse_val_losses(log_path)
    if not val_losses:
        print(f"ERROR: No 'Val loss' entries found in {log_path}")
        print("  Expected lines like: 'Iter 100: Val loss 0.234, ...'")
        return 1

    print(f"Found {len(val_losses)} validation checkpoints in log:")
    for iteration, loss in val_losses:
        print(f"  Iter {iteration:5d}: val_loss = {loss:.4f}")

    # Find best
    best_iter, best_loss = find_best_iteration(val_losses)
    print(f"\nBest val_loss: {best_loss:.4f} at iter {best_iter}")

    # Map to nearest saved checkpoint
    checkpoint_iter = nearest_checkpoint(best_iter, args.save_every)
    if checkpoint_iter == 0:
        # If best was before first checkpoint, use first checkpoint
        checkpoint_iter = args.save_every
    print(f"Nearest saved checkpoint: iter {checkpoint_iter} (save_every={args.save_every})")

    # Find the checkpoint file
    checkpoint_file = find_checkpoint_file(adapter_dir, checkpoint_iter)
    if checkpoint_file is None:
        print(f"ERROR: Checkpoint file not found for iter {checkpoint_iter} in {adapter_dir}")
        print(f"  Searched for: {checkpoint_iter:07d}_adapters.safetensors, adapters_{checkpoint_iter}.safetensors")
        print("  Available files:")
        for f in sorted(adapter_dir.iterdir()):
            print(f"    {f.name}")
        return 1

    print(f"Checkpoint file: {checkpoint_file}")

    # Backup final adapters.safetensors and replace with best checkpoint
    final_adapter = adapter_dir / "adapters.safetensors"
    backup_adapter = adapter_dir / "adapters_final.safetensors"

    if args.dry_run:
        print(f"\n[DRY RUN] Would copy {checkpoint_file} → {final_adapter}")
        if final_adapter.exists():
            print(f"[DRY RUN] Would backup {final_adapter} → {backup_adapter}")
        return 0

    if final_adapter.exists():
        print(f"\nBacking up {final_adapter.name} → {backup_adapter.name}")
        shutil.copy2(final_adapter, backup_adapter)

    print(f"Copying best checkpoint → {final_adapter.name}")
    shutil.copy2(checkpoint_file, final_adapter)

    print(f"\nDone: adapters.safetensors now points to iter {checkpoint_iter} (val_loss={best_loss:.4f})")
    print(f"  Original final checkpoint backed up to: {backup_adapter.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
