# Money Manager Architecture

This document describes the architectural patterns and conventions used in this project.

## Overview

The application follows **Clean Architecture** principles for the backend and **Feature-Based Layered Architecture** for the frontend. This separation ensures:

- **Testability**: Business logic is decoupled from frameworks
- **Maintainability**: Clear boundaries between layers
- **Scalability**: Easy to add new features without touching existing code

---

## Backend Architecture (Python/FastAPI)

### Directory Structure

```
app/
├── main.py                     # Application entry point (setup only)
├── database.py                 # Database configuration
├── models.py                   # SQLAlchemy ORM models
├── seed.py                     # Initial data seeding
│
├── api/                        # 🔵 HTTP/Presentation Layer
│   ├── __init__.py
│   ├── dependencies.py         # FastAPI dependency injection
│   ├── routes/                 # Route handlers (thin controllers)
│   │   ├── __init__.py
│   │   ├── accounts.py
│   │   ├── budgets.py
│   │   ├── categories.py
│   │   ├── imports.py
│   │   ├── rules.py
│   │   └── transactions.py
│   └── schemas/                # Pydantic request/response models
│       ├── __init__.py
│       ├── account.py
│       ├── budget.py
│       ├── category.py
│       ├── common.py
│       ├── imports.py
│       ├── rule.py
│       └── transaction.py
│
├── domain/                     # 🟢 Business Logic Layer
│   ├── __init__.py
│   ├── exceptions.py           # Custom domain exceptions
│   ├── utils.py                # Pure utility functions
│   └── services/               # Business logic services
│       ├── __init__.py
│       ├── account_service.py
│       ├── budget_service.py
│       ├── category_service.py
│       ├── import_service.py
│       ├── rule_service.py
│       └── transaction_service.py
│
└── infrastructure/             # 🟠 Data Access & External Services
    ├── __init__.py
    ├── repositories/           # Database abstraction
    │   ├── __init__.py
    │   ├── base.py
    │   ├── account_repository.py
    │   ├── budget_repository.py
    │   ├── category_repository.py
    │   ├── rule_repository.py
    │   └── transaction_repository.py
    ├── parsers/                # File parsing (CSV, Excel)
    │   ├── __init__.py
    │   ├── base.py
    │   ├── chase_parser.py
    │   ├── bofa_parser.py
    │   ├── excel_parser.py
    │   └── statement_parser.py
    └── ai/                     # AI/ML integrations
        ├── __init__.py
        └── categorization.py
```

### Layer Responsibilities

#### 🔵 API Layer (`app/api/`)

**Purpose**: Handle HTTP concerns only - no business logic.

**Routes** (`api/routes/`):
- Parse and validate incoming requests
- Call appropriate domain service
- Convert domain exceptions to HTTP responses
- Return formatted responses

```python
# Good: Route delegates to service
@router.post("", status_code=201)
def create_account(body: AccountIn, service: AccountService = Depends(get_account_service)):
    try:
        account_id = service.create(name=body.name, group=body.group, ...)
        return IdResponse(id=account_id)
    except DomainException as e:
        raise handle_domain_exception(e)

# Bad: Route contains business logic
@router.post("")
def create_account(body: AccountIn, db: Session = Depends(get_db)):
    if body.group == "Card":
        body.is_liability = True  # Business logic leaked!
    account = Account(...)
    db.add(account)
    db.commit()
```

**Schemas** (`api/schemas/`):
- Define request validation (Pydantic `BaseModel`)
- Define response shapes
- Use `*In` suffix for requests, `*Out` for responses, `*Patch` for updates

```python
class AccountIn(BaseModel):    # Request
    name: str
    group: Literal["Cash", "Accounts", "Card", "Savings"]

class AccountOut(BaseModel):   # Response
    id: int
    name: str
    balance: float
```

#### 🟢 Domain Layer (`app/domain/`)

**Purpose**: All business logic lives here. Framework-agnostic.

**Services** (`domain/services/`):
- Contain all business rules and validation
- Orchestrate repositories and other services
- Raise domain exceptions (not HTTP exceptions)

```python
class AccountService:
    def __init__(self, db: Session):
        self.repo = AccountRepository(db)

    def create(self, name: str, group: str, ...) -> int:
        # Business rule: Cards are always liabilities
        if group == "Card":
            is_liability = True

        account = Account(...)
        self.repo.add(account)
        try:
            self.repo.commit()
        except IntegrityError:
            raise DuplicateError("Account with that name exists")
        return account.id
```

**Exceptions** (`domain/exceptions.py`):
- Domain-specific exception hierarchy
- Converted to HTTP errors by API layer

```python
class DomainException(Exception): ...
class NotFoundError(DomainException): ...
class DuplicateError(DomainException): ...
class ValidationError(DomainException): ...
```

**Utils** (`domain/utils.py`):
- Pure functions with no side effects
- Shared utilities (e.g., `to_cents()`, `from_cents()`, `parse_date()`)

#### 🟠 Infrastructure Layer (`app/infrastructure/`)

**Purpose**: External integrations and data access.

**Repositories** (`infrastructure/repositories/`):
- Abstract database operations
- One repository per entity
- Inherit from `BaseRepository` for common CRUD

