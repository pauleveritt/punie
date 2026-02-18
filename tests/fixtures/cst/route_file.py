"""Route definitions fixture for testing validate_route_pattern."""


def Route(path, handler):
    """Stub Route function."""
    return (path, handler)


def handler():
    """Stub handler."""
    pass


# Valid routes
valid_route = Route("/users", handler)
valid_param = Route("/users/{id}", handler)

# Invalid route (missing leading slash)
bad_route = Route("users/list", handler)
