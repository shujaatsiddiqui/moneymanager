"""Report service - business logic for generating financial reports."""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from ...infrastructure.repositories import (
    CategoryRepository,
    TransactionRepository,
)
from ..utils import from_cents


class ReportService:
    """Service for generating financial reports."""

    def __init__(self, db: Session):
        self.db = db
        self.category_repo = CategoryRepository(db)
        self.transaction_repo = TransactionRepository(db)

    def get_profit_loss(
        self,
        start_date: date,
        end_date: date,
        is_business: Optional[bool] = None
    ) -> dict:
        """Generate a Profit & Loss report for a date range.

        Args:
            start_date: Start of the reporting period (inclusive)
            end_date: End of the reporting period (exclusive)
            is_business: Filter by business/personal transactions (None = all)

        Returns:
            P&L report with revenue, expenses, and net income
        """
        # Get all categories
        cats = self.category_repo.get_category_ids_map()
        children_map = {
            parent_id: [c.id for c in children]
            for parent_id, children in self.category_repo.get_children_map().items()
        }

        # Get transaction totals grouped by kind and category
        totals = self.transaction_repo.get_totals_by_kind_and_category(
            start_date, end_date, is_business
        )

        # Helper to check if category is excluded from budget (non-operating)
        def is_excluded(cid: Optional[int]) -> bool:
            if cid is None:
                return False
            c = cats.get(cid)
            if c is None:
                return False
            return c.exclude_from_budget or (
                c.parent_id is not None and cats[c.parent_id].exclude_from_budget
            )

        # Helper to get parent category
        def get_parent_id(cid: Optional[int]) -> Optional[int]:
            if cid is None:
                return None
            c = cats.get(cid)
            return c.parent_id if c else None

        # Build category breakdown for income
        income_by_category: dict[int, int] = {}
        for (kind, cat_id), amount in totals.items():
            if kind == "income" and cat_id is not None:
                parent_id = get_parent_id(cat_id) or cat_id
                income_by_category[parent_id] = income_by_category.get(parent_id, 0) + amount

        # Build category breakdown for expenses (excluding refunds)
        expenses_by_category: dict[int, int] = {}
        non_operating_by_category: dict[int, int] = {}

        for (kind, cat_id), amount in totals.items():
            if kind == "expense":
                parent_id = get_parent_id(cat_id) or cat_id if cat_id else None
                if parent_id is not None:
                    if is_excluded(cat_id):
                        non_operating_by_category[parent_id] = (
                            non_operating_by_category.get(parent_id, 0) + amount
                        )
                    else:
                        expenses_by_category[parent_id] = (
                            expenses_by_category.get(parent_id, 0) + amount
                        )

        # Refunds reduce expenses (or can be shown separately)
        refunds_by_category: dict[int, int] = {}
        for (kind, cat_id), amount in totals.items():
            if kind == "refund" and cat_id is not None:
                parent_id = get_parent_id(cat_id) or cat_id
                refunds_by_category[parent_id] = refunds_by_category.get(parent_id, 0) + amount

        # Calculate totals
        total_income = sum(
            amount for (kind, _), amount in totals.items() if kind == "income"
        )
        total_expenses = sum(
            amount for (kind, cat_id), amount in totals.items()
            if kind == "expense" and not is_excluded(cat_id)
        )
        total_refunds = sum(
            amount for (kind, _), amount in totals.items() if kind == "refund"
        )
        total_non_operating = sum(
            amount for (kind, cat_id), amount in totals.items()
            if kind == "expense" and is_excluded(cat_id)
        )

        # Uncategorized amounts
        uncategorized_income = totals.get(("income", None), 0)
        uncategorized_expenses = totals.get(("expense", None), 0)

        # Format category rows
        def format_category_rows(by_category: dict[int, int]) -> list[dict]:
            rows = []
            for cat_id, amount in sorted(
                by_category.items(),
                key=lambda x: -x[1]  # Sort by amount descending
            ):
                c = cats.get(cat_id)
                if c:
                    rows.append({
                        "category_id": cat_id,
                        "category": c.name,
                        "emoji": c.emoji,
                        "amount": from_cents(amount),
                    })
            return rows

        # Net calculations
        # Gross profit = Income - Cost of Revenue (we don't track COGS separately, so it's just income)
        # Operating income = Gross profit - Operating expenses
        # Net income = Operating income - Non-operating expenses + Refunds
        gross_profit = total_income
        operating_income = gross_profit - total_expenses + total_refunds
        net_income = operating_income - total_non_operating

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "filter": {
                "is_business": is_business,
            },
            "revenue": {
                "total": from_cents(total_income),
                "categories": format_category_rows(income_by_category),
                "uncategorized": from_cents(uncategorized_income),
            },
            "expenses": {
                "operating": {
                    "total": from_cents(total_expenses),
                    "categories": format_category_rows(expenses_by_category),
                    "uncategorized": from_cents(uncategorized_expenses),
                },
                "non_operating": {
                    "total": from_cents(total_non_operating),
                    "categories": format_category_rows(non_operating_by_category),
                },
            },
            "refunds": {
                "total": from_cents(total_refunds),
                "categories": format_category_rows(refunds_by_category),
            },
            "summary": {
                "gross_profit": from_cents(gross_profit),
                "operating_income": from_cents(operating_income),
                "net_income": from_cents(net_income),
            },
        }

    def get_ytd_profit_loss(
        self,
        year: int,
        is_business: Optional[bool] = None
    ) -> dict:
        """Generate a Year-to-Date P&L report.

        Args:
            year: The year for the report
            is_business: Filter by business/personal transactions (None = all)

        Returns:
            YTD P&L report
        """
        start_date = date(year, 1, 1)
        # End date is today if current year, else end of year
        today = date.today()
        if year == today.year:
            end_date = today
        else:
            end_date = date(year + 1, 1, 1)

        return self.get_profit_loss(start_date, end_date, is_business)

    def get_monthly_profit_loss(
        self,
        month: str,
        is_business: Optional[bool] = None
    ) -> dict:
        """Generate a monthly P&L report.

        Args:
            month: Month in YYYY-MM format
            is_business: Filter by business/personal transactions (None = all)

        Returns:
            Monthly P&L report
        """
        from ..utils import month_range

        start_date, end_date = month_range(month)
        return self.get_profit_loss(start_date, end_date, is_business)
