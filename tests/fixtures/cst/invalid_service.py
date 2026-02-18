"""Invalid svcs service fixture.

A service missing @injectable decorator.
"""
from dataclasses import dataclass

from svcs_di import Inject


class Database:
    """Simple database."""
    pass


@dataclass
class BadUserService:
    """Service missing @injectable decorator."""

    db: Inject[Database]

    def get_users(self) -> list:
        return []
