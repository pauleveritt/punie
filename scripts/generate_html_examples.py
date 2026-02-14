#!/usr/bin/env python3
"""Generate HTML domain training examples for Phase 7.

Creates examples for:
- HTML structure understanding
- Element finding (by tag, class, id)
- Attribute extraction
- Component identification (headers, navs, forms)
- Semantic HTML understanding

Uses real HTML patterns from tdom-svcs and web frameworks.
"""

import json
import random
from pathlib import Path


# Sample HTML snippets for generating examples
HTML_SNIPPETS = [
    {
        "name": "simple_component",
        "html": '''<div class="card">
    <h2 class="card-title">User Profile</h2>
    <div class="card-body">
        <p>Username: alice</p>
        <p>Email: alice@example.com</p>
    </div>
</div>''',
        "description": "Simple card component",
    },
    {
        "name": "form_component",
        "html": '''<form id="login-form" action="/login" method="post">
    <label for="username">Username:</label>
    <input type="text" id="username" name="username" required>

    <label for="password">Password:</label>
    <input type="password" id="password" name="password" required>

    <button type="submit">Login</button>
</form>''',
        "description": "Login form with inputs",
    },
    {
        "name": "nav_component",
        "html": '''<nav class="main-nav">
    <ul>
        <li><a href="/" class="active">Home</a></li>
        <li><a href="/about">About</a></li>
        <li><a href="/contact">Contact</a></li>
    </ul>
</nav>''',
        "description": "Navigation menu",
    },
    {
        "name": "list_component",
        "html": '''<ul class="user-list">
    <li class="user-item" data-id="1">
        <span class="username">alice</span>
        <span class="role">admin</span>
    </li>
    <li class="user-item" data-id="2">
        <span class="username">bob</span>
        <span class="role">user</span>
    </li>
</ul>''',
        "description": "User list with data attributes",
    },
    {
        "name": "table_component",
        "html": '''<table class="data-table">
    <thead>
        <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Status</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Alice</td>
            <td>alice@example.com</td>
            <td>active</td>
        </tr>
    </tbody>
</table>''',
        "description": "Data table",
    },
]


def generate_grep_examples() -> list[dict]:
    """Generate grep/search examples for HTML patterns."""
    examples = []

    # Find by tag
    examples.extend([
        {
            "query": "Find all form elements in this HTML",
            "tool": "run_command",
            "args": {"command": "grep -r '<form' --include='*.html'"},
            "result": "template.html: <form id=\"login-form\" action=\"/login\"",
            "answer": "Found 1 form element in template.html.",
        },
        {
            "query": "Find all button elements",
            "tool": "run_command",
            "args": {"command": "grep -r '<button' --include='*.html'"},
            "result": "template.html: <button type=\"submit\">Login</button>",
            "answer": "Found button element in template.html.",
        },
        {
            "query": "Find all input fields",
            "tool": "run_command",
            "args": {"command": "grep -r '<input' --include='*.html'"},
            "result": "template.html: <input type=\"text\" id=\"username\"",
            "answer": "Found input fields in template.html.",
        },
    ])

    # Find by class
    examples.extend([
        {
            "query": "Find all elements with class 'card'",
            "tool": "run_command",
            "args": {"command": "grep -r 'class=\"card\"' --include='*.html'"},
            "result": "components.html: <div class=\"card\">",
            "answer": "Found elements with class 'card' in components.html.",
        },
        {
            "query": "Find all elements with class 'user-item'",
            "tool": "run_command",
            "args": {"command": "grep -r 'class=\"user-item\"' --include='*.html'"},
            "result": "users.html: <li class=\"user-item\" data-id=\"1\">",
            "answer": "Found user-item elements in users.html.",
        },
    ])

    # Find by id
    examples.extend([
        {
            "query": "Find element with id 'login-form'",
            "tool": "run_command",
            "args": {"command": "grep -r 'id=\"login-form\"' --include='*.html'"},
            "result": "login.html: <form id=\"login-form\" action=\"/login\"",
            "answer": "Found login-form element in login.html.",
        },
        {
            "query": "Find element with id 'username'",
            "tool": "run_command",
            "args": {"command": "grep -r 'id=\"username\"' --include='*.html'"},
            "result": "forms.html: <input type=\"text\" id=\"username\"",
            "answer": "Found username input in forms.html.",
        },
    ])

    # Semantic HTML
    examples.extend([
        {
            "query": "Find all navigation elements",
            "tool": "run_command",
            "args": {"command": "grep -r '<nav' --include='*.html'"},
            "result": "layout.html: <nav class=\"main-nav\">",
            "answer": "Found navigation element in layout.html.",
        },
        {
            "query": "Find all table structures",
            "tool": "run_command",
            "args": {"command": "grep -r '<table' --include='*.html'"},
            "result": "data.html: <table class=\"data-table\">",
            "answer": "Found table element in data.html.",
        },
    ])

    return examples


