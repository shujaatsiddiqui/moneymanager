"""Unit tests for domain services (business logic).

Tests cover:
- BudgetService (net expense calculations)
- TransactionService
- ImportService (refund detection)
- ReportService (P&L with net expenses)
- AccountService
- RuleService
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch

from app.domain.services import (
    BudgetService,
    TransactionService,
    ImportService,
    ReportService,
    AccountService,
   RuleService
)
from app.domain.exceptions import NotFoundError, ValidationError
from app.models import USER_ID, Account, Category, Budget, Transaction, Rule
from app.infrastructure.parsers.base import ParsedTransaction


# ============================================================================
# BUDGET SERVICE TESTS
# ============================================================================

class TestBudgetService:
    """Test BudgetService business logic."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def budget_service(self, mock_db):
        """Create BudgetService with mocked dependencies."""
        return BudgetService(mock_db)

    def test_set_budget_creates_new(self, budget_service, mock_db):
        """Test set_budget creates new budget if doesn't exist."""
        # Mock category repo
        budget_service.category_repo = Mock()
        budget_service.category_repo.get.return_value = Category(
            id=1, user_id=USER_ID, name="Food", kind="expense"
        )

        # Mock budget repo
        budget_service.repo = Mock()
        budget_service.repo.get_by_category_and_month.return_value = None
        budget_service.repo.add = Mock()
        budget_service.repo.commit = Mock()

        # Test
        result = budget_service.set_budget(category_id=1, month="2026-11", limit=500.00)

        # Verify
        budget_service.repo.add.assert_called_once()
        budget_service.repo.commit.assert_called_once()

    def test_set_budget_updates_existing(self, budget_service):
        """Test set_budget updates existing budget."""
        # Mock category repo
        budget_service.category_repo = Mock()
        budget_service.category_repo.get.return_value = Category(
            id=1, user_id=USER_ID, name="Food", kind="expense"
        )

        # Mock budget repo with existing budget
        existing_budget = Budget(
            id=10,
            user_id=USER_ID,
            category_id=1,
            month="2026-11",
            limit_cents=50000  # $500
        )
        budget_service.repo = Mock()
        budget_service.repo.get_by_category_and_month.return_value = existing_budget
        budget_service.repo.commit = Mock()

        # Test
        result = budget_service.set_budget(category_id=1, month="2026-11", limit=600.00)

        # Verify limit was updated
        assert existing_budget.limit_cents == 60000  # $600
        budget_service.repo.commit.assert_called_once()

    def test_get_status_calculates_net_spending(self, budget_service):
        """Test get_status calculates net spending (expenses - refunds)."""
        # Mock category repo
        food_cat = Category(id=1, user_id=USER_ID, name="Food", kind="expense", exclude_from_budget=False)
        budget_service.category_repo = Mock()
        budget_service.category_repo.get_category_ids_map.return_value = {1: food_cat}
        budget_service.category_repo.get_children_map.return_value = {}

        # Mock transaction repo
        budget_service.transaction_repo = Mock()
        budget_service.transaction_repo.get_total_by_kind.side_effect = lambda kind, start, end: {
            "income": 100000,  # $1000
            "expense": 50000,  # $500 gross
            "refund": 10000,   # $100 refund
        }.get(kind, 0)

        # Mock spending by category (should be net: 400 = 500 - 100)
        budget_service.transaction_repo.get_spending_by_category.return_value = {
            1: 40000  # $400 net (expenses - refunds)
        }

        # Mock budget repo
        budget_service.repo = Mock()
        budget_service.repo.get_by_month.return_value = [
            Budget(id=1, user_id=USER_ID, category_id=1, month="2026-11", limit_cents=50000)
        ]

        # Test
        result = budget_service.get_status("2026-11")

        # Verify net spending is used
        assert result["rows"][0]["spent"] == 400.00  # Net spending
        assert result["total_expenses"] == 400.00  # Net total (500 - 100)

    def test_delete_budget(self, budget_service):
        """Test delete_budget removes budget."""
        budget_service.repo = Mock()
        existing_budget = Budget(id=1, user_id=USER_ID, category_id=1, month="2026-11", limit_cents=50000)
        budget_service.repo.get_by_category_and_month.return_value = existing_budget
        budget_service.repo.delete = Mock()
        budget_service.repo.commit = Mock()

        budget_service.delete_budget(category_id=1, month="2026-11")

        budget_service.repo.delete.assert_called_once_with(existing_budget)
        budget_service.repo.commit.assert_called_once()


