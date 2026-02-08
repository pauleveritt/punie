"""Example 02: Content Blocks

Demonstrates ACP content block types and helper factory functions.

This example shows:
- Using text_block() factory for TextContentBlock
- Creating ImageContentBlock with type discriminator
- Using update_agent_message_text() and update_user_message_text()
- Understanding session update message chunks

Tier: 1 (Sync, schema-only)
"""

from punie.acp import text_block, update_agent_message_text, update_user_message_text
from punie.acp.schema import ImageContentBlock, TextContentBlock


def main() -> None:
    """Demonstrate content block construction and message chunk factories."""

    # text_block() factory creates TextContentBlock
    block = text_block("Hello from factory")
    assert isinstance(block, TextContentBlock)
    assert block.type == "text"
    assert block.text == "Hello from factory"

    # ImageContentBlock with type discriminator
    image_block = ImageContentBlock(
        type="image", data="base64encodeddata", mime_type="image/png"
    )
    assert image_block.type == "image"
    assert image_block.data == "base64encodeddata"
    assert image_block.mime_type == "image/png"

    # update_agent_message_text() creates AgentMessageChunk
    agent_chunk = update_agent_message_text("Agent says hello")
    assert agent_chunk.session_update == "agent_message_chunk"
    assert agent_chunk.content.text == "Agent says hello"

    # update_user_message_text() creates UserMessageChunk
    user_chunk = update_user_message_text("User says hello")
    assert user_chunk.session_update == "user_message_chunk"
    assert user_chunk.content.text == "User says hello"

    print("✓ All content block patterns verified")


if __name__ == "__main__":
    main()
