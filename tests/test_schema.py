"""ACP schema model tests.

Tests basic Pydantic model serialization and deserialization.
"""

from punie.acp.schema import InitializeResponse, TextContentBlock


def test_acp_schema_model_roundtrip():
    """Test 1: Pydantic schema models serialize/deserialize under 3.14t.

    Sync test proving basic Pydantic functionality works.
    No fixtures needed—this is pure schema validation.
    """
    # Create a response model
    init_response = InitializeResponse(
        protocol_version=1, agent_capabilities=None, auth_methods=[]
    )
    assert init_response.protocol_version == 1

    # Serialize to dict
    data = init_response.model_dump()
    assert data["protocol_version"] == 1

    # Deserialize back
    reconstructed = InitializeResponse.model_validate(data)
    assert reconstructed.protocol_version == 1

    # Test content blocks
    text_block = TextContentBlock(type="text", text="Hello, 3.14t!")
    assert text_block.text == "Hello, 3.14t!"
    text_data = text_block.model_dump()
    text_reconstructed = TextContentBlock.model_validate(text_data)
    assert text_reconstructed.text == "Hello, 3.14t!"