```python
class AccountRepository(BaseRepository[Account]):
    def get_by_suffix(self, suffix: str) -> Optional[Account]: ...
    def calculate_balances(self) -> dict[int, int]: ...
```

**Parsers** (`infrastructure/parsers/`):
- Parse external file formats (CSV, Excel)
- Return standardized `ParsedTransaction` objects

**AI** (`infrastructure/ai/`):
- External AI service integrations (Ollama)
- Isolated from business logic

### Data Flow

```
HTTP Request
    ↓
┌─────────────────────────────────────────┐
│ API Layer (routes/)                     │
│  - Validate request (schemas/)          │
│  - Get service via dependency injection │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Domain Layer (services/)                │
│  - Execute business logic               │
│  - Use repositories for data access     │
│  - Raise domain exceptions              │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│ Infrastructure Layer                    │
│  - Repositories: Database operations    │
│  - Parsers: File parsing                │
│  - AI: External AI services             │
└─────────────────────────────────────────┘
    ↓
Database / External Services
```

### Dependency Injection

Services are injected via FastAPI's `Depends()`:

```python
# api/dependencies.py
def get_account_service(db: Session = Depends(get_db)) -> AccountService:
    return AccountService(db)

# api/routes/accounts.py
@router.get("")
def list_accounts(service: AccountService = Depends(get_account_service)):
    return service.get_summary()
```

---

## Frontend Architecture (React)

### Target Directory Structure

```
frontend/src/
├── main.jsx                    # Entry point
├── App.jsx                     # Routing + providers only
│
├── api/                        # 🔵 API Layer
│   ├── client.js               # HTTP client (fetch/axios wrapper)
│   ├── accounts.js             # Account API calls
│   ├── transactions.js         # Transaction API calls
│   └── ...
│
├── hooks/                      # 🟢 Shared Hooks
│   ├── useAsync.js             # Generic async state management
│   ├── useAccounts.js          # Account data hook
│   ├── useCategories.js        # Category data hook
│   └── useMonthParam.js        # URL month parameter
│
├── components/                 # 🟡 Shared UI Components
│   ├── Table/
│   │   ├── Table.jsx
│   │   ├── SortableHeader.jsx
│   │   └── index.js
│   ├── CategoryTree/
│   ├── MoneyDisplay/
│   ├── ProgressBar/
│   └── LoadingSpinner/
│
├── features/                   # 🟠 Feature Modules
│   ├── accounts/
│   │   ├── AccountsPage.jsx
│   │   └── AccountRow.jsx
│   ├── transactions/
│   │   ├── TransactionsPage.jsx
│   │   ├── TransactionTable.jsx
│   │   ├── TransactionFilters.jsx
│   │   └── useTransactions.js
│   ├── budgets/
│   ├── categories/
│   ├── rules/
│   ├── import/
│   ├── dashboard/
│   └── reports/                # P&L reports
│       ├── PLReportPage.jsx
│       ├── IncomeSection.jsx
│       ├── ExpenseSection.jsx
│       └── usePLReport.js
│
└── utils/                      # 🔵 Utilities
    ├── formatters.js           # formatMoney, formatDate
    ├── calculations.js         # Business calculations
    └── constants.js
```

### Layer Responsibilities

#### 🔵 API Layer (`api/`)
- HTTP client wrapper
- Domain-organized API functions
- Response normalization

#### 🟢 Hooks Layer (`hooks/`)
- Reusable data fetching hooks
- State management abstractions
- Shared across features

#### 🟡 Components (`components/`)
- Reusable UI components
- No business logic
- Pure presentation

#### 🟠 Features (`features/`)
- Self-contained feature modules
- Feature-specific components, hooks, and pages
- Each feature is independent

---

## Conventions

### Naming

| Type | Convention | Example |
|------|------------|---------|
| Services | `*Service` | `AccountService` |
| Repositories | `*Repository` | `AccountRepository` |
| Request schemas | `*In` | `AccountIn` |
| Response schemas | `*Out` | `AccountOut` |
| Update schemas | `*Patch` | `AccountPatch` |
| Exceptions | `*Error` | `NotFoundError` |
| React hooks | `use*` | `useAccounts` |
| React pages | `*Page` | `AccountsPage` |

### Money Handling

- **Always store as integer cents** to avoid floating-point errors
- Use `to_cents()` and `from_cents()` for conversion
- Display layer handles formatting

### Error Handling

- Domain layer raises `DomainException` subclasses
- API layer converts to `HTTPException`
- Never expose stack traces to clients

### Testing

- Unit test services with mocked repositories
- Integration test repositories with test database
- E2E test routes with test client

---

## Adding a New Feature

### Backend

1. **Create schemas** in `api/schemas/newfeature.py`
2. **Create repository** in `infrastructure/repositories/newfeature_repository.py`
3. **Create service** in `domain/services/newfeature_service.py`
4. **Create routes** in `api/routes/newfeature.py`
5. **Register routes** in `api/routes/__init__.py`

### Frontend

1. **Create API functions** in `api/newfeature.js`
2. **Create feature directory** `features/newfeature/`
3. **Create page component** `NewFeaturePage.jsx`
4. **Create feature-specific hooks** if needed
5. **Add route** in `App.jsx`
