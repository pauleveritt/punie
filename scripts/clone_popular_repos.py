#!/usr/bin/env python3
"""Clone popular Python repositories for training data generation.

Instead of using gated datasets, we'll clone popular open-source projects
(MIT/Apache/BSD licensed) and generate tool-calling examples from real code.

This provides:
- Real-world Python patterns
- Diverse domains (web, data, testing, CLI)
- Ethically sourced (explicit open-source licenses)
- High-quality code (maintained projects)
"""

import subprocess
from pathlib import Path


# Popular Python projects with permissive licenses
REPOS = [
    # Web frameworks
    {"url": "https://github.com/tiangolo/fastapi.git", "name": "fastapi", "category": "web"},
    {"url": "https://github.com/pallets/flask.git", "name": "flask", "category": "web"},

    # Testing
    {"url": "https://github.com/pytest-dev/pytest.git", "name": "pytest", "category": "testing"},

    # CLI tools
    {"url": "https://github.com/tiangolo/typer.git", "name": "typer", "category": "cli"},
    {"url": "https://github.com/pallets/click.git", "name": "click", "category": "cli"},

    # Async
    {"url": "https://github.com/encode/httpx.git", "name": "httpx", "category": "async"},
    {"url": "https://github.com/encode/starlette.git", "name": "starlette", "category": "async"},

    # Data validation
    {"url": "https://github.com/pydantic/pydantic.git", "name": "pydantic", "category": "typing"},

    # Small, focused projects for diversity
    {"url": "https://github.com/hynek/attrs.git", "name": "attrs", "category": "typing"},
    {"url": "https://github.com/hynek/structlog.git", "name": "structlog", "category": "tools"},
]


def clone_repo(repo: dict, base_dir: Path) -> bool:
    """Clone a repository if it doesn't exist."""
    target_dir = base_dir / repo["name"]

    if target_dir.exists():
        print(f"  ✓ {repo['name']} already exists, skipping")
        return True

    print(f"  Cloning {repo['name']}...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo["url"], str(target_dir)],
            capture_output=True,
            check=True,
            timeout=300,  # 5 minute timeout
        )
        print(f"    ✓ Cloned successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"    ✗ Failed: {e.stderr.decode()}")
        return False
    except subprocess.TimeoutExpired:
        print(f"    ✗ Timed out")
        return False


def main():
    print("=" * 80)
    print("POPULAR PYTHON REPOS CLONER")
    print("=" * 80)
    print(f"\nCloning {len(REPOS)} popular Python projects...")
    print("(This will take a few minutes)")
    print()

    # Create repos directory
    repos_dir = Path("data/repos")
    repos_dir.mkdir(parents=True, exist_ok=True)

    print(f"Target directory: {repos_dir.absolute()}\n")

    # Clone repos
    success_count = 0
    for repo in REPOS:
        success = clone_repo(repo, repos_dir)
        if success:
            success_count += 1

    print(f"\n{'=' * 80}")
    print(f"✅ Cloned {success_count}/{len(REPOS)} repositories")
    print(f"\nRepositories in {repos_dir}/:")

    # Show what was cloned
    for repo in REPOS:
        repo_dir = repos_dir / repo["name"]
        if repo_dir.exists():
            # Count Python files
            py_files = list(repo_dir.rglob("*.py"))
            print(f"  • {repo['name']:20} ({repo['category']:8}) - {len(py_files)} Python files")

    print(f"\nNext step: Run scripts/generate_repo_examples.py")
    print("=" * 80)


if __name__ == "__main__":
    main()