def generate_read_examples() -> list[dict]:
    """Generate read_file examples for HTML components."""
    examples = []

    for snippet in HTML_SNIPPETS:
        examples.append({
            "query": f"Show me the {snippet['description']}",
            "tool": "read_file",
            "args": {"path": f"templates/{snippet['name']}.html"},
            "result": snippet["html"],
            "answer": f"Here's the {snippet['description']} from templates/{snippet['name']}.html. "
                     f"It contains {snippet['html'].count('<')} HTML tags.",
        })

    return examples


def generate_direct_examples() -> list[dict]:
    """Generate direct-answer examples for HTML concepts."""
    examples = [
        # HTML Basics
        {
            "query": "What is semantic HTML?",
            "answer": "Semantic HTML uses elements that clearly describe their meaning and content, like <nav>, <article>, <section>, <header>, <footer>. This improves accessibility, SEO, and code maintainability compared to generic <div> elements.",
        },
        {
            "query": "What is the difference between div and span?",
            "answer": "Div is a block-level element that starts on a new line and takes full width. Span is an inline element that stays within the text flow. Use div for structure/layout and span for styling small portions of text.",
        },
        {
            "query": "What are data attributes in HTML?",
            "answer": "Data attributes (data-*) store custom data on HTML elements. They're accessed via JavaScript with dataset and don't affect page rendering. Common uses include storing IDs, configuration, or state for JavaScript to read.",
        },

        # Forms
        {
            "query": "What is the difference between id and name attributes?",
            "answer": "Id uniquely identifies an element for CSS/JavaScript and must be unique on the page. Name identifies form fields for server submission and can be shared by radio buttons in a group. Form data uses the name attribute, not id.",
        },
        {
            "query": "What is the purpose of the label element?",
            "answer": "Label associates text with form inputs, improving accessibility. Clicking the label focuses the input. It uses the 'for' attribute matching the input's id, or wraps the input directly.",
        },
        {
            "query": "What is the difference between GET and POST in forms?",
            "answer": "GET appends form data to the URL (visible, cacheable, limited size) - use for searches/filters. POST sends data in the request body (not visible, no size limit) - use for creating/updating data or sensitive information.",
        },

        # Tables
        {
            "query": "What is the purpose of thead and tbody?",
            "answer": "Thead groups table header rows, tbody groups body content rows. This improves accessibility, enables styling different sections, and allows browsers to keep headers visible when scrolling long tables.",
        },
        {
            "query": "When should I use a table vs div layout?",
            "answer": "Use tables for tabular data (data with rows and columns). Use div/CSS for page layout and non-tabular content. Tables should represent actual data relationships, not be used for visual layout.",
        },

        # Attributes
        {
            "query": "What is the difference between class and id?",
            "answer": "Id must be unique per page and identifies a single element. Class can be reused on multiple elements and represents a group. Use id for unique elements (forms, headers) and class for styling/behavior groups.",
        },
        {
            "query": "What are required and optional attributes?",
            "answer": "Required attributes must be present for valid HTML (e.g., img src, a href). Optional attributes add functionality or metadata (e.g., input placeholder, div class). Required form inputs use the 'required' boolean attribute.",
        },

        # Best Practices
        {
            "query": "What is accessibility in HTML?",
            "answer": "Accessibility means making HTML usable by everyone, including people with disabilities. Key practices: semantic HTML, alt text for images, proper heading hierarchy, label for form inputs, ARIA attributes when needed, keyboard navigation support.",
        },
        {
            "query": "What is the purpose of alt text in images?",
            "answer": "Alt text describes images for screen readers, shows when images fail to load, and helps SEO. It should be descriptive for meaningful images, empty for decorative images (alt=\"\"), and never omitted.",
        },
        {
            "query": "What is a heading hierarchy?",
            "answer": "Heading hierarchy uses h1-h6 in order without skipping levels. H1 is the main title (one per page), h2 for major sections, h3 for subsections, etc. This improves accessibility, SEO, and document structure.",
        },

        # Components
        {
            "query": "What is a nav element?",
            "answer": "Nav is a semantic element that marks navigation sections (main menu, breadcrumbs, pagination). It helps screen readers identify navigation, improves SEO, and makes page structure clear. Not all link groups need nav.",
        },
        {
            "query": "What is the difference between section and div?",
            "answer": "Section is semantic and represents a thematic grouping of content, typically with a heading. Div is generic and has no semantic meaning. Use section for meaningful content divisions, div for styling containers.",
        },
        {
            "query": "What is an article element?",
            "answer": "Article represents self-contained, independently distributable content (blog posts, news articles, comments). It should make sense on its own, even outside its context. Can be nested and can contain header/footer.",
        },
    ]

    return examples