# ============================================================================
# IMPORT SERVICE TESTS
# ============================================================================

class TestImportService:
    """Test ImportService with refund detection."""

    @pytest.fixture
    def import_service(self):
        """Create ImportService with mocked dependencies."""
        mock_db = Mock()
        service = ImportService(mock_db)
        return service

    def test_import_converts_income_on_liability_to_refund(self, import_service):
        """Test that income on credit cards is converted to refunds."""
        # Mock account (credit card = liability)
        credit_card = Account(
            id=1,
            user_id=USER_ID,
            name="Credit Card",
            group_name="Card",
            is_liability=True,
            opening_cents=0,
            include_in_totals=True,
            is_business=False
        )

        # Mock repos
        import_service.account_repo = Mock()
        import_service.account_repo.get.return_value = credit_card

        import_service.batch_repo = Mock()
        mock_batch = Mock(id=1)
        import_service.batch_repo.create.return_value = mock_batch

        import_service.transaction_repo = Mock()
        import_service.transaction_repo.add = Mock()
        import_service.transaction_repo.commit = Mock()
        import_service.transaction_repo.find_by_hash.return_value = None

        import_service.category_repo = Mock()
        import_service.category_repo.list_expense_categories.return_value = []

        import_service.rule_repo = Mock()
        import_service.rule_repo.match.return_value = None

        # Parsed transaction (income/inflow on credit card)
        parsed_tx = ParsedTransaction(
            date=date(2026, 11, 15),
            description="REFUND FROM STORE",
            amount=50.00,
            kind="income",  # Parser detected as income
            is_inflow=True,
            import_hash="hash123"
        )

        # Test import
        result = import_service.import_transactions(
            transactions=[parsed_tx],
            target_account_id=1,
            use_ai=False,
            filename="test.csv"
        )

        # Verify transaction was converted to refund
        import_service.transaction_repo.add.assert_called_once()
        added_tx = import_service.transaction_repo.add.call_args[0][0]
        assert added_tx.kind == "refund"  # Converted from income to refund

    def test_import_skips_duplicates(self, import_service):
        """Test that duplicate transactions are skipped."""
        # Mock account
        account = Account(
            id=1, user_id=USER_ID, name="Checking", group_name="Accounts",
            is_liability=False, opening_cents=0, include_in_totals=True, is_business=False
        )

        import_service.account_repo = Mock()
        import_service.account_repo.get.return_value = account

        import_service.batch_repo = Mock()
        import_service.batch_repo.create.return_value = Mock(id=1)

        # Mock existing transaction with same hash
        import_service.transaction_repo = Mock()
        import_service.transaction_repo.find_by_hash.return_value = Transaction(
            id=99, user_id=USER_ID, date=date(2026, 11, 15), kind="expense",
            amount_cents=5000, account_id=1, description="Existing"
        )
        import_service.transaction_repo.commit = Mock()

        parsed_tx = ParsedTransaction(
            date=date(2026, 11, 15),
            description="DUPLICATE",
            amount=50.00,
            kind="expense",
            is_inflow=False,
            import_hash="duplicate_hash"
        )

        result = import_service.import_transactions(
            transactions=[parsed_tx],
            target_account_id=1,
            use_ai=False,
            filename="test.csv"
        )

        # Verify skipped
        assert result["imported"] == 0
        assert result["skipped"] > 0


# ============================================================================
# TRANSACTION SERVICE TESTS
# ============================================================================

