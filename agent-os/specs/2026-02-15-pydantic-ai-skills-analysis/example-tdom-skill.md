# Example: tdom-components Skill — End-to-End Flow

**Purpose:** Concrete example showing how a user generates a tdom component using the Monty + Skills architecture.

## User Session Example

### Interaction 1: Discover Available Skills

**User:**
```
What skills do you have for building UI components?
```

**Punie (internal tool call):**
```python
list_skills(category="ui")
→ ["tdom-components", "htmx-patterns", "css-utilities"]
```

**Punie (response):**
```
I have these UI skills:
- **tdom-components**: Generate tdom views with type-safe HTML and dependency injection
- **htmx-patterns**: Add HTMX interactions to components
- **css-utilities**: Generate Tailwind/utility CSS

Which would you like to use?
```

### Interaction 2: Load Skill Details

**User:**
```
Tell me about tdom-components
```

**Punie (internal tool call):**
```python
load_skill("tdom-components")
→ {
    "name": "tdom-components",
    "description": "Generate tdom components/views...",
    "patterns": ["@view decorator", "html(t'...')", "..."],
    "examples": [...],
    "validation_rules": [...]
}
```

**Punie (response):**
```
The tdom-components skill helps you create type-safe HTML views using PEP 750 t-strings.

Key patterns:
- Use @view decorator for component functions
- Return Element type
- Use html(t"...") for HTML generation
- Inject dependencies via keyword-only args

Example:
@view
def hello_view(name: str) -> Element:
    return html(t"<h1>Hello, {name}!</h1>")

Would you like me to generate a component for you?
```

### Interaction 3: Generate Component

**User:**
```
Create a UserProfileView that shows:
- User avatar (img tag)
- Username in h2
- Bio paragraph
- "Edit Profile" button

It should accept a User object via dependency injection.
```

**Punie (internal reasoning):**
```
1. Load tdom-components skill (already loaded)
2. Extract requirements:
   - Name: UserProfileView
   - Elements: avatar img, h2 username, p bio, button
   - Dependencies: User object injected
3. Generate code using skill patterns
4. Validate against TdomComponentSchema
5. Save to project
```

**Punie (tool call):**
```python
generate_artifact(
    artifact_type="component",
    name="user_profile_view",
    description="User profile view with avatar, username, bio, and edit button",
    code="""
from tdom import html, t, Element
from hopscotch import view
from myapp.models import User

@view
def user_profile_view(user_id: int, *, user_service: UserService) -> Element:
    \"\"\"Display user profile with avatar, name, bio, and edit button.

    Args:
        user_id: ID of user to display
        user_service: Service for fetching user data (injected)

    Returns:
        Element with user profile HTML
    \"\"\"
    user = user_service.get(user_id)

    return html(t'''
        <div class="user-profile">
            <img
                src="{user.avatar_url}"
                alt="{user.username}'s avatar"
                class="avatar"
            />
            <h2>{user.username}</h2>
            <p class="bio">{user.bio}</p>
            <button class="edit-btn">Edit Profile</button>
        </div>
    ''')
"""
)
```

**Validation (internal):**
```
✓ Syntax valid (ast.parse succeeds)
✓ Has @view decorator
✓ Returns Element type
✓ Uses html(t"...") pattern
✓ Function name ends with _view
✓ Dependencies keyword-only
✓ Type check passes (ty)
```

**Punie (response):**
```
✓ Created user_profile_view component at: src/myapp/views/user_profile.py

The component:
- Accepts user_id as positional arg
- Injects UserService via keyword arg
- Fetches user data from service
- Renders avatar, username, bio, and edit button
- Returns type-safe Element

Would you like me to:
1. Generate tests for this component?
2. Add it to a route?
3. Create the UserService if it doesn't exist?
```

### Interaction 4: Generate Tests

**User:**
```
Yes, generate tests
```

**Punie (tool call):**
```python
generate_artifact(
    artifact_type="test",
    name="test_user_profile_view",
    description="Tests for user_profile_view component",
    code="""
import pytest
from myapp.views.user_profile import user_profile_view
from myapp.models import User
from myapp.services import UserService

@pytest.fixture
def mock_user():
    return User(
        id=1,
        username="alice",
        avatar_url="https://example.com/avatar.jpg",
        bio="Software developer"
    )

@pytest.fixture
def mock_user_service(mock_user):
    class MockUserService:
        def get(self, user_id: int) -> User:
            return mock_user
    return MockUserService()

def test_user_profile_view_renders_username(mock_user_service):
    result = user_profile_view(1, user_service=mock_user_service)
    html_str = str(result)
    assert "alice" in html_str

def test_user_profile_view_renders_avatar(mock_user_service):
    result = user_profile_view(1, user_service=mock_user_service)
    html_str = str(result)
    assert "https://example.com/avatar.jpg" in html_str
    assert "alt=\\"alice's avatar\\"" in html_str

def test_user_profile_view_renders_bio(mock_user_service):
    result = user_profile_view(1, user_service=mock_user_service)
    html_str = str(result)
    assert "Software developer" in html_str

def test_user_profile_view_has_edit_button(mock_user_service):
    result = user_profile_view(1, user_service=mock_user_service)
    html_str = str(result)
    assert "Edit Profile" in html_str
"""
)
```

