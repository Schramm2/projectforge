![9f5dbc47-0643-46bb-89b1-cccc902c3ac6](https://api.plane.so/api/assets/v2/workspaces/ubundi/9f5dbc47-0643-46bb-89b1-cccc902c3ac6/?disposition=inline)

# UBUNDI STANDARD REPOSITORY STRUCTURE

**Version:** 1.0.0 **Architecture Pattern:** Onion / Clean Architecture

This document outlines the standard folder structure and architectural principles for Ubundi Python projects. It explains the reasoning behind the separation of concerns and provides a blueprint for where code should reside.

## 1. ARCHITECTURE OVERVIEW

Our projects follow **Clean Architecture** (also known as Onion Architecture or Hexagonal Architecture). This design philosophy strictly enforces the dependency rule: **Dependencies point inwards.**

### Core Principles

* **Separation of Concerns:** Each layer has a distinct responsibility.

* **Dependency Inversion:** High-level policy does not depend on low-level detail. Details depend on policy.

* **Testability:** Business logic can be tested without UI, Database, or Web Server.

* **Framework Agnostic:** The core business logic doesn't know (or care) which framework handles the HTTP requests.

### The Onion Layers

```
+---------------------------------------------------------------------+
|                       Presentation Layer                            |
|               (API Routes, CLI Commands, UI Views)                  |
+---------------------------------------------------------------------+
|                        Application Layer                            |
|             (Use Cases, Orchestration, App Services)                |
+---------------------------------------------------------------------+
|                          Domain Layer                               |
|          (Entities, Business Rules, Value Objects, Logic)           |
+---------------------------------------------------------------------+
|                      Infrastructure Layer                           |
|       (Database Implementation, External APIs, File Systems)        |
+---------------------------------------------------------------------+
```

## 2. ROOT DIRECTORY STRUCTURE

```
project_root/
├── main.py                 # Application entry point / wiring
├── requirements.txt        # Production dependencies
├── requirements-dev.txt    # Development dependencies
├── README.md               # Setup and usage guide
├── .env                    # Secrets (API Keys, DB Credentials) - NEVER COMMIT
├── .example.env            # Template for environment variables
├── .gitignore              # Git ignore rules
│
├── domain/                 # INNERMOST: Core business logic (Pure Python)
├── application/            # INNER: Use cases & orchestration
├── infrastructure/         # OUTER: External implementations (DB, 3rd Party)
├── presentation/           # OUTER: User-facing interfaces (API, CLI)
├── shared/                 # SUPPORT: Cross-cutting utilities
│
├── tests/                  # Test suite (Unit & Integration)
├── docs/                   # Documentation
├── scripts/                # Devops/Utility scripts
├── data/                   # Local artifacts (SQLite, temp files)
└── logs/                   # Application logs
```

## 3. CORE LAYER DETAILS

### 3.1. domain/ (The Core)

**PURPOSE:** Contains the enterprise-wide logic and business rules. This layer **MUST NOT** depend on any other layer, nor any external frameworks (like Django, FastAPI, SQLAlcemy specific logic).

**REASONING:** This allows the business logic to remain stable even if the database changes or the UI is swapped.

**STRUCTURE:**

```
domain/
├── __init__.py
├── models/                 # Pure entities (Dataclasses/Pydantic)
│   ├── [entity]_model.py
│   └── value_objects.py
├── services/               # Pure domain logic/calculations
│   └── [logic]_service.py
└── interfaces/             # Abstract Base Classes (Protocols)
    └── repository_interfaces.py
```

**WHAT GOES HERE:**

* **Entities:** Objects that have an ID and lifecycle.

* **Value Objects:** Objects defined by their attributes (e.g., Coordinates, Money).

* **Domain Services:** Complex business logic that doesn't fit into a single entity.

* **Interfaces:** Definitions of what persistence/external services _should_ look like (implemented in Infrastructure).

### 3.2. application/ (The Orchestrator)

**PURPOSE:** Orchestrates the flow of data between the UI (Presentation) and the Business Rules (Domain). It implements **Use Cases**.

**REASONING:** This layer coordinates the application's specific actions. It retrieves data using interfaces and passes it to the domain for processing.

**STRUCTURE:**

```
application/
├── __init__.py
├── use_cases/              # Specific user actions
│   ├── create_[entity].py
│   └── process_[workflow].py
└── services/               # Application-specific logic
    └── orchestration_service.py
```

**WHAT GOES HERE:**

* **Use Cases:** "Create User", "Generate Report", "Process Payment".

* **DTOs (Data Transfer Objects):** Simple objects used to move data between layers.

* **Orchestration:** Calling a repository to get data $\to$ calling a domain service to calculate $\to$ saving results.

### 3.3. infrastructure/ (The Tools)

**PURPOSE:** Implements the technical details. Contains code that talks to "outside things" like databases, external APIs, or file systems.

**REASONING:** By isolating "dirty" details here, we can swap a SQL database for a NoSQL one, or OpenAI for Anthropic, by simply changing this layer.

**STRUCTURE:**

```
infrastructure/
├── __init__.py
├── persistence/            # Database access
│   ├── repositories/       # Implementation of Domain Interfaces
│   └── database_config.py
└── external/               # 3rd Party Integrations
    ├── email_service.py
    ├── payment_gateway.py
    └── llm_provider.py
```

**WHAT GOES HERE:**

* **Repositories:** SQL queries, ORM calls.

* **API Clients:** Wrappers for Stripe, OpenAI, AWS S3, etc.

* **Configuration:** Loading settings from environment variables.

### 3.4. presentation/ (The Interface)

**PURPOSE:** The entry point for users or other systems. It handles HTTP requests, CLI arguments, or socket events.

**REASONING:** The way a user interacts with the system (Web vs CLI) should not change the business rules.

**STRUCTURE:**

```
presentation/
├── api/                    # Web API
│   ├── routes/
│   └── schemas/            # Request/Response models
└── cli/                    # Command Line Interface
    └── commands.py
```

**WHAT GOES HERE:**

* **Controllers/Routes:** FastAPI/Flask/Django routes.

* **Serializers:** Converting Domain objects to JSON.

* **Argument Parsing:** Logic for reading CLI flags.

## 4. SUPPORT DIRECTORIES

### 4.1. shared/

Utilities used across multiple layers (e.g., Date formatting, Custom Exceptions, Logging setups). **Note:** Try to minimize dependencies here.

### 4.2. tests/

* **tests/unit:** Fast. Mocks everything. Tests `domain` and `application` logic.

* **tests/integration:** Slower. Tests `infrastructure` with real DBs or API sandboxes.

### 4.3. docs/

Architecture Decision Records (ADRs), Data Models, and Setup Guides.

## 5. DEPENDENCY FLOW RULES

Strict adherence to these rules is required for Pull Request approval.

1. **Presentation** $\to$ depends on $\to$ **Application**

2. **Application** $\to$ depends on $\to$ **Domain**

3. **Infrastructure** $\to$ depends on $\to$ **Domain** (It implements interfaces defined in Domain)

4. **Domain** $\to$ depends on $\to$ **NOTHING** (Standard Library only)

**Visualization:** `Presentation` calls `Application`. `Application` uses `Domain` logic. `Application` calls `Infrastructure` (via interfaces defined in `Domain`).

## 6. DEVELOPMENT WORKFLOW

**Adding a New Feature:**

1. **Domain:** Define the Models (Data) and Interfaces (What data do I need?).

2. **Infrastructure:** Implement the Interfaces (Connect to DB/API).

3. **Application:** Create the Use Case (Connect Domain logic with Infra data).

4. **Presentation:** Expose the Use Case (Create API Endpoint or CLI command).

**Naming Conventions:**

| Type           | Suffix            | Example                   |
| -------------- | ----------------- | ------------------------- |
| **Model**      | `*_model.py`      | `user_model.py`           |
| **Service**    | `*_service.py`    | `payment_service.py`      |
| **Repository** | `*_repository.py` | `user_repository.py`      |
| **Test**       | `test_*.py`       | `test_payment_service.py` |

_Last Updated: [CURRENT_DATE]_
