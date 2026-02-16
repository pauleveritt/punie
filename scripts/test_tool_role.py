"""Test if Qwen3 tokenizer handles role: 'tool' correctly."""

from transformers import AutoTokenizer

# Load Qwen3 tokenizer
tokenizer = AutoTokenizer.from_pretrained(
    "fused_model_qwen3_phase27_augmented_5bit",
    trust_remote_code=True,
)

# Test message with role: "tool"
messages = [
    {"role": "system", "content": "You are Punie, an AI coding assistant."},
    {"role": "user", "content": "Check types in src/"},
    {"role": "assistant", "content": "<tool_call>result = typecheck('src/')</tool_call>"},
    {"role": "tool", "content": "<tool_response>TypeCheckResult(...)</tool_response>"},
    {"role": "assistant", "content": "All types are correct!"},
]

try:
    # Apply chat template
    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False,
    )

    print("✅ SUCCESS: Tokenizer handles role: 'tool' correctly")
    print("\nFormatted prompt:")
    print(prompt)

except Exception as e:
    print("❌ ERROR: Tokenizer failed on role: 'tool'")
    print(f"Error: {e}")
    print("\nThis means we need to convert those 60 examples to use role: 'user' instead")
