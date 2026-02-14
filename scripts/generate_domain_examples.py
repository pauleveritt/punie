"""Generate domain-specific training examples from t-strings repos.

Reads real example and test files from tdom-svcs, svcs-di, storyville, and aria-testing
to create training data that teaches the model actual Python/DI/tdom patterns.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Base directory for t-strings repos
T_STRINGS_BASE = Path("/Users/pauleveritt/projects/t-strings")

# System message for all examples
SYSTEM_MSG = "You are Punie, an AI coding assistant that helps with Python development via PyCharm."


@dataclass
class Example:
    """A single training example."""

    user_query: str
    tool_name: str | None  # None for direct answers
    tool_args: dict[str, Any] | None
    tool_result: str | None
    final_response: str


def create_messages(example: Example) -> dict[str, list[dict[str, str]]]:
    """Convert an Example to the messages format."""
    messages = [
        {"role": "system", "content": SYSTEM_MSG},
        {"role": "user", "content": example.user_query},
    ]

    if example.tool_name:
        # Assistant calls tool
        tool_call = {
            "role": "assistant",
            "content": f"I'll use the {example.tool_name} tool.\n\n```json\n{json.dumps({'name': example.tool_name, 'arguments': example.tool_args}, indent=2)}\n```",
        }
        messages.append(tool_call)

        # Tool result
        messages.append({"role": "user", "content": f"Tool result: {example.tool_result}"})

    # Final response
    messages.append({"role": "assistant", "content": example.final_response})

    return {"messages": messages}


def read_file_safe(path: Path) -> str | None:
    """Read file, return None if it doesn't exist or is too large."""
    try:
        if not path.exists() or path.stat().st_size > 50_000:
            return None
        return path.read_text()
    except Exception:
        return None


def generate_read_file_examples() -> list[Example]:
    """Generate read_file examples from real source files."""
    examples = []

    # svcs-di examples
    files_to_read = [
        ("svcs-di/examples/basic_injection.py", "Show me the basic injection example", "basic injection pattern"),
        ("svcs-di/examples/basic_function.py", "What's in the basic function example?", "function-based DI example"),
        ("svcs-di/examples/modern_dataclass.py", "Show me the modern dataclass example", "advanced dataclass features"),
        ("svcs-di/examples/protocol_injection.py", "Show me protocol injection", "protocol-based DI"),
    ]

    # tdom-svcs examples
    files_to_read.extend(
        [
            ("tdom-svcs/examples/basic/pure_tdom.py", "Show me pure tdom example", "basic tdom component"),
            ("tdom-svcs/examples/basic/inject_service.py", "Show me service injection in tdom", "tdom with DI"),
            (
                "tdom-svcs/examples/hopscotch/simple_inject.py",
                "Show me Hopscotch injection",
                "Hopscotch DI pattern",
            ),
        ]
    )

    for file_path, query, description in files_to_read:
        full_path = T_STRINGS_BASE / file_path
        content = read_file_safe(full_path)
        if content:
            examples.append(
                Example(
                    user_query=query,
                    tool_name="read_file",
                    tool_args={"path": file_path},
                    tool_result=content,
                    final_response=f"This file shows {description}. It demonstrates the key patterns for this approach.",
                )
            )

    return examples


def generate_test_file_examples() -> list[Example]:
    """Generate examples from test files."""
    examples = []

    test_files = [
        (
            "svcs-di/tests/test_injectable.py",
            "Show me the injectable tests",
            "type introspection and Inject marker testing",
        ),
        ("svcs-di/tests/test_auto.py", "What tests cover the auto() function?", "auto() factory testing"),
        (
            "tdom-svcs/tests/test_di_injection.py",
            "Show me DI injection tests",
            "dependency injection with tdom components",
        ),
        (
            "aria-testing/tests/test_queries.py",
            "Show me ARIA query tests",
            "comprehensive accessibility query testing",
        ),
    ]

    for file_path, query, description in test_files:
        full_path = T_STRINGS_BASE / file_path
        content = read_file_safe(full_path)
        if content:
            # Truncate long test files
            if len(content) > 3000:
                lines = content.split("\n")
                content = "\n".join(lines[:80]) + "\n... (truncated)"

            examples.append(
                Example(
                    user_query=query,
                    tool_name="read_file",
                    tool_args={"path": file_path},
                    tool_result=content,
                    final_response=f"This test file covers {description}. The tests use pytest with fixtures and parametrize.",
                )
            )

    return examples


