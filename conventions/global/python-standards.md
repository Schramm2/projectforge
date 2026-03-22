### Python / FastAPI

- Type hints on all functions and variables
- Pydantic models for all data structures
- Async endpoints where possible
- No ORM - use raw SQL via asyncpg
- API routes prefixed with `/v1/`
- Structured error responses using Pydantic models for error bodies
- FastAPI exception handlers for consistent error formatting
- Ruff for linting and formatting
- Docstrings (triple double quotes) on all public modules, functions, classes, and methods
- Imports ordered: stdlib -> third-party -> local application. No wildcard imports.
