#!/usr/bin/env python3
"""Generate domain-pruned training data for Phase 8.

Focuses on Python+HTML+CSS+JS with Django/FastAPI/Flask/Sphinx.
Target: 500-1000 examples, 70/30 tool-calling vs direct-answer split.

Phase 8 strategy:
- Use existing Phase 7 data as base
- Add Django/Sphinx examples
- Add HTML/CSS/JS template examples
- Maintain 70/30 tool vs direct-answer balance
- Prune to 600-800 total examples (smaller, domain-focused)
"""

import json
import random
from pathlib import Path
from subprocess import run


def clone_repo_if_needed(name: str, url: str, repos_dir: Path) -> Path:
    """Clone a repository if it doesn't exist."""
    repo_dir = repos_dir / name
    if repo_dir.exists():
        print(f"✓ {name} already cloned")
        return repo_dir

    print(f"Cloning {name}...")
    run(["git", "clone", "--depth", "1", url, str(repo_dir)], check=True)
    print(f"✓ Cloned {name}")
    return repo_dir


def load_phase7_data() -> list[dict]:
    """Load existing Phase 7 training data."""
    phase7_dir = Path("data/phase7_format")
    examples = []

    for file in ["train.jsonl", "valid.jsonl"]:
        filepath = phase7_dir / file
        if filepath.exists():
            with filepath.open() as f:
                for line in f:
                    examples.append(json.loads(line))

    return examples


def categorize_example(ex: dict) -> str:
    """Categorize example as tool or direct."""
    text = ex.get("text", "")
    # Tool examples have the JSON tool call format
    if "```json" in text and '"name":' in text:
        return "tool"
    return "direct"


def is_domain_relevant(ex: dict, target_frameworks: set[str]) -> bool:
    """Check if example is relevant to target domain."""
    text = ex.get("text", "").lower()
    source = ex.get("source", "")

    # Keep all direct answers (concepts are universal)
    if categorize_example(ex) == "direct":
        return True

    # For tool examples, check if they reference target frameworks
    for framework in target_frameworks:
        if framework.lower() in text:
            return True

    # Keep examples from target repos
    if any(fw in source for fw in ["fastapi", "flask", "django", "sphinx"]):
        return True

    # Keep general Python patterns
    if any(pattern in text for pattern in [
        "class ", "def ", "import ", "async ", "decorator",
        "__init__", "pytest", "type hint"
    ]):
        return True

    return False


def generate_django_examples() -> list[dict]:
    """Generate Django-specific examples."""
    examples = []

    # Tool-calling examples
    examples.append({
        "text": (
            "<|im_start|>system\n"
            "You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
            "<|im_start|>user\n"
            "Find all Django views<|im_end|>\n"
            "<|im_start|>assistant\n"
            "I'll use the run_command tool.\n\n"
            "```json\n"
            '{\n  "name": "run_command",\n  "arguments": {\n    "command": "grep -r \'def.*request\' --include=\'views.py\'"\n  }\n'
            "}```<|im_end|>\n"
            "<|im_start|>user\n"
            "Tool result: Found 15 view functions<|im_end|>\n"
            "<|im_start|>assistant\n"
            "Found 15 Django view functions in views.py files.<|im_end|>"
        ),
        "source": "phase8_django_tool",
    })

    examples.append({
        "text": (
            "<|im_start|>system\n"
            "You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
            "<|im_start|>user\n"
            "Show me the Django model definitions<|im_end|>\n"
            "<|im_start|>assistant\n"
            "I'll use the read_file tool.\n\n"
            "```json\n"
            '{\n  "name": "read_file",\n  "arguments": {\n    "path": "models.py"\n  }\n'
            "}```<|im_end|>\n"
            "<|im_start|>user\n"
            "Tool result: class User(models.Model): ...<|im_end|>\n"
            "<|im_start|>assistant\n"
            "Here are the Django model definitions from models.py.<|im_end|>"
        ),
        "source": "phase8_django_tool",
    })

    # Direct answer examples
    examples.append({
        "text": (
            "<|im_start|>system\n"
            "You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
            "<|im_start|>user\n"
            "What is the difference between Django ORM and raw SQL?<|im_end|>\n"
            "<|im_start|>assistant\n"
            "Django ORM provides a Pythonic API to interact with databases using objects and methods, "
            "automatically handling SQL generation, type conversion, and database portability. "
            "Raw SQL gives you direct control over queries and can be more efficient for complex operations, "
            "but requires manual escaping and is database-specific. Use ORM for most cases, raw SQL for optimization.<|im_end|>"
        ),
        "source": "phase8_django_direct",
    })

    examples.append({
        "text": (
            "<|im_start|>system\n"
            "You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
            "<|im_start|>user\n"
            "When should I use Django templates vs React?<|im_end|>\n"
            "<|im_start|>assistant\n"
            "Use Django templates for server-rendered pages with simple interactivity - they're simpler, "
            "integrate well with Django, and work without JavaScript. Use React for complex, highly interactive UIs "
            "that need real-time updates, rich state management, or SPA architecture. "
            "Many projects use both: Django templates for marketing pages, React for app UI.<|im_end|>"
        ),
        "source": "phase8_django_direct",
    })

    return examples


