#### FastAPI

_Frontend-Backend Communication Optimisation_

**Dependency Injection & Singletons**

* Use @lru_cache(maxsize=1) or similar patterns to create singleton services

* Expensive objects (API clients, DB connections, ML models) should be instantiated once and reused

* Place singleton factories in a dedicated [dependencies.py](http://dependencies.py) or [services.py](http://services.py) file

* Inject dependencies into route handlers rather than creating them inline

**Combined Endpoints**

* Identify API calls that always happen in sequence from the frontend

* Combine into a single endpoint to reduce network round trips

* Load shared state once at the start, reuse across all operations

* Return all data the client needs in one response

**Eliminate Redundant Work**

* Don't recalculate values that were already computed upstream

* Pass pre-calculated results through the pipeline

* Persistence layers should store values, not recompute them

* Avoid instantiating services inside other services - inject them instead

**State Loading**

* Load state once per request, not once per operation

* Follow the pattern: load → process → persist

* Avoid repeated database queries for the same data within a request

#### Python

###### PEP 8 Naming Conventions

| Type              | Convention                              | Example                                     |
| ----------------- | --------------------------------------- | ------------------------------------------- |
| Modules           | Short, lowercase, underscores if needed | `my_module.py`                              |
| Packages          | Short, lowercase, no underscores        | `mypackage`                                 |
| Classes           | CapWords (PascalCase)                   | `MyClass`, `HTTPServer`                     |
| Exceptions        | CapWords, suffix with "Error"           | `ValidationError`, `ConnectionTimeoutError` |
| Functions         | lowercase_with_underscores              | `calculate_total()`, `get_user_by_id()`     |
| Methods           | lowercase_with_underscores              | `process_data()`, `validate_input()`        |
| Variables         | lowercase_with_underscores              | `user_count`, `total_amount`                |
| Constants         | UPPERCASE_WITH_UNDERSCORES              | `MAX_CONNECTIONS`, `DEFAULT_TIMEOUT`        |
| Type variables    | CapWords, short names                   | `T`, `KT`, `VT`, `AnyStr`                   |
| Private           | Single leading underscore               | `_internal_method()`, `_private_var`        |
| "Mangled" private | Double leading underscore               | `__mangled_name`                            |
| Magic/dunder      | Double leading and trailing underscores | `__init__`, `__str__`                       |

Imports:

* Imports should be on separate lines

* Group imports in this order: standard library, third-party, local application

* Use absolute imports over relative imports

* Avoid wildcard imports (`from module import *`)

Avoid extraneous whitespace:

* Immediately inside parentheses, brackets, or braces

* Between a trailing comma and a closing parenthesis

* Immediately before a comma, semicolon, or colon

* Immediately before the open parenthesis of a function call

Comments and Docstrings

* Write docstrings for all public modules, functions, classes, and methods

* Use triple double quotes (`"""`) for docstrings

* Follow a consistent docstring format

## Object-Oriented Programming

* Service Layer Structure: All business logic should be encapsulated within Service Classes (e.g., `UserService`) rather than standalone module-level functions. This ensures better organization and allows for easier extension of logic in the future.

* Dependency Injection: Service classes must be initialised with their dependencies (e.g., database sessions, external clients) via the `__init__` method, promoting testability and preventing reliance on global state.
