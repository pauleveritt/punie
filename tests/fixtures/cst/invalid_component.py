"""Invalid tdom component fixture.

A component missing @dataclass and with a bad return type.
Used to test validate_component error detection.
"""


class BadGreeting:
    """Component missing @dataclass decorator."""

    name: str = "World"

    def __call__(self):
        return "Hello!"