**Punie (response):**
```
✓ Created tests at: tests/views/test_user_profile_view.py

Tests cover:
- Username rendering
- Avatar with alt text
- Bio paragraph
- Edit button presence

Run tests with: uv run pytest tests/views/test_user_profile_view.py
```

### Interaction 5: Behind the Scenes — Training Data Collection

**Training collector automatically records:**

```json
{
  "timestamp": "2026-02-15T10:30:00",
  "artifact_type": "component",
  "user_request": "Create a UserProfileView that shows: avatar, username in h2, bio paragraph, edit button. Accept User via DI.",
  "generated_code": "from tdom import html...",
  "validation_passed": true,
  "type_check_passed": true,
  "test_generated": true,
  "file_path": "src/myapp/views/user_profile.py",
  "metadata": {
    "skill_used": "tdom-components",
    "retries": 0,
    "tokens_used": 450
  }
}
```

**This becomes training data for Phase 27:**

```
<|im_start|>system
You are Punie, an AI coding assistant expert in tdom-svcs architecture...
<|im_end|>
<|im_start|>user
Create a UserProfileView that shows: avatar, username in h2, bio paragraph, edit button. Accept User via DI.
<|im_end|>
<|im_start|>assistant
I'll generate a tdom component using the @view decorator and html(t"...") pattern:

<tool_call><function=generate_artifact>
<parameter=artifact_type>component</parameter>
<parameter=name>user_profile_view</parameter>
<parameter=code>
from tdom import html, t, Element
from hopscotch import view
from myapp.models import User

@view
def user_profile_view(user_id: int, *, user_service: UserService) -> Element:
    """Display user profile..."""
    user = user_service.get(user_id)
    return html(t'''...''')
</parameter>
</function></tool_call>
<|im_end|>
<|im_start|>user
<tool_response>
Validation passed. File saved to src/myapp/views/user_profile.py
</tool_response>
<|im_end|>
<|im_start|>assistant
✓ Created user_profile_view component at: src/myapp/views/user_profile.py
<|im_end|>
```

## Implementation Details

### File Structure After Generation

```
myapp/
├── src/
│   └── myapp/
│       ├── models/
│       │   └── user.py                    # User dataclass
│       ├── services/
│       │   └── user_service.py            # UserService (to be generated)
│       └── views/
│           └── user_profile.py            # ← Generated component
└── tests/
    └── views/
        └── test_user_profile_view.py      # ← Generated tests
```

### Generated user_profile.py (Full File)

```python
"""User profile view component."""

from tdom import html, t, Element
from hopscotch import view
from myapp.models import User
from myapp.services import UserService

@view
def user_profile_view(user_id: int, *, user_service: UserService) -> Element:
    """Display user profile with avatar, name, bio, and edit button.

    Args:
        user_id: ID of user to display
        user_service: Service for fetching user data (injected via svcs)

    Returns:
        Element with user profile HTML

    Example:
        >>> container = Container()
        >>> container.register(UserService, factory=...)
        >>> view = user_profile_view(1, user_service=container.get(UserService))
        >>> print(view)
        <div class="user-profile">...</div>
    """
    user = user_service.get(user_id)

    return html(t'''
        <div class="user-profile">
            <img
                src="{user.avatar_url}"
                alt="{user.username}'s avatar"
                class="avatar"
            />
            <h2>{user.username}</h2>
            <p class="bio">{user.bio}</p>
            <button class="edit-btn">Edit Profile</button>
        </div>
    ''')
```

### Validation That Ran

**TdomComponentSchema validation (Layered Approach):**

The validation uses a layered approach combining ast (fast gate) and libcst (convention checking):

