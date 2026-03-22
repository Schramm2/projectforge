# Python Cross-Project Defaults

- pyproject.toml with hatchling build system
- Ruff for linting and formatting with rules: ["E", "F", "I", "N", "W", "UP", "B"]
- Line length: 100
- Python target: 3.12
- Package manager: uv
- MyPy with --strict for type checking
- pytest for testing, pytest-cov for coverage
- Include a .pre-commit-config.yaml with ruff hooks
- No ORM - use raw SQL via asyncpg for database access
- API routes prefixed with `/v1/` (e.g. `/v1/users`, `/v1/items`)
- Backend services must include a `/health` or `/ready` endpoint
- Structured error responses: use Pydantic models for error bodies
- FastAPI exception handlers for consistent error formatting across all routes
- Tests in three tiers: tests/unit/, tests/integration/, tests/manual/ (optional)
- PEP 8 naming: snake_case (modules, functions, variables), PascalCase (classes, Pydantic models), UPPER_SNAKE_CASE (constants)
- Import order: stdlib -> third-party -> local application. No wildcard imports.
- Docstrings (triple double quotes) on all public modules, functions, classes, and methods
- Service Layer: business logic in Service Classes with DI via __init__, not standalone functions
