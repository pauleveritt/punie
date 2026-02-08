"""Example: Using local MLX models for offline development.

This example demonstrates how to use MLX models for fully local, offline AI
development on Apple Silicon Macs. No API calls, no internet required.

Requirements:
    - macOS with Apple Silicon (arm64)
    - mlx-lm installed: uv pip install 'punie[local]'
    - Model downloaded (mlx-lm downloads automatically on first use)

Usage:
    uv run examples/15_mlx_local_model.py
"""

import platform
import sys

# Platform guard - MLX only works on macOS arm64
if platform.system() != "Darwin" or platform.machine() != "arm64":
    print("ERROR: MLX models require macOS with Apple Silicon (arm64)")
    print(f"Current platform: {platform.system()} {platform.machine()}")
    sys.exit(1)


def example_direct_model_creation():
    """Example 1: Create MLXModel directly."""
    print("\n=== Example 1: Direct MLXModel Creation ===\n")

    try:
        from punie.models.mlx import MLXModel

        # Create model with default Qwen 7B 4-bit quantized model
        print("Loading mlx-community/Qwen2.5-Coder-7B-Instruct-4bit...")
        print("(First run will download ~4GB model)")

        model = MLXModel.from_pretrained("mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")

        print(f"Model loaded: {model.model_name}")
        print(f"System: {model.system}")

    except ImportError as e:
        print(f"ERROR: {e}")
        print("\nInstall mlx-lm with: uv pip install 'punie[local]'")
        return


def example_agent_with_local_model():
    """Example 2: Create Pydantic AI agent with local model."""
    print("\n=== Example 2: Agent with Local Model ===\n")

    try:
        from punie.agent.factory import create_pydantic_agent

        # Use model='local' for default MLX model
        print("Creating agent with model='local'...")
        agent = create_pydantic_agent(model="local")

        print(f"Agent created with model: {agent._model.model_name}")
        print(f"Agent has {len(agent._function_tools)} tools available")

        # Note: To actually run the agent, you need ACPDeps with a client connection
        # This example just demonstrates model setup

    except ImportError as e:
        print(f"ERROR: {e}")
        print("\nInstall mlx-lm with: uv pip install 'punie[local]'")
        return


def example_custom_model_name():
    """Example 3: Use custom MLX model."""
    print("\n=== Example 3: Custom Model Name ===\n")

    try:
        from punie.agent.factory import create_pydantic_agent

        # Use 'local:model-name' to specify a different model
        custom_model = "mlx-community/Qwen2.5-Coder-3B-Instruct-4bit"
        print(f"Creating agent with model='local:{custom_model}'...")

        agent = create_pydantic_agent(model=f"local:{custom_model}")

        print(f"Agent created with custom model: {agent._model.model_name}")

    except ImportError as e:
        print(f"ERROR: {e}")
        print("\nInstall mlx-lm with: uv pip install 'punie[local]'")
        return


def example_model_info():
    """Example 4: Display available MLX models info."""
    print("\n=== Example 4: Recommended MLX Models ===\n")

    print("Recommended models for local development:")
    print()
    print("1. Qwen2.5-Coder-7B-Instruct-4bit (default)")
    print("   - Size: ~4GB")
    print("   - Memory: 8GB+ recommended")
    print("   - Quality: Excellent for coding tasks")
    print("   - Model: mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")
    print()
    print("2. Qwen2.5-Coder-3B-Instruct-4bit (faster, smaller)")
    print("   - Size: ~2GB")
    print("   - Memory: 6GB+ recommended")
    print("   - Quality: Good for simple tasks")
    print("   - Model: mlx-community/Qwen2.5-Coder-3B-Instruct-4bit")
    print()
    print("3. Qwen2.5-Coder-14B-Instruct-4bit (best quality)")
    print("   - Size: ~8GB")
    print("   - Memory: 16GB+ recommended")
    print("   - Quality: Best, but slower")
    print("   - Model: mlx-community/Qwen2.5-Coder-14B-Instruct-4bit")
    print()
    print("Find more models at: https://huggingface.co/mlx-community")
    print()
    print("Note: Tool calling requires models with tool-aware chat templates.")
    print("      Qwen2.5-Coder series has excellent tool calling support.")


if __name__ == "__main__":
    print("=" * 70)
    print("MLX Local Model Examples")
    print("=" * 70)

    example_model_info()
    example_direct_model_creation()
    example_agent_with_local_model()
    example_custom_model_name()

    print("\n" + "=" * 70)
    print("Examples complete!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Set PUNIE_MODEL=local environment variable")
    print("  2. Run: punie serve")
    print("  3. Connect from PyCharm for fully local AI coding!")
    print()
