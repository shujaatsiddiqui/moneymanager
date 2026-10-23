"""Budget service - business logic for budgets."""

from sqlalchemy.orm import Session

from ...models import USER_ID, Budget
from ...infrastructure.repositories import (
    BudgetRepository,
    CategoryRepository,
    TransactionRepository,
)
from ..exceptions import NotFoundError
from ..utils import from_cents, month_range, to_cents


class BudgetService:
    """Service for budget-related business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = BudgetRepository(db)
        self.category_repo = CategoryRepository(db)
        self.transaction_repo = TransactionRepository(db)

    def get_status(self, month: str) -> dict:
        """Get budget status for a month."""
        start, end = month_range(month)

        # Get all categories
        cats = self.category_repo.get_category_ids_map()
        children_map = {
            parent_id: [c.id for c in children]
            for parent_id, children in self.category_repo.get_children_map().items()
        }

        # Get totals
        total_income_cents = self.transaction_repo.get_total_by_kind("income", start, end)
        total_expenses_cents = self.transaction_repo.get_total_by_kind("expense", start, end)

        # Get spending by category
        spent_by_cat = self.transaction_repo.get_spending_by_category(start, end)

        def spent(cid: int) -> int:
            """Get total spent for a category including children."""
            return sum(spent_by_cat.get(i, 0) for i in [cid] + children_map.get(cid, []))

        def excluded(cid: int | None) -> bool:
            """Check if category is excluded from budget."""
            c = cats.get(cid)
            if c is None:
                return False
            return c.exclude_from_budget or (
                c.parent_id is not None and cats[c.parent_id].exclude_from_budget
            )

        # Build budget rows
        budgets = self.repo.get_by_month(month)
        rows = []
        covered = set()

        for b in budgets:
            c = cats[b.category_id]
            s = spent(b.category_id)
            covered.update([b.category_id] + children_map.get(b.category_id, []))
            rows.append({
                "category_id": c.id,
                "category": c.name,
                "emoji": c.emoji,
                "limit": from_cents(b.limit_cents),
                "spent": from_cents(s),
                "left": from_cents(b.limit_cents - s),
                "pct": round(s / b.limit_cents * 100, 1) if b.limit_cents else None,
            })

        # Sort by amount left (most overspent first)
        rows.sort(key=lambda r: (r["left"] is None, r["left"]))

        # Calculate summary metrics
        uncategorized = spent_by_cat.get(None, 0)
        unbudgeted = sum(
            v for cid, v in spent_by_cat.items()
            if cid is not None and cid not in covered and not excluded(cid)
        )
        excluded_total = sum(
            v for cid, v in spent_by_cat.items()
            if cid is not None and excluded(cid)
        )
        total_limit = sum(b.limit_cents for b in budgets)
        total_spent = sum(to_cents(r["spent"]) for r in rows)
        saved_cents = total_income_cents - total_expenses_cents
        savings_rate = round((saved_cents / total_income_cents) * 100, 1) if total_income_cents > 0 else 0

        return {
            "month": month,
            "rows": rows,
            "total_limit": from_cents(total_limit),
            "total_spent": from_cents(total_spent),
            "total_left": from_cents(total_limit - total_spent),
            "unbudgeted_spent": from_cents(unbudgeted),
            "uncategorized_spent": from_cents(uncategorized),
            "excluded_spent": from_cents(excluded_total),
            "total_income": from_cents(total_income_cents),
            "total_expenses": from_cents(total_expenses_cents),
            "saved": from_cents(saved_cents),
            "savings_rate": savings_rate,
        }

    def set_budget(self, category_id: int, month: str, limit: float) -> int:
        """Set or update a budget."""
        # Validate category exists
        if self.category_repo.get(category_id) is None:
            raise NotFoundError("Category", category_id)

        cents = to_cents(limit)
        budget = self.repo.get_by_category_and_month(category_id, month)

        if budget is None:
            budget = Budget(
                user_id=USER_ID,
                category_id=category_id,
                month=month,
                limit_cents=cents,
            )
            self.repo.add(budget)
        else:
            budget.limit_cents = cents

        self.repo.commit()
        return budget.id

    def delete_budget(self, category_id: int, month: str) -> None:
        """Delete a budget."""
        budget = self.repo.get_by_category_and_month(category_id, month)
        if budget:
            self.repo.delete(budget)
            self.repo.commit()

    def copy_budgets(self, from_month: str, to_month: str) -> int:
        """Copy budgets from one month to another."""
        count = self.repo.copy_budgets(from_month, to_month)
        self.repo.commit()
        return count

    def get_budgeted_category_ids(self, month: str) -> set[int]:
        """Get all category IDs that are covered by a budget for the given month."""
        children_map = {
            parent_id: [c.id for c in children]
            for parent_id, children in self.category_repo.get_children_map().items()
        }
        return self.repo.get_budgeted_category_ids(month, children_map)
