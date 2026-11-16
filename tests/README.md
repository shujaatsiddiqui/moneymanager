# Money Manager Tests

Comprehensive test suite for the Money Manager application.

## Test Structure

```
tests/
├── conftest.py                  # Pytest configuration and fixtures
├── test_api.py                  # Basic API tests (original)
├── test_api_comprehensive.py    # Comprehensive API endpoint tests
├── test_services.py             # Backend logic (services, parsers, utils)
└── README.md                    # This file
```

## Test Coverage

### API Tests (`test_api_comprehensive.py`)

**Accounts API**
- GET /accounts - List all accounts with balances
- PATCH /accounts/{id} - Update account
- GET /accounts/credit-card-dues - Credit card due dates

**Categories API**
- GET /categories - Get category tree
- POST /categories - Create category
- PATCH /categories/{id} - Update category
- DELETE /categories/{id} - Delete category

**Transactions API**
- POST /transactions - Create expense/income/refund/transfer
- GET /transactions - List with filters (month, category, account)
- PATCH /transactions/{id} - Update transaction
- DELETE /transactions/{id} - Delete transaction
- POST /transactions/detect-transfers - Auto-detect transfers

**Budgets API (with Net Expense Tests)**
- GET /budgets/status - Get budget status for month
- PUT /budgets - Set category budget
- DELETE /budgets - Delete category budget
- POST /budgets/copy - Copy budgets to another month
- **Net expense calculation**: Validates expenses - refunds = net spending

**Rules API**
- GET /rules - List all rules
- POST /rules - Create categorization rule
- DELETE /rules/{id} - Delete rule
- POST /rules/apply - Apply rules to uncategorized transactions
- POST /rules/suggest - Suggest pattern from description

**Imports API**
- GET /import/ai-status - Check AI availability
- POST /import - Import statement files with refund detection
- GET /import/history - Import batch history

**Reports/P&L API (with Net Expenses)**
- GET /reports/profit-loss - Monthly P&L report
- GET /reports/profit-loss/ytd - Year-to-date P&L
- **Net expenses**: Validates expenses - refunds in reports

**Validation & Error Handling**
- Invalid month formats
- Negative amounts
- Missing required fields
- Invalid IDs

**Integration Tests**
- Complete workflows (expense → refund → verify net)
- Rule creation and application
- Multi-step operations

---

### Service Tests (`test_services.py`)

**BudgetService**
- Create new budgets
- Update existing budgets
- **Net spending calculation** (expenses - refunds per category)
- Delete budgets

**ImportService**
- **Refund detection**: Income on credit cards → refunds
- Duplicate transaction detection and skipping
- Transaction import workflow

**TransactionService**
- Create transactions
- Transfer validation (requires to_account_id)
- Delete transactions
- Auto-categorization

**ReportService**
- **P&L net expenses**: Expenses - refunds
- Operating vs non-operating separation
- Income/expense breakdown

**RuleService**
- Create categorization rules
- Pattern suggestion from descriptions
- Apply rules to existing transactions
- Amount range filtering

**BaseParser**
- **Refund pattern detection** (RETURN, REFUND, REVERSAL, etc.)
- Transaction kind determination
- Transfer detection

**Domain Utils**
- to_cents() - Convert dollars to cents
- from_cents() - Convert cents to dollars
- month_range() - Generate date ranges

---

## Running Tests

### Run All Tests
```bash
pytest tests/ -v
```

### Run Specific Test File
```bash
# API tests
pytest tests/test_api_comprehensive.py -v

# Service tests
pytest tests/test_services.py -v

# Original API tests
pytest tests/test_api.py -v
```

### Run Specific Test Class
```bash
# Budget API tests
pytest tests/test_api_comprehensive.py::TestBudgetsAPI -v

# Budget service tests
pytest tests/test_services.py::TestBudgetService -v
```

### Run Specific Test
```bash
# Test net expense calculation
pytest tests/test_api_comprehensive.py::TestBudgetsAPI::test_net_expense_calculation -v

# Test refund detection
pytest tests/test_services.py::TestBaseParer::test_refund_pattern_detection -v
```

### Run with Coverage
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run in Watch Mode (requires pytest-watch)
```bash
ptw tests/
```

---

## Key Test Scenarios

### 1. Net Expense Calculations
Tests verify that **expenses - refunds = net spending** throughout the system:

```python
# Budget shows net spending
def test_net_expense_calculation(self, client):
    # Create expense: $150
    # Create refund: $50
    # Budget should show: $100 (net)
```

### 2. Refund Detection on Credit Cards
Tests verify that income on liabilities (credit cards) is auto-converted to refunds:

```python
# Import service converts income → refund
def test_import_converts_income_on_liability_to_refund(self, import_service):
    # Parsed as "income" on credit card
    # Should be converted to "refund"
```

### 3. Auto-Categorization
Tests verify that rules automatically categorize matching transactions:

```python
# Rule matches description
def test_rule_auto_categorizes(self, client):
    # Create rule: pattern="gas_station" → Fuel
    # Create transaction: "GAS_STATION FUEL"
    # Should auto-categorize as Fuel
```

### 4. Transfer Detection
Tests verify that transfers don't count as expenses:

```python
# Transfers don't affect budget
def test_transfer_is_not_an_expense(self, client):
    # Create transfer: Checking → Credit Card
    # Budget total_spent should not change
```

---

## Test Data

Tests use a seeded database with:
- **Accounts**: Chase Checking, BOFA CC, Apple Card, Chase CC, etc.
- **Categories**: Food & Outing, Transport, Shopping, Apps, etc.
- **Month**: `2026-11` (November 2026) for most tests

---

## Writing New Tests

### API Test Example
```python
class TestMyAPI:
    """Test /my-endpoint API."""

    def test_my_feature(self, client):
        """Test description."""
        response = client.get("/my-endpoint")
        assert response.status_code == 200
        data = response.json()
        assert "field" in data
```

### Service Test Example
```python
class TestMyService:
    """Test MyService business logic."""

    @pytest.fixture
    def my_service(self):
        mock_db = Mock()
        return MyService(mock_db)

    def test_my_method(self, my_service):
        """Test description."""
        # Setup mocks
        my_service.repo = Mock()
        my_service.repo.get.return_value = SomeModel()

        # Test
        result = my_service.my_method()

        # Verify
        assert result is not None
```

---

## Continuous Integration

Tests should be run in CI/CD pipeline:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    source venv/bin/activate
    pytest tests/ -v --cov=app
```

---

## Test Maintenance

- **Update tests** when adding new features
- **Keep tests fast** - use mocks for external dependencies
- **Test edge cases** - invalid inputs, error conditions
- **Document complex tests** - explain what's being tested and why
- **Use descriptive names** - test names should explain what they test

---

## Troubleshooting

### ImportError: No module named 'app'
Make sure you're in the project root directory:
```bash
cd /path/to/moneymanager
pytest tests/
```

### Database errors
Tests use a temporary test database. Check `conftest.py` configuration.

### Slow tests
Use `-v` flag to see which tests are slow:
```bash
pytest tests/ -v --durations=10
```

### Mock issues
Ensure you're mocking the right dependencies. Check the service's `__init__` method.

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Python Mock](https://docs.python.org/3/library/unittest.mock.html)