def generate_run_command_examples() -> list[Example]:
    """Generate run_command examples (search, test execution, etc.)."""
    examples = [
        Example(
            user_query="Find all files using Inject in svcs-di",
            tool_name="run_command",
            tool_args={"command": "grep -r 'Inject\\[' svcs-di/"},
            tool_result="svcs-di/examples/basic_injection.py:    db: Inject[Database]\nsvcs-di/src/svcs_di/auto.py:Inject: TypeAlias = Annotated[T, InjectionMarker()]\nsvcs-di/tests/test_injectable.py:    assert extract_inner_type(Inject[Database]) is Database",
            final_response="Found 3 files using Inject: the basic injection example, the auto module where it's defined, and the tests.",
        ),
        Example(
            user_query="Run the svcs-di tests",
            tool_name="run_command",
            tool_args={"command": "cd svcs-di && pytest tests/ -v"},
            tool_result="===== test session starts =====\nplatform darwin -- Python 3.14.2, pytest-9.0.2\ncollected 47 items\n\ntests/test_auto.py::test_auto_creates_factory PASSED\ntests/test_injectable.py::test_injectable_wraps_type PASSED\n... (45 more tests)\n\n===== 47 passed in 1.23s =====",
            final_response="All 47 tests passed successfully in 1.23 seconds!",
        ),
        Example(
            user_query="Find tdom component definitions",
            tool_name="run_command",
            tool_args={"command": "grep -r '@component' tdom-svcs/examples/"},
            tool_result="tdom-svcs/examples/basic/pure_tdom.py:@component\ntdom-svcs/examples/middleware/request_context.py:@component\ntdom-svcs/examples/hopscotch/category_components.py:@component",
            final_response="Found component decorators in 3 files: pure_tdom.py, request_context.py, and category_components.py.",
        ),
    ]

    return examples


def generate_multi_file_examples() -> list[Example]:
    """Generate examples that explore multiple files."""
    # These are simulated multi-turn conversations, but we'll create single-tool versions
    examples = [
        Example(
            user_query="Show me conftest.py in svcs-di",
            tool_name="read_file",
            tool_args={"path": "svcs-di/tests/conftest.py"},
            tool_result='"""Pytest configuration and shared fixtures."""\nimport pytest\nfrom svcs import Container, Registry\n\n\n@pytest.fixture\ndef registry():\n    """Shared registry fixture."""\n    return Registry()\n\n\n@pytest.fixture\ndef container(registry):\n    """Container with fresh registry."""\n    return Container(registry)',
            final_response="The conftest defines shared pytest fixtures: a registry fixture and a container fixture that uses it. These are used across all tests.",
        ),
        Example(
            user_query="Show me test_examples.py in tdom-svcs",
            tool_name="read_file",
            tool_args={"path": "tdom-svcs/tests/test_examples.py"},
            tool_result='"""Run all examples as tests using dynamic parametrization."""\nimport pytest\nfrom pathlib import Path\n\n# Discover all example files\nEXAMPLES_DIR = Path(__file__).parent.parent / "examples"\nexample_files = list(EXAMPLES_DIR.rglob("*.py"))\n\n\n@pytest.mark.parametrize("example_file", example_files)\ndef test_example_runs(example_file):\n    """Each example should run without errors."""\n    exec(example_file.read_text())',
            final_response="This test discovers all example files dynamically and runs each one as a separate test using pytest.mark.parametrize. Smart pattern for validating examples!",
        ),
    ]

    return examples