```python
# ═══════════════════════════════════════════════════════════
# Layer 1: Fast Syntax Check (ast)
# ═══════════════════════════════════════════════════════════
import ast

ast.parse(code)  # ✓ No SyntaxError (~10x faster than libcst)

# ═══════════════════════════════════════════════════════════
# Layer 2: Convention Checking (libcst matchers)
# ═══════════════════════════════════════════════════════════
import libcst as cst
import libcst.matchers as m

tree = cst.parse_module(code)
functions = m.findall(tree, m.FunctionDef())
assert len(functions) > 0  # ✓ Found user_profile_view

func = functions[0]

# Check @view decorator using matchers API (more ergonomic)
has_view = m.matches(
    func,
    m.FunctionDef(decorators=[m.AtLeastN(
        n=1,
        matcher=m.Decorator(decorator=m.Name("view"))
    )])
)
assert has_view  # ✓ Has @view decorator

# Check return type annotation
assert func.returns is not None  # ✓ Returns Element
assert m.matches(func.returns, m.Annotation(annotation=m.Name("Element")))  # ✓ Correct type

# Check html(t"...") usage pattern
has_html_call = bool(m.findall(
    func,
    m.Call(func=m.Name("html"))
))
assert has_html_call  # ✓ Uses html()

# Check keyword-only dependencies
params = func.params
kw_only_params = params.kwonly_params
assert len(kw_only_params) > 0  # ✓ Has keyword-only args
assert any(p.name.value == "user_service" for p in kw_only_params)  # ✓ Service injected

# ═══════════════════════════════════════════════════════════
# Layer 3: Type Checking (external tool)
# ═══════════════════════════════════════════════════════════
import subprocess

result = subprocess.run(["ty", "check", file_path])
assert result.returncode == 0  # ✓ Type check passed
```

**Why layered?**
- **ast**: Fast syntax gate (~10x faster than libcst, built-in)
- **libcst matchers**: Ergonomic pattern matching for convention checking
- **libcst transformers** (not shown): Can auto-fix validation errors while preserving formatting
- **ty**: External type checker for semantic correctness

This approach enables **validate-then-fix** workflows where the model can retry with corrections.

## Skill Definition File

**punie/skills/tdom-components/SKILL.md:**

```yaml
---
name: tdom-components
version: "1.0.0"
description: Generate tdom views with type-safe HTML and dependency injection
requires:
  - tdom>=0.1.0
  - svcs-di>=0.1.0
  - hopscotch>=0.1.0
patterns:
  - "@view decorator"
  - "html(t'...')"
  - "Return Element type"
  - "Keyword-only dependency injection"
validation:
  - syntax_check
  - has_view_decorator
  - returns_element
  - uses_html_t_string
  - keyword_only_deps
examples:
  - basic_view
  - view_with_services
  - nested_components
---

# tdom Components Skill

Generate type-safe tdom components following svcs-di patterns.

## When to Use

Use this skill when the user asks to:
- "Create a {name} view/component"
- "Build a UI for {feature}"
- "Generate a component that shows {elements}"
- "Add a page/view for {purpose}"

## Core Patterns

### Pattern 1: Basic View

The simplest tdom component:

```python
from tdom import html, t, Element
from hopscotch import view

@view
def hello_view(name: str) -> Element:
    """Display a greeting.

    Args:
        name: Name to greet

    Returns:
        Element with greeting HTML
    """
    return html(t"<h1>Hello, {name}!</h1>")
```

**Key elements:**
- `@view` decorator marks it as a view component
- Returns `Element` type (required)
- Uses `html(t"...")` for HTML generation
- Type hints on all parameters

### Pattern 2: View with Dependency Injection

Components that need services:

```python
from tdom import html, t, Element
from hopscotch import view
from svcs import Container

@view
def user_list_view(*, user_service: UserService) -> Element:
    """Display list of all users.

    Args:
        user_service: Service for user data (injected)

    Returns:
        Element with user list HTML
    """
    users = user_service.get_all()

    user_items = [
        html(t"<li>{user.username}</li>")
        for user in users
    ]

    return html(t'''
        <div class="user-list">
            <h2>Users</h2>
            <ul>{user_items}</ul>
        </div>
    ''')
```

**Key elements:**
- Dependencies are **keyword-only** (after `*`)
- svcs automatically injects services
- Can compose multiple `html()` calls
- Interpolate lists directly in templates

### Pattern 3: View with Mixed Args

Combine positional args + injected dependencies:

```python
@view
def user_detail_view(
    user_id: int,
    *,
    user_service: UserService,
    auth_service: AuthService
) -> Element:
    """Display single user details.

    Args:
        user_id: ID of user to show (from route)
        user_service: User data service (injected)
        auth_service: Auth service (injected)

    Returns:
        Element with user details
    """
    user = user_service.get(user_id)
    can_edit = auth_service.can_edit(user)

    edit_button = (
        html(t"<button>Edit</button>")
        if can_edit else None
    )

    return html(t'''
        <div class="user-detail">
            <h2>{user.username}</h2>
            <p>{user.bio}</p>
            {edit_button}
        </div>
    ''')
