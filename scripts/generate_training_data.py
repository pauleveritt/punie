#!/usr/bin/env python3
"""Generate training data for knowledge distillation (30B → 7B).

Uses 30B model to create (query, tool_calls, answer) training examples.
Goal: Teach 7B to autonomously use tools like 30B does.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path

from punie.agent.factory import create_pydantic_agent
from punie.agent.config import AgentConfig
from punie.agent.deps import ACPDeps
from punie.acp.contrib.tool_calls import ToolCallTracker
from punie.local import LocalClient


@dataclass
class TrainingExample:
    """Single training example for knowledge distillation."""

    query: str
    reasoning: str  # Why tools are needed
    tool_calls: list[dict]  # Tool name + args
    answer: str
    metadata: dict  # Category, difficulty, etc.


# Query templates for diverse training data
QUERY_TEMPLATES = {
    "code_search": [
        "Which classes in this codebase subclass from {base_class}?",
        "Find all classes that inherit from {base_class}",
        "What classes extend {base_class}?",
        "List all {base_class} subclasses in the codebase",
        "Show me classes that implement {interface}",
    ],
    "import_analysis": [
        "Find all files that import '{module}'",
        "Which files use the {module} module?",
        "List files importing {module}",
        "Show all imports of {module}",
        "What files depend on {module}?",
    ],
    "function_discovery": [
        "What are the parameters for the {function} function?",
        "Show me the signature of {function}",
        "What arguments does {function} take?",
        "Describe the {function} function parameters",
        "What's the function signature for {function}?",
    ],
    "counting": [
        "How many test files are in {directory}?",
        "Count the number of {pattern} files in {directory}",
        "How many files match {pattern} in {directory}?",
        "What's the total count of {pattern} in {directory}?",
    ],
    "pattern_search": [
        "List all dataclasses defined in {directory}",
        "Find all functions decorated with @{decorator} in {directory}",
        "Show me all {pattern} in {directory}",
        "What {pattern} exist in {directory}?",
    ],
    "web_frontend": [
        "Find all {html_element} elements in {web_directory}",
        "List all CSS classes used in {web_directory}",
        "What JavaScript functions are defined in {js_file}?",
        "Find all React components in {web_directory}",
        "Show me all CSS files that use {css_property}",
    ],
    "web_backend": [
        "What routes are defined in {web_file}?",
        "List all HTTP endpoints in {directory}",
        "Find all template files in {directory}",
        "What API endpoints exist in the codebase?",
    ],
    "negative_examples": [
        "What is {num1} × {num2}?",
        "What are Python type hints?",
        "Explain what a Protocol is",
        "What's the difference between async and sync?",
        "How does inheritance work in Python?",
    ],
}

# Real values from Punie codebase
SUBSTITUTIONS = {
    "base_class": ["Protocol", "Exception", "BaseModel", "ABC"],
    "interface": ["Protocol", "Client", "Agent"],
    "module": ["asyncio", "pydantic", "pytest", "pathlib", "dataclasses"],
    "function": ["create_pydantic_agent", "run_command", "read_file", "create_toolset"],
    "directory": ["src/punie/", "tests/", "src/punie/acp/", "src/punie/training/"],
    "pattern": ["test_*.py", "@dataclass", "async def", "class.*Protocol"],
    "decorator": ["dataclass", "pytest.fixture", "contextmanager"],
    "num1": ["25", "17", "42"],
    "num2": ["4", "3", "7"],
    # Web-related substitutions
    "html_element": ["div", "button", "form", "input", "a"],
    "web_directory": ["templates/", "static/", "frontend/", "public/"],
    "js_file": ["app.js", "main.js", "index.js"],
    "css_property": ["flex", "grid", "color", "margin"],
    "web_file": ["app.py", "routes.py", "views.py", "server.py"],
}


def generate_queries(target_count: int = 1000) -> list[tuple[str, str, dict]]:
    """Generate query variations from templates.

    Returns:
        List of (query, category, metadata) tuples
    """
    queries = []

    for category, templates in QUERY_TEMPLATES.items():
        for template in templates:
            # Find placeholders in template
            placeholders = []
            for key in SUBSTITUTIONS:
                if f"{{{key}}}" in template:
                    placeholders.append(key)

            if not placeholders:
                # No substitution needed
                queries.append((
                    template,
                    category,
                    {"difficulty": "easy", "requires_tools": category != "negative_examples"}
                ))
            else:
                # Generate variants with substitutions
                for value in SUBSTITUTIONS[placeholders[0]]:
                    query = template.replace(f"{{{placeholders[0]}}}", value)

                    # Handle additional placeholders if present
                    for ph in placeholders[1:]:
                        if SUBSTITUTIONS[ph]:
                            query = query.replace(f"{{{ph}}}", SUBSTITUTIONS[ph][0])

                    queries.append((
                        query,
                        category,
                        {
                            "difficulty": "medium",
                            "requires_tools": category != "negative_examples",
                            "template": template,
                        }
                    ))

            if len(queries) >= target_count:
                break

        if len(queries) >= target_count:
            break

    return queries[:target_count]


async def generate_training_example(
    query: str,
    category: str,
    metadata: dict,
    agent,
    client: LocalClient,
    session_id: str,
) -> TrainingExample | None:
    """Run 30B on query and create training example.

    Args:
        query: User query
        category: Query category (code_search, import_analysis, etc.)
        metadata: Additional metadata
        agent: 30B agent instance
        client: LocalClient for workspace access
        session_id: Unique session ID

    Returns:
        TrainingExample or None if generation failed
    """
    tracker = ToolCallTracker()
    deps = ACPDeps(
        client_conn=client,
        session_id=session_id,
        tracker=tracker,
    )

    try:
        start = time.perf_counter()
        # Add 90 second timeout to prevent hanging on stuck queries
        result = await asyncio.wait_for(
            agent.run(query, deps=deps),
            timeout=90.0
        )
        elapsed = time.perf_counter() - start

        # Extract tool calls
        tool_calls = []
        if result.all_messages():
            for msg in result.all_messages():
                if hasattr(msg, "parts"):
                    for part in msg.parts:
                        if hasattr(part, "tool_name"):
                            tool_calls.append({
                                "tool": part.tool_name,
                                "args": getattr(part, "args", {}),
                            })

        # Determine reasoning
        if category == "negative_examples":
            reasoning = "No tools needed - general knowledge or math question"
        elif tool_calls:
            reasoning = f"Need to search/analyze codebase using {len(tool_calls)} tool(s)"
        else:
            reasoning = "Answer requires codebase knowledge but model didn't use tools"

        # Create example
        example = TrainingExample(
            query=query,
            reasoning=reasoning,
            tool_calls=tool_calls,
            answer=result.output,
            metadata={
                **metadata,
                "category": category,
                "execution_time": elapsed,
                "tool_count": len(tool_calls),
                "model": "qwen3-30b-a3b-instruct-2507-mlx",
            }
        )

        return example

    except asyncio.TimeoutError:
        print(f"⏱️  Timeout (90s) generating example for '{query}'")
        return None
    except Exception as e:
        print(f"❌ Failed to generate example for '{query}': {e}")
        return None


async def generate_dataset(
    output_file: Path,
    target_count: int = 1000,
    batch_size: int = 10,
) -> None:
    """Generate full training dataset.

    Args:
        output_file: Path to save training data (JSONL format)
        target_count: Number of examples to generate
        batch_size: Number of concurrent queries
    """
    print("=" * 80)
    print("TRAINING DATA GENERATION")
    print("=" * 80)
    print(f"\nTarget: {target_count} examples")
    print(f"Batch size: {batch_size} concurrent queries")
    print(f"Output: {output_file}\n")

    # Setup
    workspace = Path.cwd()
    model_name = "local:http://127.0.0.1:8080/v1/qwen3-30b-a3b-instruct-2507-mlx"
    agent_config = AgentConfig(temperature=0.0)
    agent = create_pydantic_agent(model=model_name, config=agent_config)
    client = LocalClient(workspace=workspace)

    # Generate queries
    print("Generating query variations...")
    queries = generate_queries(target_count)
    print(f"✅ Generated {len(queries)} queries\n")

    # Process in batches
    examples = []
    failed = 0

    for i in range(0, len(queries), batch_size):
        batch = queries[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(queries) + batch_size - 1) // batch_size

        print(f"Batch {batch_num}/{total_batches} ({len(batch)} queries)...")

        # Run batch concurrently
        tasks = [
            generate_training_example(
                query=query,
                category=category,
                metadata=meta,
                agent=agent,
                client=client,
                session_id=f"gen-{i + j}",
            )
            for j, (query, category, meta) in enumerate(batch)
        ]

        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in batch_results:
            if isinstance(result, Exception):
                failed += 1
            elif result is not None:
                examples.append(result)

        print(f"  ✅ {len([r for r in batch_results if not isinstance(r, Exception)])} succeeded")
        print(f"  Progress: {len(examples)}/{target_count} examples\n")

        # Save checkpoint every batch
        save_examples(examples, output_file)

    # Final stats
    print("=" * 80)
    print("GENERATION COMPLETE")
    print("=" * 80)
    print(f"\nTotal examples: {len(examples)}")
    print(f"Failed: {failed}")
    print(f"Success rate: {len(examples)/(len(examples)+failed)*100:.1f}%")

    # Category breakdown
    categories = {}
    for ex in examples:
        cat = ex.metadata.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    print("\nCategory breakdown:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count}")

    # Tool usage stats
    with_tools = len([ex for ex in examples if ex.tool_calls])
    without_tools = len(examples) - with_tools

    print(f"\nTool usage:")
    print(f"  With tools: {with_tools} ({with_tools/len(examples)*100:.1f}%)")
    print(f"  Without tools: {without_tools} ({without_tools/len(examples)*100:.1f}%)")

    print(f"\n💾 Saved to: {output_file}")


def save_examples(examples: list[TrainingExample], output_file: Path) -> None:
    """Save examples to JSONL file.

    Args:
        examples: List of training examples
        output_file: Output path
    """
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w") as f:
        for ex in examples:
            # Convert to dict for JSON serialization
            data = {
                "query": ex.query,
                "reasoning": ex.reasoning,
                "tool_calls": ex.tool_calls,
                "answer": ex.answer,
                "metadata": ex.metadata,
            }
            f.write(json.dumps(data) + "\n")


async def main():
    """Generate training dataset for MVP (1K examples)."""
    output_file = Path("data/training_examples_1k.jsonl")

    await generate_dataset(
        output_file=output_file,
        target_count=100,  # Start with 100 for quick MVP
        batch_size=2,  # 2 concurrent queries (reduced to avoid hangs)
    )


if __name__ == "__main__":
    asyncio.run(main())