def generate_direct_answer_examples() -> list[Example]:
    """Generate examples where no tool is needed - mined from real documentation."""
    examples = []

    # Category 1: Concept Questions (~15 examples)
    # Source: svcs/docs/glossary.md, tdom-svcs/docs/core_concepts.md
    concepts = [
        ("What is dependency injection?", "Dependency injection means the service layer is called with all services it needs to do its job. Instead of constructing dependencies inside your functions, you pass them in as parameters, making your code testable and loosely coupled."),
        ("What is a service locator?", "A service locator is an architectural pattern that provides a central registry of factories for services that aren't instantiated directly in your business code. Unlike dependency injection, it's imperative: you ask for services explicitly at runtime using get() instead of having them injected."),
        ("What is inversion of control?", "Inversion of Control (IoC) describes the concept of your code being invoked by someone else based on configuration. It's sometimes called the Hollywood Principle: 'Don't call us, we'll call you.' A service locator is an example of IoC because you tell it how to create services and it invokes that factory when asked."),
        ("What is a composition root?", "The composition root is the place that acquires all the services your application needs and calls into the service layer. Common types are web framework views, CLI command entry points, or test fixtures. It's where you use svcs to get services and pass them into your business logic."),
        ("What is late binding?", "Late binding means the concrete instance type of a service is only determined when it's requested using container.get(). This makes your code very testable because you can easily replace services with test objects without brittle methods like monkey-patching."),
        ("What is the service layer?", "The service layer (also called orchestration layer or use-case layer) is where your business logic meets your services. It coordinates database transactions, other services, and the domain model. If you pass in all the services it needs, it's dependency injection. If you look up services within it, it's service location."),
        ("What is hexagonal architecture?", "Hexagonal architecture (also known as ports and adapters, onion architecture, or clean architecture) divides a system into loosely-coupled interchangeable components. The business code is in the middle and doesn't use services directly, but only through interfaces (ports). A service locator like svcs can register factories for those interfaces so business code can use services as adapters without knowing what they are."),
        ("What is the dependency inversion principle?", "The dependency inversion principle is the D in SOLID and means 'program against interfaces, not implementations.' The goal is to achieve loose coupling by making code depend on interfaces instead of concrete implementations. In Python's dynamic environment, you're free to ignore type hints in tests."),
        ("What is Inject[T] in svcs-di?", "Inject[T] is a type alias in svcs-di that marks a dataclass field for automatic dependency injection. When you use Inject[Database], svcs-di will automatically resolve and inject the Database service from the container. At runtime, svcs-di detects the Inject wrapper and resolves from the container."),
        ("What is a HopscotchRegistry?", "HopscotchRegistry extends svcs.Registry with built-in ServiceLocator for multi-implementation support. It's application-scoped and defines service factories and component registrations. Unlike a basic Registry, it supports multiple implementations of the same service type with resource and location-based resolution."),
        ("What is a HopscotchContainer?", "HopscotchContainer extends svcs.Container with a built-in inject() method for automatic dependency injection. It's request-scoped, created from a registry, and handles automatic dependency resolution. It supports resource-based and location-based service selection."),
        ("What are class components in tdom-svcs?", "Class components are Python classes (typically dataclasses) that can be discovered via @injectable decorator and resolved directly from the container. They use Inject[] for automatic dependency injection, implement __call__() to render output, and are the recommended approach for production use."),
        ("What is the Node type in tdom-svcs?", "The Node type from tdom provides a standard intermediate representation for HTML. It's a dataclass with tag, attrs, and children fields. Instead of producing HTML strings directly, templates produce Node trees which enable tools to inspect and act on structure before rendering."),
        ("What is package scanning in svcs-di?", "Package scanning via scan() automatically discovers @injectable decorated classes and registers them in the registry. It scans specified packages for modules, finds decorated classes, extracts metadata (resource, location, categories), and validates all items are classes."),
        ("What is the @injectable decorator?", "The @injectable decorator marks a class for automatic discovery by scan(). It can specify metadata like resource type, location, categories, and for_ (abstract interface). Only classes can be decorated with @injectable; functions cannot be discovered this way."),
    ]
    for query, response in concepts:
        examples.append(Example(user_query=query, tool_name=None, tool_args=None, tool_result=None, final_response=response))

    # Category 2: Comparison Questions (~10 examples)
    # Source: svcs/docs/glossary.md, svcs/docs/why.md, tdom-svcs/docs/core_concepts.md
    comparisons = [
        ("What is the difference between dependency injection and service location?", "Dependency injection means services are passed into your code as parameters from outside. Service location means your code actively asks for services at runtime using get(). Both achieve loose coupling, but DI is declarative while service location is imperative."),
        ("What is the difference between a Registry and a Container?", "Registry is application-scoped and stores factory functions and value services - it lives for the entire application lifetime and is shared across all containers. Container is request-scoped, creates and caches service instances from registry factories, and handles cleanup when closed."),
        ("What is the difference between Inject[T] and Resource[T]?", "Inject[T] resolves services from the registry/container - it gets services that were registered via register_factory or register_value. Resource[T] gets the current resource instance passed to the container constructor - it's the specific context object (like an HttpRequest) for the current request."),
        ("What is the difference between class and function components?", "Class components can use Inject[], be discovered via @injectable, be resolved from container, and are recommended for production. Function components can use Inject[] but cannot be discovered via @injectable, must be called directly with an injector, and are limited to simple programmatic use."),
        ("What is the difference between svcs and svcs-di?", "svcs is the core service locator library providing Registry and Container for manual service registration and retrieval. svcs-di builds on svcs to add automatic dependency injection via the Inject marker and auto() factory, eliminating boilerplate while preserving svcs patterns."),
        ("What is the difference between register_value and register_factory?", "register_value registers a singleton instance that's shared across all container.get() calls. register_factory registers a function that creates instances on demand - each container.get() may create a new instance or return a cached one depending on the container's lifetime."),
        ("What is the difference between resource-based and location-based resolution?", "Resource-based resolution selects implementations based on the current resource type (like CustomerContext vs AdminContext) - scored 100 for exact match, 10 for subclass. Location-based resolution selects based on URL path hierarchy (like /admin/users) - scored 1000 for match. Both can be combined for a total score up to 1100."),
        ("How does service location differ from service discovery?", "Service location (implemented by svcs) is about finding local objects in your application at runtime. Service discovery is a completely unrelated concept for finding remote services like web services or database servers (e.g., Consul, etcd, ZooKeeper)."),
        ("What is the difference between the Basic and Hopscotch patterns?", "The Basic pattern uses auto() wrapper with DefaultInjector for simple single-implementation services using standard svcs container. The Hopscotch pattern uses scan() with HopscotchRegistry for advanced features like multi-implementation support, resource/location-based resolution, and categories."),
        ("What is the difference between HopscotchContainer and KeywordInjector?", "HopscotchContainer is production-ready with built-in inject() method, resource/location-based resolution, and async support. KeywordInjector is educational only, works with function components, has no resource/location resolution, and is not suitable for production class components."),
    ]
    for query, response in comparisons:
        examples.append(Example(user_query=query, tool_name=None, tool_args=None, tool_result=None, final_response=response))

    # Category 3: Best Practices (~10 examples)
    # Source: svcs/docs/why.md, tdom-svcs/docs/how_it_works.md, svcs-di/docs/core-concepts.md
    best_practices = [
        ("When should I use svcs vs a DI framework?", "Use svcs when you want late binding, imperative service acquisition, and the flexibility to get services only when needed. The main trade-off is runtime verification vs compile-time. Use a DI framework like incant if you prefer declarative injection with ahead-of-time validation."),
        ("When should I use class components vs function components?", "Always use class components for production. They can be discovered via @injectable, resolved from container, easily tested and composed. Use function components only for simple educational examples or direct programmatic use."),
        ("How should I define services as dataclasses?", "Use frozen=True for immutability (thread-safe), kw_only=True for explicit call sites, and slots=True for memory efficiency. Keep services stateless with no business logic. Name them with a Service suffix. Services contain behavior but pass data back and forth - domain models make decisions."),
        ("When should I use the Hopscotch pattern vs the Basic pattern?", "Use Hopscotch when you need multiple implementations of the same service type, resource or location-based service selection, category-based organization, or convention-based setup functions. Use Basic for simple single-implementation services or when working with existing svcs code."),
        ("How should I test services in svcs-di?", "Use registry.register_value() to provide fakes (not mocks) for testing. Create fake implementations that behave like real services but use in-memory storage. This is better than mocking because fakes test actual behavior and interaction patterns."),
        ("When should I use categories in svcs-di?", "Use categories for plugin discovery (get all services tagged 'plugin'), middleware loading (get all 'middleware' services to build pipeline), or feature flags (check if service has 'experimental' category). Categories are string tags for organizing and querying services."),
        ("What is the recommended way to use svcs in views?", "Use svcs as a composition root in your views: call container.get() to acquire services, then pass them into your service layer via dependency injection. Don't use svcs directly in your service layer - keep business logic clean from framework code."),
        ("Should I use mocks or fakes for testing services?", "Use fakes. Create real implementations that behave correctly but use in-memory storage (like a FakeCache with a dict). Fakes test actual behavior and interaction patterns, while mocks are brittle and don't test what you actually care about."),
        ("When should I use scanning vs manual registration?", "Use scan() for production applications with many components - it automatically discovers @injectable classes and reduces boilerplate. Use manual registration for simple cases, tests, or when you need fine-grained control over registration order and configuration."),
        ("What are best practices for field ordering in component dataclasses?", "Put Inject[] fields first (they have no defaults), then regular parameters with defaults. This is a Python dataclass requirement, not tdom-svcs specific. Fields without defaults must come before fields with defaults to avoid TypeError."),
    ]
    for query, response in best_practices:
        examples.append(Example(user_query=query, tool_name=None, tool_args=None, tool_result=None, final_response=response))

    # Category 4: Syntax/How-to Questions (~10 examples)
    # Source: svcs-di/docs/core-concepts.md, tdom-svcs/docs/getting_started.md
    how_to = [
        ("How do I register a service in svcs-di?", "Use registry.register_value(Type, instance) for singletons shared across all containers, or registry.register_factory(Type, factory_function) for instances created on demand. The registry is application-scoped and should be created once at startup."),
        ("How do I use Inject[] in a dataclass?", "Import Inject from svcs_di and use it as a type annotation: 'field: Inject[ServiceType]'. Put Inject[] fields before fields with defaults. The service will be automatically resolved from the container when you call container.inject(YourClass)."),
        ("How do I create a component with dependency injection?", "Decorate your class with @injectable, make it a dataclass, use Inject[] for dependencies, and implement __call__() to render. Then scan(registry, package_name) to discover it, and use container.inject(ComponentType) to resolve with dependencies."),
        ("How do I set up a HopscotchContainer?", "Create a HopscotchRegistry, register services with register_value/register_factory, scan packages with scan(registry, package_name), then create HopscotchContainer(registry). Use it as a context manager: 'with HopscotchContainer(registry) as container:' for automatic cleanup."),
        ("How does the scan() function work?", "scan() takes a registry and package name (or __name__ for current module). It finds all modules in the package, looks for @injectable decorated classes, extracts metadata (resource, location, categories), and registers them automatically. Non-classes are skipped with a warning."),
        ("How do I override a service in tests?", "Create your test registry, call registry.register_value(ServiceType, FakeService()) to register your fake implementation, then create a container from that registry. The fake will be injected instead of the real service."),
        ("How do I register multiple implementations of a service?", "Use registry.register_implementation(ServiceType, ImplClass, resource=ResourceType, location=PurePath('/path')). Multiple implementations are scored based on resource (100 exact, 10 subclass) and location (1000) matching. Highest score wins, LIFO for ties."),
        ("How do I use PEP 750 t-strings for HTML?", "Use t-strings with the t prefix: t'<div>{variable}</div>'. Pass them to html() function which converts to Node trees. PEP 750 t-strings provide template interpolation at the language level, making HTML construction type-safe and IDE-friendly."),
        ("What Python version is needed for t-strings?", "Python 3.14 or later is required for PEP 750 template strings (t-strings). This is a language-level feature for template interpolation that tdom leverages for type-safe HTML construction."),
        ("How do I use the @middleware decorator?", "Create a dataclass with a priority field (lower executes first) and __call__(self, component, props, context) method. Return props to continue the chain or None to halt. Register with manager.register_middleware(YourMiddleware()). Async middleware with async __call__ is supported via execute_async()."),
    ]
    for query, response in how_to:
        examples.append(Example(user_query=query, tool_name=None, tool_args=None, tool_result=None, final_response=response))

    # Category 5: Documentation/Architecture (~5 examples)
    # Source: tdom-svcs/docs/node.md, various mission docs
    architecture = [
        ("What frameworks does svcs integrate with?", "svcs has official integrations for Flask, AIOHTTP, Starlette, FastAPI, and Pyramid. All integrations provide unified API for storing services on request objects and automatic cleanup. Most integrations are for async frameworks."),
        ("What is the tdom-svcs ecosystem?", "The ecosystem includes: tdom (Node type and templating), svcs-di (dependency injection), aria-testing (Testing Library-style queries), Storyville (component catalog), and tdom-django (Django integration). All tools work with Node as the standard intermediate representation."),
        ("How does tdom-django integrate with Django templates?", "tdom-django bridges Django templates with type-safe components. Components are dataclasses that become template tags automatically. You can use {% card title='Welcome' %} syntax in templates, and components can use Inject[] to request Django services from the container."),
        ("What is the architecture of a tdom-svcs application?", "Request arrives, components resolve with dependencies injected and overrides applied, middleware runs for validation/logging/asset collection, Node tree is built (components return Nodes not strings), post-processing happens on the tree, and finally the Node tree converts to HTML once at the end."),
        ("What problem does the Node standard solve?", "Python's web templating is fragmented - Jinja2, Mako, Django all produce strings directly, making it hard to test, compose tools, or analyze output. Node provides a standard intermediate representation so tools can inspect structure before rendering, enabling testing, validation, and asset collection."),
    ]
    for query, response in architecture:
        examples.append(Example(user_query=query, tool_name=None, tool_args=None, tool_result=None, final_response=response))

    return examples


