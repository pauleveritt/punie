"""Shared LibCST parsing utilities.

Provides parse_file and parse_source as the entry points for all
CST-based analysis in the punie.cst package.
"""

import libcst as cst


def parse_file(path: str) -> cst.Module:
    """Parse a Python source file into a LibCST Module.

    Args:
        path: Absolute or relative path to a Python file

    Returns:
        LibCST Module (lossless CST with whitespace preservation)

    Raises:
        FileNotFoundError: If the file does not exist
        libcst.ParserSyntaxError: If the file cannot be parsed
    """
    with open(path) as f:
        source = f.read()
    return cst.parse_module(source)


def parse_source(code: str) -> cst.Module:
    """Parse Python source code string into a LibCST Module.

    Args:
        code: Python source code as a string

    Returns:
        LibCST Module (lossless CST with whitespace preservation)

    Raises:
        libcst.ParserSyntaxError: If the code cannot be parsed

    Example:
        >>> module = parse_source("x = 1\\n")
        >>> module.code
        'x = 1\\n'
    """
    return cst.parse_module(code)
