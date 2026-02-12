"""Check if Qwen3-Coder-30B model exists and get its details.

Run: uv run python check_30b_model.py
"""

import sys

try:
    from huggingface_hub import model_info
except ImportError:
    print("❌ huggingface_hub not installed")
    print("   Run: uv add --dev huggingface-hub")
    sys.exit(1)


def main():
    """Check model availability."""
    model_path = "mlx-community/Qwen3-Coder-30B-A3B-Instruct-4bit"

    print("=" * 70)
    print("🔍 Checking Model Availability")
    print("=" * 70)
    print(f"\nModel: {model_path}")

    try:
        info = model_info(model_path)

        print("\n✅ Model found!")
        print(f"\nDetails:")
        print(f"  Model ID: {info.id}")
        print(f"  Author: {info.author or 'N/A'}")
        print(f"  Downloads: {info.downloads:,}" if info.downloads else "  Downloads: N/A")

        if info.siblings:
            total_size = sum(
                f.size for f in info.siblings if hasattr(f, "size") and f.size
            )
            print(f"  Total size: {total_size / (1024**3):.2f} GB")

            print(f"\n  Files ({len(info.siblings)}):")
            for f in sorted(info.siblings, key=lambda x: x.rfilename)[:10]:
                if hasattr(f, "size") and f.size:
                    size_mb = f.size / (1024**2)
                    print(f"    - {f.rfilename}: {size_mb:.1f} MB")
            if len(info.siblings) > 10:
                print(f"    ... and {len(info.siblings) - 10} more files")

        print("\n💡 This model will be downloaded (~15GB) on first use")
        print("   Benchmark will take several minutes to run")

        print("\n" + "=" * 70)
        print("Ready to benchmark!")
        print("Run: uv run python benchmark_30b_model.py")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ Model not found or error: {e}")
        print("\n💡 Checking alternative models...")

        alternatives = [
            "mlx-community/Qwen2.5-Coder-32B-Instruct-4bit",
            "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
            "mlx-community/Qwen2.5-Coder-14B-Instruct-4bit",
        ]

        for alt in alternatives:
            try:
                alt_info = model_info(alt)
                print(f"\n✅ Found: {alt}")
                if alt_info.siblings:
                    total_size = sum(
                        f.size
                        for f in alt_info.siblings
                        if hasattr(f, "size") and f.size
                    )
                    print(f"   Size: {total_size / (1024**3):.2f} GB")
            except Exception:
                print(f"\n❌ Not available: {alt}")


if __name__ == "__main__":
    main()