def generate_write_file_examples() -> list[Example]:
    """Generate write_file examples."""
    examples = [
        Example(
            user_query="Create a new service class",
            tool_name="write_file",
            tool_args={
                "path": "src/services/user_service.py",
                "content": '"""User service."""\nfrom dataclasses import dataclass\n\n\n@dataclass\nclass UserService:\n    """Service for user operations."""\n\n    db: Database\n\n    def get_user(self, user_id: int) -> User:\n        """Fetch user by ID."""\n        return self.db.query(User, user_id)',
            },
            tool_result="File written successfully",
            final_response="Created UserService with a database dependency and get_user method.",
        ),
        Example(
            user_query="Create a tdom component",
            tool_name="write_file",
            tool_args={
                "path": "src/components/greeting.py",
                "content": '"""Greeting component."""\nfrom tdom import component\n\n\n@component\ndef greeting(name: str) -> str:\n    """Render a greeting."""\n    return t"<div>Hello, {name}!</div>"',
            },
            tool_result="File written successfully",
            final_response="Created a greeting component that takes a name and renders it in a div.",
        ),
    ]

    return examples


def main():
    """Generate all domain examples and write to output file."""
    all_examples = []

    print("Generating read_file examples...")
    all_examples.extend(generate_read_file_examples())

    print("Generating test file examples...")
    all_examples.extend(generate_test_file_examples())

    print("Generating run_command examples...")
    all_examples.extend(generate_run_command_examples())

    print("Generating multi-file examples...")
    all_examples.extend(generate_multi_file_examples())

    print("Generating direct answer examples...")
    all_examples.extend(generate_direct_answer_examples())

    print("Generating write_file examples...")
    all_examples.extend(generate_write_file_examples())

    # Convert to messages format
    messages = [create_messages(ex) for ex in all_examples]

    # Write to output file
    output_path = Path(__file__).parent.parent / "data" / "domain_examples.jsonl"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as f:
        for msg in messages:
            f.write(json.dumps(msg) + "\n")

    print(f"\nGenerated {len(messages)} domain examples -> {output_path}")
    print(f"  - {len(generate_read_file_examples())} read_file examples")
    print(f"  - {len(generate_test_file_examples())} test file examples")
    print(f"  - {len(generate_run_command_examples())} run_command examples")
    print(f"  - {len(generate_multi_file_examples())} multi-file examples")
    print(f"  - {len(generate_direct_answer_examples())} direct answer examples")
    print(f"  - {len(generate_write_file_examples())} write_file examples")


if __name__ == "__main__":
    main()
