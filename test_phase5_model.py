"""Test Phase 5 model: verify tool vs. direct-answer discrimination."""

from mlx_lm import load, generate

# Load the fine-tuned model
model_path = "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
adapter_path = "./adapters"

print("=" * 80)
print("Phase 5 Model Test: Tool vs. Direct Answer Discrimination")
print("=" * 80)

print("\nLoading model...")
model, tokenizer = load(model_path, adapter_path=adapter_path)
print("✓ Model loaded with Phase 5 adapters\n")

# Test queries
test_cases = [
    {
        "query": "What is dependency injection?",
        "expected": "direct",
        "description": "Concept question - should give direct answer"
    },
    {
        "query": "Find all classes that inherit from Protocol",
        "expected": "tool",
        "description": "Search query - should use tool (grep/search)"
    },
    {
        "query": "Show me examples of using Inject",
        "expected": "tool",
        "description": "Read file query - should use tool (read_file)"
    },
    {
        "query": "What is the difference between a Registry and a Container?",
        "expected": "direct",
        "description": "Comparison question - should give direct answer"
    },
    {
        "query": "When should I use svcs vs a DI framework?",
        "expected": "direct",
        "description": "Best practice question - should give direct answer"
    },
]

system_msg = "You are Punie, an AI coding assistant that helps with Python development via PyCharm."

def format_prompt(query: str) -> str:
    """Format query as chat prompt."""
    return f"<|im_start|>system\n{system_msg}<|im_end|>\n<|im_start|>user\n{query}<|im_end|>\n<|im_start|>assistant\n"

def has_tool_call(response: str) -> bool:
    """Check if response contains a tool call."""
    return ("I'll use the" in response or
            "```json" in response and '"name":' in response)

# Run tests
print("-" * 80)
print("TEST RESULTS")
print("-" * 80)

results = {"correct": 0, "incorrect": 0}

for i, test_case in enumerate(test_cases, 1):
    query = test_case["query"]
    expected = test_case["expected"]
    description = test_case["description"]

    print(f"\n{i}. {description}")
    print(f"   Query: \"{query}\"")
    print(f"   Expected: {expected.upper()}")

    # Generate response
    prompt = format_prompt(query)
    response = generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=300,
        verbose=False
    )

    # Check if tool was called
    used_tool = has_tool_call(response)
    actual = "tool" if used_tool else "direct"

    print(f"   Actual: {actual.upper()}")

    # First 150 chars of response
    response_preview = response.replace("\n", " ")[:150]
    print(f"   Response: {response_preview}...")

    # Check correctness
    if actual == expected:
        print("   ✅ CORRECT")
        results["correct"] += 1
    else:
        print("   ❌ INCORRECT")
        results["incorrect"] += 1

# Summary
total = results["correct"] + results["incorrect"]
accuracy = (results["correct"] / total * 100) if total > 0 else 0

print("\n" + "=" * 80)
print(f"SUMMARY")
print("=" * 80)
print(f"Correct: {results['correct']}/{total} ({accuracy:.1f}%)")
print(f"Incorrect: {results['incorrect']}/{total}")

if accuracy >= 80:
    print("\n✅ Phase 5 SUCCESS: Model learned to discriminate!")
    print("   • Concept questions → direct answers")
    print("   • Search/read queries → tool calls")
elif accuracy >= 60:
    print("\n⚠️  Phase 5 PARTIAL: Model shows some discrimination")
    print(f"   • {accuracy:.1f}% correct, needs more training or better examples")
else:
    print("\n❌ Phase 5 FAILED: Model needs improvement")
    print("   • Consider adjusting direct-answer ratio")
    print("   • Or adding more diverse examples")

print("=" * 80)
