## Python Architecture

Follow Clean Architecture (Onion Architecture). Dependencies point inward.

### Layer Structure

- domain/: Core business logic - entities, value objects, domain services, interfaces (Protocols). Depends on NOTHING (stdlib only).
- application/: Use cases and orchestration. Depends only on domain.
- infrastructure/: External implementations - DB repositories, API clients, config loading. Implements interfaces defined in domain.
- api/: Presentation layer - FastAPI routes, request/response schemas. Depends on application.
- shared/: Cross-cutting utilities used across layers. Keep minimal.

### Dependency Flow

Presentation (api/) -> Application -> Domain <- Infrastructure

### Service Layer Pattern

- Encapsulate business logic in Service Classes (e.g., UserService), not standalone functions.
- Inject dependencies via `__init__` (database sessions, external clients).
- No global state - all state passed through constructor or method params.

### FastAPI Patterns

- Use `@lru_cache` for singleton services in a dedicated `dependencies.py` file.
- Load state once per request: load -> process -> persist. No repeated DB queries for the same data.
- Inject services into route handlers - never instantiate inline.
- Combined endpoints: if the frontend always calls two endpoints in sequence, combine them.

### File Naming

- Models: `*_model.py` (e.g., `user_model.py`)
- Services: `*_service.py` (e.g., `payment_service.py`)
- Repositories: `*_repository.py` (e.g., `user_repository.py`)
- Tests: `test_*.py` (e.g., `test_payment_service.py`)
