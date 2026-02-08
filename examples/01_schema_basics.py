"""Example 01: ACP Schema Basics

Demonstrates basic ACP schema model construction, serialization, and deserialization.

This example shows:
- Creating ACP schema models (InitializeResponse, TextContentBlock)
- Serializing models to dictionaries with model_dump()
- Deserializing dictionaries back to models with model_validate()
- Roundtrip serialization preserves all fields

Tier: 1 (Sync, schema-only)
"""

from acp.schema import InitializeResponse, TextContentBlock


def main() -> None:
    """Demonstrate schema model construction and serialization roundtrips."""

    # Create an InitializeResponse model
    init_response = InitializeResponse(protocol_version=1)
    assert init_response.protocol_version == 1

    # Serialize to dict
    data = init_response.model_dump()
    assert isinstance(data, dict)
    assert data["protocol_version"] == 1

    # Deserialize back to model
    restored = InitializeResponse.model_validate(data)
    assert restored.protocol_version == 1
    assert restored == init_response

    # TextContentBlock roundtrip
    text_block = TextContentBlock(type="text", text="Hello, ACP!")
    assert text_block.type == "text"
    assert text_block.text == "Hello, ACP!"

    # Serialize and deserialize
    block_data = text_block.model_dump()
    restored_block = TextContentBlock.model_validate(block_data)
    assert restored_block.type == text_block.type
    assert restored_block.text == text_block.text
    assert restored_block == text_block

    print("✓ All schema basics verified")


if __name__ == "__main__":
    main()
