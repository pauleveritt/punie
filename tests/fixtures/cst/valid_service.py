"""Valid svcs service fixture.

A properly-formed service with @injectable and @dataclass.
"""
from dataclasses import dataclass

from svcs_di import Inject
from svcs_di.injectors import injectable


class Database:
    """Simple database."""
    pass


@injectable
@dataclass
class UserService:
    """Service that depends on Database."""

    db: Inject[Database]

    def get_users(self) -> list:
        return []
