# Phase 32 References

## Key Source Files

### Existing patterns to follow
- `src/punie/agent/typed_tools.py` — Result model + parser function pattern
- `src/punie/agent/toolset.py` — Direct tool + sync bridge pattern
- `src/punie/agent/monty_runner.py` — ExternalFunctions + namespace pattern
- `src/punie/agent/stubs.py` — Manual stub generation pattern
- `src/punie/agent/config.py` — PUNIE_DIRECT_INSTRUCTIONS update pattern

### Domain patterns
- `/Users/pauleveritt/projects/t-strings/tdom-svcs/examples/basic/inject_service.py` — Component + service pattern
- `/Users/pauleveritt/projects/t-strings/tdom-svcs/examples/common/services.py` — @injectable @dataclass service pattern
- `/Users/pauleveritt/projects/t-strings/tdom-svcs/examples/middleware/aria/middleware.py` — Per-target middleware pattern
- `/Users/pauleveritt/projects/t-strings/tdom-svcs/examples/categories/categories_example.py` — @middleware global + categories

## New Files Created
- `src/punie/cst/__init__.py`
- `src/punie/cst/core.py`
- `src/punie/cst/code_tools.py`
- `src/punie/cst/domain_models.py`
- `src/punie/cst/validators/__init__.py`
- `src/punie/cst/validators/tdom.py`
- `src/punie/cst/validators/svcs.py`
- `src/punie/cst/validators/tdom_svcs.py`
