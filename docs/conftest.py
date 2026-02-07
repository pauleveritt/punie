"""Pytest configuration for docs/ markdown doctests.

This conftest handles docs/**/*.md only (README.md is in root conftest.py)
Uses PythonCodeBlockParser to parse ```python blocks containing doctest syntax.
"""

from sybil import Sybil
from sybil.parsers.myst import PythonCodeBlockParser

# Configure Sybil for docs/ markdown files
pytest_collect_file = Sybil(
    parsers=[PythonCodeBlockParser()],
    patterns=["*.md"],
    path=".",
    setup=lambda ns: ns.update(
        {
            # Add any imports needed for doctests here
        }
    ),
).pytest()