def format_tool_example(ex: dict) -> str:
    """Format a tool-calling example in Qwen chat format."""
    tool_call = {"name": ex["tool"], "arguments": ex["args"]}

    return (
        f"<|im_start|>system\n"
        f"You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
        f"<|im_start|>user\n"
        f"{ex['query']}<|im_end|>\n"
        f"<|im_start|>assistant\n"
        f"I'll use the {ex['tool']} tool.\n\n"
        f"```json\n"
        f"{json.dumps(tool_call, indent=2)}\n"
        f"```<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Tool result: {ex['result']}<|im_end|>\n"
        f"<|im_start|>assistant\n"
        f"{ex['answer']}<|im_end|>"
    )


def format_direct_example(ex: dict) -> str:
    """Format a direct-answer example in Qwen chat format."""
    return (
        f"<|im_start|>system\n"
        f"You are Punie, an AI coding assistant that helps with Python development via PyCharm.<|im_end|>\n"
        f"<|im_start|>user\n"
        f"{ex['query']}<|im_end|>\n"
        f"<|im_start|>assistant\n"
        f"{ex['answer']}<|im_end|>"
    )


def main():
    print("=" * 80)
    print("HTML DOMAIN EXAMPLE GENERATOR - Phase 7")
    print("=" * 80)
    print("\nGenerating HTML-focused training examples")
    print("  Target: 50 grep + 10 read + 50 direct = 110 total")
    print()

    # Generate examples
    grep_examples = generate_grep_examples()
    read_examples = generate_read_examples()
    direct_examples = generate_direct_examples()

    print(f"Generated:")
    print(f"  Grep examples: {len(grep_examples)}")
    print(f"  Read examples: {len(read_examples)}")
    print(f"  Direct examples: {len(direct_examples)}")
    print(f"  Total: {len(grep_examples) + len(read_examples) + len(direct_examples)}")

    # Format all examples
    all_formatted = []

    for ex in grep_examples:
        all_formatted.append({
            "text": format_tool_example(ex),
            "source": "html_grep",
        })

    for ex in read_examples:
        all_formatted.append({
            "text": format_tool_example(ex),
            "source": "html_read",
        })

    for ex in direct_examples:
        all_formatted.append({
            "text": format_direct_example(ex),
            "source": "html_direct",
        })

    # Shuffle
    random.shuffle(all_formatted)

    # Save
    output_dir = Path("data/html_examples")
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "training_examples.jsonl"
    with output_file.open('w') as f:
        for ex in all_formatted:
            f.write(json.dumps(ex) + '\n')

    print(f"\n✅ Saved {len(all_formatted)} examples to {output_file}")
    print(f"   Tool-calling: {len(grep_examples) + len(read_examples)} ({(len(grep_examples) + len(read_examples))/len(all_formatted)*100:.1f}%)")
    print(f"   Direct answers: {len(direct_examples)} ({len(direct_examples)/len(all_formatted)*100:.1f}%)")
    print()
    print("Next step: Merge with Phase 6 data for Phase 7 training")
    print("=" * 80)


if __name__ == "__main__":
    random.seed(42)
    main()
