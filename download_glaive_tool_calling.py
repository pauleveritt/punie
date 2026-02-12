"""Download Glaive Function Calling dataset.

Real tool-calling dataset with function definitions and conversations.

Run: uv run python download_glaive_tool_calling.py
"""

from pathlib import Path

from datasets import load_dataset
from punie.training.dataset import ChatMessage, TrainingDataset, TrainingExample
from punie.training.dataset_io import write_dataset


def main():
    """Download and convert Glaive function calling dataset."""
    print("=" * 70)
    print("📥 Downloading Glaive Function Calling Dataset")
    print("=" * 70)

    print("\nDataset: glaiveai/glaive-function-calling-v2")
    print("License: Apache 2.0")
    print("Type: Real function calling examples")

    print("\nDownloading 500 examples...")
    print("(This may take 2-3 minutes)")
    print("-" * 70)

    dataset = load_dataset(
        "glaiveai/glaive-function-calling-v2",
        split="train",
        streaming=True
    )

    examples = []
    for i, item in enumerate(dataset):
        if i >= 500:
            break

        # Extract system message and chat
        system_msg = item.get("system", "")
        chat = item.get("chat", "")

        # Skip if malformed
        if len(system_msg) < 10 or len(chat) < 10:
            continue

        # Parse chat into user/assistant messages
        # Format: "USER: ...\n\nASSISTANT: ..."
        parts = chat.split("\n\nASSISTANT:")

        if len(parts) != 2:
            continue

        user_part = parts[0].replace("USER:", "").strip()
        assistant_part = parts[1].strip()

        # Create training example
        messages = (
            ChatMessage(role="system", content=system_msg),
            ChatMessage(role="user", content=user_part),
            ChatMessage(role="assistant", content=assistant_part),
        )

        examples.append(TrainingExample(messages=messages))

        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1} items, kept {len(examples)} examples...")

    print(f"\n✅ Downloaded {len(examples)} examples")

    # Split 80/10/10
    total = len(examples)
    train_end = int(total * 0.8)
    valid_end = int(total * 0.9)

    dataset = TrainingDataset(
        name="glaive-function-calling",
        version="v2",
        train=tuple(examples[:train_end]),
        valid=tuple(examples[train_end:valid_end]),
        test=tuple(examples[valid_end:]),
    )

    output_dir = Path("data/downloaded/glaive-function-calling")
    write_dataset(dataset, output_dir)

    print(f"\n📊 Dataset Split:")
    print(f"   Train: {len(dataset.train)} examples")
    print(f"   Valid: {len(dataset.valid)} examples")
    print(f"   Test: {len(dataset.test)} examples")

    print(f"\n✅ Saved to: {output_dir}/")

    # Show first example
    if dataset.train:
        first = dataset.train[0]
        print(f"\n📝 Example:")
        print(f"   System: {first.messages[0].content[:100]}...")
        print(f"   User: {first.messages[1].content[:100]}...")
        print(f"   Assistant: {first.messages[2].content[:100]}...")

    print("\n💡 This is REAL tool-calling data:")
    print("   - Actual function definitions")
    print("   - Real user requests")
    print("   - Proper function calling responses")

    print("\n" + "=" * 70)
    print("Ready to train on real tool-calling data!")
    print("=" * 70)


if __name__ == "__main__":
    main()
