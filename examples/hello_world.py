"""Hello world example for Punie.

This example demonstrates:
- Basic punie package import
- Verifying package structure
- Self-testing example pattern
"""

import punie


def main() -> None:
    """Verify basic punie package access."""
    # Check package name
    assert punie.__name__ == "punie"

    # Create a greeting using the package
    greeting = f"Hello from {punie.__name__}!"

    # Verify greeting content
    assert "Hello" in greeting
    assert "punie" in greeting

    print(greeting)


if __name__ == "__main__":
    main()
    print("Hello world example passed!")