class TestTransactionService:
    """Test TransactionService business logic."""

    @pytest.fixture
    def transaction_service(self):
        """Create TransactionService with mocked dependencies."""
        mock_db = Mock()
        return TransactionService(mock_db)

    def test_create_transaction(self, transaction_service):
        """Test create transaction."""
        transaction_service.repo = Mock()
        transaction_service.repo.add = Mock()
        transaction_service.repo.commit = Mock()
        transaction_service.repo.get_by_id = Mock()

        transaction_service.account_repo = Mock()
        transaction_service.account_repo.get.return_value = Account(
            id=1, user_id=USER_ID, name="Checking", group_name="Accounts",
            is_liability=False, opening_cents=0, include_in_totals=True, is_business=False
        )

        transaction_service.category_repo = Mock()
        transaction_service.category_repo.get.return_value = Category(
            id=1, user_id=USER_ID, name="Food", kind="expense"
        )

        transaction_service.rule_repo = Mock()
        transaction_service.rule_repo.match.return_value = None

        result = transaction_service.create(
            date=date(2026, 11, 15),
            kind="expense",
            amount=50.00,
            account_id=1,
            category_id=1,
            description="Test"
        )

        transaction_service.repo.add.assert_called_once()
        transaction_service.repo.commit.assert_called_once()

    def test_create_transfer_validates_to_account(self, transaction_service):
        """Test that creating transfer requires to_account_id."""
        with pytest.raises(ValidationError):
            transaction_service.create(
                date=date(2026, 11, 15),
                kind="transfer",
                amount=100.00,
                account_id=1,
                to_account_id=None,  # Missing!
                description="Invalid transfer"
            )

    def test_delete_transaction(self, transaction_service):
        """Test delete transaction."""
        mock_tx = Transaction(
            id=1, user_id=USER_ID, date=date(2026, 11, 15), kind="expense",
            amount_cents=5000, account_id=1, description="To delete"
        )

        transaction_service.repo = Mock()
        transaction_service.repo.get_by_id.return_value = mock_tx
        transaction_service.repo.delete = Mock()
        transaction_service.repo.commit = Mock()

        transaction_service.delete(1)

        transaction_service.repo.delete.assert_called_once_with(mock_tx)
        transaction_service.repo.commit.assert_called_once()


# ============================================================================
# REPORT SERVICE TESTS
# ============================================================================

class TestReportService:
    """Test ReportService with net expense calculations."""

    @pytest.fixture
    def report_service(self):
        """Create ReportService with mocked dependencies."""
        mock_db = Mock()
        return ReportService(mock_db)

    def test_profit_loss_calculates_net_expenses(self, report_service):
        """Test P&L report calculates net expenses (expenses - refunds)."""
        # Mock category repo
        food_cat = Category(id=1, user_id=USER_ID, name="Food", kind="expense", exclude_from_budget=False, parent_id=None)
        report_service.category_repo = Mock()
        report_service.category_repo.get_category_ids_map.return_value = {1: food_cat}
        report_service.category_repo.get_children_map.return_value = {}

        # Mock transaction totals
        # (kind, category_id) -> amount_cents
        totals = {
            ("expense", 1): 50000,  # $500 expenses
            ("refund", 1): 10000,   # $100 refunds
            ("income", 1): 20000,   # $200 income
        }
        report_service.transaction_repo = Mock()
        report_service.transaction_repo.get_totals_by_kind_and_category.return_value = totals

        # Test
        result = report_service.get_profit_loss(
            start_date=date(2026, 11, 1),
            end_date=date(2026, 12, 1)
        )

        # Verify net calculation
        # Operating expenses should be: 500 - 100 = 400
        assert result["expenses"]["operating"]["total"] == 400.00

    def test_profit_loss_excludes_non_operating(self, report_service):
        """Test P&L report separates operating and non-operating expenses."""
        # Mock categories
        food_cat = Category(id=1, user_id=USER_ID, name="Food", kind="expense", exclude_from_budget=False, parent_id=None)
        tax_cat = Category(id=2, user_id=USER_ID, name="Taxes", kind="expense", exclude_from_budget=True, parent_id=None)

        report_service.category_repo = Mock()
        report_service.category_repo.get_category_ids_map.return_value = {
            1: food_cat,
            2: tax_cat
        }
        report_service.category_repo.get_children_map.return_value = {}

        # Mock totals
        totals = {
            ("expense", 1): 30000,  # $300 food (operating)
            ("expense", 2): 50000,  # $500 taxes (non-operating)
        }
        report_service.transaction_repo = Mock()
        report_service.transaction_repo.get_totals_by_kind_and_category.return_value = totals

        # Test
        result = report_service.get_profit_loss(
            start_date=date(2026, 11, 1),
            end_date=date(2026, 12, 1)
        )

        # Verify separation
        assert result["expenses"]["operating"]["total"] == 300.00
        assert result["expenses"]["non_operating"]["total"] == 500.00


# ============================================================================
# RULE SERVICE TESTS
# ============================================================================

