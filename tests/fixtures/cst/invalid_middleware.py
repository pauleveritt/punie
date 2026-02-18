"""Invalid middleware fixture.

A middleware with @middleware but wrong __call__ signature.
"""
from dataclasses import dataclass


def middleware(categories=None):
    """Stub @middleware decorator for fixture."""
    def decorator(cls):
        return cls
    return decorator


@middleware(categories=["security"])
@dataclass
class BadMiddleware:
    """Middleware with wrong __call__ signature."""

    priority: int = 0

    def __call__(self, target, props):
        # Missing context parameter!
        return props
