"""Try to download real tool-calling datasets.

Attempts several public tool-calling datasets to find one that's accessible.

Run: uv run python try_download_tool_calling.py
"""

from datasets import load_dataset


def try_dataset(name: str, config: str | None = None) -> bool:
    """Try to load a dataset and show sample.

    Returns True if successful, False if failed.
    """
    print(f"\n{'=' * 70}")
    print(f"Trying: {name}")
    if config:
        print(f"Config: {config}")
    print("-" * 70)

    try:
        if config:
            dataset = load_dataset(name, config, split="train", streaming=True)
        else:
            dataset = load_dataset(name, split="train", streaming=True)

        # Get first example
        first = next(iter(dataset))

        print("✅ SUCCESS - Dataset is accessible!")
        print(f"\nFirst example keys: {list(first.keys())}")
        print(f"\nSample:")
        for key, value in list(first.items())[:5]:
            value_str = str(value)[:200] + "..." if len(str(value)) > 200 else str(value)
            print(f"  {key}: {value_str}")

        return True

    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


def main():
    """Try multiple tool-calling datasets."""
    print("=" * 70)
    print("🔍 Searching for Accessible Tool-Calling Datasets")
    print("=" * 70)

    datasets_to_try = [
        # Glaive - Known to work well
        ("glaiveai/glaive-function-calling-v2", None),

        # Salesforce CodeGen
        ("salesforce/xlam-function-calling-60k", None),

        # NousResearch Hermes
        ("NousResearch/hermes-function-calling-v1", None),

        # Smaller Glaive variant
        ("glaiveai/glaive-function-calling-v1", None),

        # Hugging Face datasets
        ("HuggingFaceH4/no_robots", None),
    ]

    successful = []

    for name, config in datasets_to_try:
        if try_dataset(name, config):
            successful.append(name)

    print("\n" + "=" * 70)
    print("📊 Summary")
    print("=" * 70)
    print(f"\nAttempted: {len(datasets_to_try)} datasets")
    print(f"Successful: {len(successful)} datasets")

    if successful:
        print("\n✅ Accessible datasets:")
        for name in successful:
            print(f"  - {name}")

        print("\n💡 Next step:")
        print("  Choose one and create a downloader function")
        print("  Convert to TrainingExample format")
        print("  Train and evaluate")
    else:
        print("\n❌ No publicly accessible tool-calling datasets found")
        print("\n💡 Alternatives:")
        print("  - Use synthetic data we already created")
        print("  - Capture real Punie agent traces")
        print("  - Use general chat datasets with some tool examples")


if __name__ == "__main__":
    main()