def generate_sphinx_examples() -> list[dict]:
    """Generate Sphinx-specific examples."""
    examples = []

    # Tool-calling examples
    examples.append({
        "text": (
            "<|im_start|>system\n"
            "You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
            "<|im_start|>user\n"
            "Find all Sphinx directives in documentation<|im_end|>\n"
            "<|im_start|>assistant\n"
            "I'll use the run_command tool.\n\n"
            "```json\n"
            '{\n  "name": "run_command",\n  "arguments": {\n    "command": "grep -r \'.. \\w\\+::\' --include=\'*.rst\' --include=\'*.md\'"\n  }\n'
            "}```<|im_end|>\n"
            "<|im_start|>user\n"
            "Tool result: Found 42 directive usages<|im_end|>\n"
            "<|im_start|>assistant\n"
            "Found 42 Sphinx directives across RST and Markdown files.<|im_end|>"
        ),
        "source": "phase8_sphinx_tool",
    })

    # Direct answer examples
    examples.append({
        "text": (
            "<|im_start|>system\n"
            "You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
            "<|im_start|>user\n"
            "What is the difference between RST and MyST Markdown?<|im_end|>\n"
            "<|im_start|>assistant\n"
            "RST (reStructuredText) is Sphinx's native markup format with extensive directive support but complex syntax. "
            "MyST Markdown extends CommonMark with Sphinx directives using familiar Markdown syntax. "
            "MyST is easier to read/write and works with standard Markdown tools, "
            "while RST has more mature tooling and edge-case handling. Modern projects prefer MyST for better DX.<|im_end|>"
        ),
        "source": "phase8_sphinx_direct",
    })

    return examples


def generate_html_css_js_examples() -> list[dict]:
    """Generate HTML/CSS/JS template examples."""
    examples = []

    # Django template
    examples.append({
        "text": (
            "<|im_start|>system\n"
            "You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
            "<|im_start|>user\n"
            "Find all Django template tags<|im_end|>\n"
            "<|im_start|>assistant\n"
            "I'll use the run_command tool.\n\n"
            "```json\n"
            '{\n  "name": "run_command",\n  "arguments": {\n    "command": "grep -r \'{%.*%}\' --include=\'*.html\'"\n  }\n'
            "}```<|im_end|>\n"
            "<|im_start|>user\n"
            "Tool result: Found 87 template tag usages<|im_end|>\n"
            "<|im_start|>assistant\n"
            "Found 87 Django template tags in HTML files.<|im_end|>"
        ),
        "source": "phase8_html_tool",
    })

    # Jinja2 template
    examples.append({
        "text": (
            "<|im_start|>system\n"
            "You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
            "<|im_start|>user\n"
            "What is the difference between Django templates and Jinja2?<|im_end|>\n"
            "<|im_start|>assistant\n"
            "Django templates use {% %} syntax with conservative design philosophy - simple, safe, limited Python access. "
            "Jinja2 is more flexible, faster, and allows more Python expressions in templates. "
            "Django templates integrate seamlessly with Django, while Jinja2 is framework-agnostic. "
            "Flask uses Jinja2 by default. Choose Django templates for Django projects, Jinja2 for other frameworks.<|im_end|>"
        ),
        "source": "phase8_html_direct",
    })

    # CSS
    examples.append({
        "text": (
            "<|im_start|>system\n"
            "You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
            "<|im_start|>user\n"
            "Find all CSS files with flexbox<|im_end|>\n"
            "<|im_start|>assistant\n"
            "I'll use the run_command tool.\n\n"
            "```json\n"
            '{\n  "name": "run_command",\n  "arguments": {\n    "command": "grep -r \'display: *flex\' --include=\'*.css\'"\n  }\n'
            "}```<|im_end|>\n"
            "<|im_start|>user\n"
            "Tool result: Found 23 flexbox usages<|im_end|>\n"
            "<|im_start|>assistant\n"
            "Found 23 files using CSS flexbox layout.<|im_end|>"
        ),
        "source": "phase8_css_tool",
    })

    # JavaScript
    examples.append({
        "text": (
            "<|im_start|>system\n"
            "You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
            "<|im_start|>user\n"
            "Find all fetch API usage<|im_end|>\n"
            "<|im_start|>assistant\n"
            "I'll use the run_command tool.\n\n"
            "```json\n"
            '{\n  "name": "run_command",\n  "arguments": {\n    "command": "grep -r \'fetch(\' --include=\'*.js\'"\n  }\n'
            "}```<|im_end|>\n"
            "<|im_start|>user\n"
            "Tool result: Found 18 fetch calls<|im_end|>\n"
            "<|im_start|>assistant\n"
            "Found 18 fetch API calls in JavaScript files.<|im_end|>"
        ),
        "source": "phase8_js_tool",
    })

    return examples


