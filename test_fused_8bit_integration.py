"""Test 8-bit fused model integration: verify it works without adapters."""

from mlx_lm import load, generate
import time

# Load the 8-bit fused model (no adapter needed!)
model_path = "./fused_model_8bit"

print("=" * 80)
print("8-bit Fused Model Integration Test")
print("=" * 80)

print(f"\nLoading model from: {model_path}")
start_time = time.time()
model, tokenizer = load(model_path)
load_time = time.time() - start_time
print(f"✓ Model loaded in {load_time:.2f}s\n")

# Test the same queries as Phase 5 to verify behavior is preserved
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
total_gen_time = 0.0

for i, test_case in enumerate(test_cases, 1):
    query = test_case["query"]
    expected = test_case["expected"]
    description = test_case["description"]

    print(f"\n{i}. {description}")
    print(f"   Query: \"{query}\"")
    print(f"   Expected: {expected.upper()}")

    # Generate response with timing
    prompt = format_prompt(query)
    gen_start = time.time()
    response = generate(
        model,
        tokenizer,
        prompt=prompt,
        max_tokens=300,
        verbose=False
    )
    gen_time = time.time() - gen_start
    total_gen_time += gen_time

    # Check if tool was called
    used_tool = has_tool_call(response)
    actual = "tool" if used_tool else "direct"

    print(f"   Actual: {actual.upper()}")
    print(f"   Generation time: {gen_time:.2f}s")

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
avg_gen_time = total_gen_time / total if total > 0 else 0

print("\n" + "=" * 80)
print(f"SUMMARY")
print("=" * 80)
print(f"Model path: {model_path}")
print(f"Load time: {load_time:.2f}s")
print(f"Average generation time: {avg_gen_time:.2f}s")
print(f"Correct: {results['correct']}/{total} ({accuracy:.1f}%)")
print(f"Incorrect: {results['incorrect']}/{total}")

if accuracy >= 80:
    print("\n✅ INTEGRATION SUCCESS: 8-bit fused model works correctly!")
    print("   • Preserves Phase 5 discrimination ability")
    print("   • No adapter overhead")
    print(f"   • {avg_gen_time:.2f}s average generation time")
elif accuracy >= 60:
    print("\n⚠️  INTEGRATION PARTIAL: Some behavior preserved")
    print(f"   • {accuracy:.1f}% correct")
else:
    print("\n❌ INTEGRATION FAILED: Behavior not preserved")
    print("   • May need to re-fuse or check quantization")

print("=" * 80)
