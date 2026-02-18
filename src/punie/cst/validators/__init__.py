"""Domain validators for tdom, svcs, and tdom-svcs patterns.

Exposes the validator dispatcher and all individual validators.
"""

from punie.cst.domain_models import DomainValidationResult
from punie.cst.validators.svcs import (
    check_dependency_graph,
    validate_injection_site,
    validate_service_registration,
)
from punie.cst.validators.tdom import (
    check_render_tree,
    validate_component,
    validate_escape_context,
)
from punie.cst.validators.tdom_svcs import (
    check_di_template_binding,
    validate_middleware_chain,
    validate_route_pattern,
)

__all__ = [
    "DomainValidationResult",
    "check_dependency_graph",
    "check_di_template_binding",
    "check_render_tree",
    "validate_component",
    "validate_escape_context",
    "validate_injection_site",
    "validate_middleware_chain",
    "validate_route_pattern",
    "validate_service_registration",
]