def main():
    print("=" * 80)
    print("PHASE 8 DOMAIN-PRUNED TRAINING DATA GENERATOR")
    print("=" * 80)
    print("\nTarget: Python+HTML+CSS+JS with Django/FastAPI/Flask/Sphinx")
    print("Goal: 600-800 examples, 70/30 tool vs direct-answer split")
    print()

    # Setup
    repos_dir = Path("data/repos")
    repos_dir.mkdir(parents=True, exist_ok=True)

    target_frameworks = {"django", "fastapi", "flask", "sphinx", "jinja2", "pytest"}

    # Clone missing repos
    print("Step 1: Checking repositories...")
    clone_repo_if_needed("django", "https://github.com/django/django.git", repos_dir)
    clone_repo_if_needed("sphinx", "https://github.com/sphinx-doc/sphinx.git", repos_dir)
    print()

    # Load Phase 7 data
    print("Step 2: Loading Phase 7 data...")
    phase7_examples = load_phase7_data()
    print(f"✓ Loaded {len(phase7_examples)} Phase 7 examples")

    # Analyze Phase 7 distribution
    phase7_tool = sum(1 for ex in phase7_examples if categorize_example(ex) == "tool")
    phase7_direct = len(phase7_examples) - phase7_tool
    print(f"  Tool: {phase7_tool} ({phase7_tool/len(phase7_examples)*100:.1f}%)")
    print(f"  Direct: {phase7_direct} ({phase7_direct/len(phase7_examples)*100:.1f}%)")
    print()

    # Filter Phase 7 to domain-relevant examples
    print("Step 3: Filtering Phase 7 to domain-relevant examples...")
    relevant_examples = [
        ex for ex in phase7_examples
        if is_domain_relevant(ex, target_frameworks)
    ]
    print(f"✓ Kept {len(relevant_examples)} domain-relevant examples from Phase 7")
    print()

    # Generate new domain examples
    print("Step 4: Generating new domain-specific examples...")
    django_examples = generate_django_examples()
    sphinx_examples = generate_sphinx_examples()
    html_examples = generate_html_css_js_examples()

    print(f"✓ Generated {len(django_examples)} Django examples")
    print(f"✓ Generated {len(sphinx_examples)} Sphinx examples")
    print(f"✓ Generated {len(html_examples)} HTML/CSS/JS examples")
    print()

    # Combine all examples
    all_examples = (
        relevant_examples +
        django_examples +
        sphinx_examples +
        html_examples
    )
    random.shuffle(all_examples)

    # Analyze distribution
    tool_count = sum(1 for ex in all_examples if categorize_example(ex) == "tool")
    direct_count = len(all_examples) - tool_count

    print(f"Step 5: Combined dataset statistics")
    print(f"  Total: {len(all_examples)} examples")
    print(f"  Tool: {tool_count} ({tool_count/len(all_examples)*100:.1f}%)")
    print(f"  Direct: {direct_count} ({direct_count/len(all_examples)*100:.1f}%)")
    print()

    # Balance if needed (target 70/30)
    target_tool_pct = 0.70
    target_direct_pct = 0.30

    current_tool_pct = tool_count / len(all_examples)
    current_direct_pct = direct_count / len(all_examples)

    print(f"  Current split: {current_tool_pct*100:.1f}% tool, {current_direct_pct*100:.1f}% direct")
    print(f"  Target split: {target_tool_pct*100:.1f}% tool, {target_direct_pct*100:.1f}% direct")

    # Split into train/valid/test (80/10/10)
    random.shuffle(all_examples)
    train_split = int(len(all_examples) * 0.8)
    valid_split = int(len(all_examples) * 0.9)

    train_examples = all_examples[:train_split]
    valid_examples = all_examples[train_split:valid_split]
    test_examples = all_examples[valid_split:]

    print()
    print(f"Step 6: Saving Phase 8 data")
    print(f"  Train: {len(train_examples)} examples")
    print(f"  Valid: {len(valid_examples)} examples")
    print(f"  Test: {len(test_examples)} examples")

    # Save
    output_dir = Path("data/phase8_format")
    output_dir.mkdir(parents=True, exist_ok=True)

    with (output_dir / "train.jsonl").open('w') as f:
        for ex in train_examples:
            f.write(json.dumps(ex) + '\n')

    with (output_dir / "valid.jsonl").open('w') as f:
        for ex in valid_examples:
            f.write(json.dumps(ex) + '\n')

    with (output_dir / "test.jsonl").open('w') as f:
        for ex in test_examples:
            f.write(json.dumps(ex) + '\n')

    print(f"✅ Saved to {output_dir}/")
    print()
    print("Next step: Run scripts/test_qwen3_trainability.sh then full training")
    print("=" * 80)


if __name__ == "__main__":
    random.seed(42)
    main()