class TestRuleService:
    """Test RuleService business logic."""

    @pytest.fixture
    def rule_service(self):
        """Create RuleService with mocked dependencies."""
        mock_db = Mock()
        return RuleService(mock_db)

    def test_create_rule(self, rule_service):
        """Test create categorization rule."""
        rule_service.category_repo = Mock()
        rule_service.category_repo.get.return_value = Category(
            id=1, user_id=USER_ID, name="Gas", kind="expense"
        )

        rule_service.repo = Mock()
        rule_service.repo.add = Mock()
        rule_service.repo.commit = Mock()

        result = rule_service.create(
            pattern="shell",
            category_id=1,
            min_amount=10.00,
            max_amount=100.00
        )

        rule_service.repo.add.assert_called_once()
        rule_service.repo.commit.assert_called_once()

    def test_suggest_pattern(self, rule_service):
        """Test pattern suggestion from description."""
        result = rule_service.suggest_pattern("SHELL OIL #1234 DALLAS TX")

        # Should extract merchant name
        assert "shell" in result["pattern"].lower()

    def test_apply_rules(self, rule_service):
        """Test applying rules to uncategorized transactions."""
        # Mock rule
        rule = Rule(
            id=1,
            user_id=USER_ID,
            pattern="coffee",
            category_id=1,
            min_cents=None,
            max_cents=None
        )

        rule_service.repo = Mock()
        rule_service.repo.get_all.return_value = [rule]

        # Mock uncategorized transaction
        uncategorized_tx = Transaction(
            id=10,
            user_id=USER_ID,
            date=date(2026, 11, 15),
            kind="expense",
            amount_cents=500,
            account_id=1,
            category_id=None,  # Uncategorized
            description="COFFEE SHOP"
        )

        rule_service.transaction_repo = Mock()
        rule_service.transaction_repo.get_uncategorized.return_value = [uncategorized_tx]
        rule_service.transaction_repo.commit = Mock()

        # Test
        result = rule_service.apply_rules()

        # Verify categorization
        assert uncategorized_tx.category_id == 1
        assert result["categorized"] == 1


# ============================================================================
# PARSER TESTS
# ============================================================================

class TestBaseParer:
    """Test base parser refund detection."""

    def test_refund_pattern_detection(self):
        """Test that refund patterns are detected."""
        from app.infrastructure.parsers.base import BaseParser

        # Create concrete implementation for testing
        class TestParser(BaseParser):
            def parse(self, content: str):
                return []

        parser = TestParser()

        # Test refund patterns
        assert parser.is_likely_refund("RETURN CREDIT") is True
        assert parser.is_likely_refund("REFUND FOR PURCHASE") is True
        assert parser.is_likely_refund("PURCHASE REVERSAL") is True
        assert parser.is_likely_refund("MERCHANT CREDIT ADJUSTMENT") is True

        # Test non-refund
        assert parser.is_likely_refund("COFFEE SHOP") is False

    def test_determine_kind_with_refund(self):
        """Test _determine_kind detects refunds."""
        from app.infrastructure.parsers.base import BaseParser

        # Create concrete implementation for testing
        class TestParser(BaseParser):
            def parse(self, content: str):
                return []

        parser = TestParser()

        # Positive amount with refund keyword
        kind, is_inflow = parser._determine_kind(50.00, "REFUND FOR PURCHASE")
        assert kind == "refund"
        assert is_inflow is True

        # Negative amount (expense)
        kind, is_inflow = parser._determine_kind(-50.00, "COFFEE SHOP")
        assert kind == "expense"
        assert is_inflow is False

        # Positive amount without refund keyword (income)
        kind, is_inflow = parser._determine_kind(50.00, "SALARY PAYMENT")
        assert kind == "income"
        assert is_inflow is True


# ============================================================================
# REPOSITORY TESTS
# ============================================================================

class TestTransactionRepository:
    """Test TransactionRepository net spending calculations."""

    def test_get_spending_by_category_returns_net(self):
        """Test get_spending_by_category returns net spending (expenses - refunds)."""
        from app.infrastructure.repositories.transaction_repository import TransactionRepository

        # This would require actual database or more complex mocking
        # Demonstrating the test structure
        pass  # Actual implementation would need integration test with real DB


# ============================================================================
# UTILITY TESTS
# ============================================================================

class TestDomainUtils:
    """Test domain utility functions."""

    def test_to_cents(self):
        """Test converting dollars to cents."""
        from app.domain.utils import to_cents

        assert to_cents(50.00) == 5000
        assert to_cents(0.50) == 50
        assert to_cents(123.45) == 12345

    def test_from_cents(self):
        """Test converting cents to dollars."""
        from app.domain.utils import from_cents

        assert from_cents(5000) == 50.00
        assert from_cents(50) == 0.50
        assert from_cents(12345) == 123.45

    def test_month_range(self):
        """Test generating date range for month."""
        from app.domain.utils import month_range

        start, end = month_range("2026-11")

        assert start == date(2026, 11, 1)
        assert end == date(2026, 12, 1)
