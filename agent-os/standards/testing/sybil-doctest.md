# Sybil Doctest Integration

Use Sybil to test code examples in docs and docstrings.

## Configuration (conftest.py)

```python
from sybil import Sybil
from sybil.parsers.myst import PythonCodeBlockParser
from sybil.parsers.rest import DocTestParser

# Test Python docstrings in src/
_sybil_src = Sybil(
    parsers=[DocTestParser()],
    patterns=["*.py"],
    path="src",
)

# Test code blocks in README.md
_sybil_readme = Sybil(
    parsers=[PythonCodeBlockParser()],
    patterns=["README.md"],
    path=".",
)

def pytest_collect_file(file_path, parent):
    """Route files to appropriate Sybil parser."""
    ...
```

## What Gets Tested

- `src/**/*.py`: Docstring examples (`>>> ...`)
- `README.md`: Python code blocks
- `docs/**/*.md`: Via separate `docs/conftest.py`

## Rules

- Keep doctest examples minimal and focused
- Exclude research/draft docs from collection
- Use `PythonCodeBlockParser` for Markdown, `DocTestParser` for docstrings