```

**Key elements:**
- Positional args for route params
- Keyword-only for injected services
- Conditional rendering with None/False
- Multiple service dependencies

## Validation Rules

Generated components must pass these checks:

1. ✓ **Syntax valid** — `ast.parse()` succeeds
2. ✓ **Has @view decorator** — Required for component registration
3. ✓ **Returns Element** — Type annotation must be `-> Element`
4. ✓ **Uses html(t"...")** — Must use t-strings, not f-strings
5. ✓ **Keyword-only deps** — Services after `*` separator
6. ✓ **Type check passes** — `ty check` returns 0
7. ✓ **Function name ends with _view** — Naming convention

## Common Mistakes & Fixes

### ❌ Mistake 1: Using f-strings instead of t-strings

```python
# WRONG
return html(f"<h1>{name}</h1>")

# CORRECT
return html(t"<h1>{name}</h1>")
```

**Why:** t-strings provide type safety and proper escaping.

### ❌ Mistake 2: Missing @view decorator

```python
# WRONG
def my_view() -> Element:
    return html(t"<div>...</div>")

# CORRECT
@view
def my_view() -> Element:
    return html(t"<div>...</div>")
```

**Why:** @view registers the component with Hopscotch.

### ❌ Mistake 3: Returning string instead of Element

```python
# WRONG
def my_view() -> str:
    return str(html(t"<div>...</div>"))

# CORRECT
def my_view() -> Element:
    return html(t"<div>...</div>")
```

**Why:** Components must return Element for composition.

### ❌ Mistake 4: Positional dependencies

```python
# WRONG
def my_view(user_service: UserService) -> Element:
    ...

# CORRECT
def my_view(*, user_service: UserService) -> Element:
    ...
```

**Why:** Dependencies must be keyword-only for injection.

## Reference Examples

See `examples/` directory for:
- `basic_view.py` — Simple component with no dependencies
- `service_view.py` — Component with injected service
- `nested_view.py` — Composing multiple components
- `conditional_view.py` — Conditional rendering patterns
- `list_view.py` — Rendering lists of items

## Related Skills

- **svcs-services** — Generate services to inject
- **htmx-patterns** — Add HTMX interactions
- **css-utilities** — Style components
- **test-generation** — Generate pytest tests
```

## Schema Definition

**punie/skills/tdom-components/schemas/component_schema.py:**

```python
"""Validation schema for tdom components."""

from pydantic import BaseModel, Field, field_validator
import ast
import subprocess
from pathlib import Path

class TdomComponentSchema(BaseModel):
    """Schema for validating generated tdom components."""

    code: str = Field(description="Python source code")
    name: str = Field(description="Function name")
    file_path: Path | None = Field(default=None, description="Where to save")

    @field_validator("code")
    def validate_structure(cls, code: str) -> str:
        """Validate component structure using AST analysis."""
        # Parse syntax
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Syntax error: {e}")

        # Find function definition
        functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        if not functions:
            raise ValueError("No function definition found")

        func = functions[0]

        # Check @view decorator
        has_view_decorator = any(
            (isinstance(d, ast.Name) and d.id == "view")
            or (isinstance(d, ast.Attribute) and d.attr == "view")
            for d in func.decorator_list
        )
        if not has_view_decorator:
            raise ValueError("Missing @view decorator")

        # Check return type annotation
        if func.returns is None:
            raise ValueError("Missing return type annotation")

        returns_element = (
            (isinstance(func.returns, ast.Name) and func.returns.id == "Element")
            or (isinstance(func.returns, ast.Attribute) and func.returns.attr == "Element")
        )
        if not returns_element:
            raise ValueError("Must return Element type")

        # Check for html(t"...") usage
        has_html_call = any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Name)
            and n.func.id == "html"
            for n in ast.walk(func)
        )
        if not has_html_call:
            raise ValueError("Must use html(t'...') for HTML generation")

        # Check keyword-only parameters for dependencies
        if func.args.kwonlyargs:
            # Has keyword-only args - good!
            pass
        else:
            # No keyword-only args - might be ok if no dependencies
            # We'll allow it but warn
            pass

        return code

    @field_validator("name")
    def validate_naming(cls, name: str) -> str:
        """Validate naming conventions."""
        if not name.endswith("_view"):
            raise ValueError("View function names must end with '_view'")

        if not name.islower():
            raise ValueError("Function names must be lowercase with underscores")

        return name

    def validate_types(self, file_path: Path) -> list[str]:
        """Run ty type checker on the file."""
        result = subprocess.run(
            ["ty", "check", str(file_path)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            errors = result.stderr.split("\n")
            return [e for e in errors if e.strip()]

        return []
```

## Summary

This example shows:

1. **User flow** — Natural conversation from discovery → generation → testing
2. **Progressive disclosure** — Load skill docs only when needed
3. **Validation** — Multi-layer checks ensure quality
4. **Training data collection** — Automatic capture for future fine-tuning
5. **Practical output** — Real code that works in real projects

**Next:** Implement this for real with Milestone 1 deliverables.
