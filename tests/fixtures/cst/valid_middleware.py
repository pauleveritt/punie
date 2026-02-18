"""Valid tdom-svcs middleware fixture.

A properly-formed global middleware with @middleware, categories,
and correct __call__ signature.
"""
from dataclasses import dataclass


def middleware(categories=None):
    """Stub @middleware decorator for fixture."""
    def decorator(cls):
        return cls
    return decorator


@middleware(categories=["security", "auth"])
@dataclass
class AuthMiddleware:
    """Authentication middleware."""

    priority: int = -20

    def __call__(self, target, props, context):
        props["authenticated"] = True
        return props
