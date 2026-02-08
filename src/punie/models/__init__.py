"""Punie custom model implementations.

This package contains alternative model implementations for Pydantic AI,
including local models using MLX on Apple Silicon.
"""

__all__ = ["MLXModel", "parse_tool_calls"]

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from punie.models.mlx import MLXModel, parse_tool_calls
