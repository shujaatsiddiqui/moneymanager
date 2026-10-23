"""Budget repository."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import USER_ID, Budget
from .base import BaseRepository


class BudgetRepository(BaseRepository[Budget]):
    """Repository for Budget entities."""

    def __init__(self, db: Session):
        super().__init__(db, Budget)

    def get_by_month(self, month: str) -> list[Budget]:
        """Get all budgets for a given month."""
        return list(self.db.scalars(
            select(Budget).where(
                Budget.user_id == self.user_id,
                Budget.month == month
            )
        ).all())

    def get_by_category_and_month(self, category_id: int, month: str) -> Optional[Budget]:
        """Get budget for a specific category and month."""
        return self.db.scalars(
            select(Budget).where(
                Budget.user_id == self.user_id,
                Budget.category_id == category_id,
                Budget.month == month
            )
        ).first()

    def get_budgeted_category_ids(self, month: str, children_map: dict[int, list[int]]) -> set[int]:
        """Get all category IDs that are covered by a budget for the given month.

        Args:
            month: The month in YYYY-MM format
            children_map: Map of parent_id to list of child category IDs

        Returns:
            Set of category IDs that are budgeted (including children of budgeted parents)
        """
        budgets = self.get_by_month(month)
        covered = set()
        for b in budgets:
            covered.add(b.category_id)
            covered.update(children_map.get(b.category_id, []))
        return covered

    def delete_by_category(self, category_id: int) -> int:
        """Delete all budgets for a category."""
        count = 0
        for b in self.db.scalars(
            select(Budget).where(Budget.category_id == category_id)
        ):
            self.db.delete(b)
            count += 1
        return count

    def copy_budgets(self, from_month: str, to_month: str) -> int:
        """Copy budgets from one month to another (skips existing)."""
        source_budgets = self.get_by_month(from_month)
        existing_category_ids = {b.category_id for b in self.get_by_month(to_month)}

        count = 0
        for b in source_budgets:
            if b.category_id not in existing_category_ids:
                new_budget = Budget(
                    user_id=self.user_id,
                    category_id=b.category_id,
                    month=to_month,
                    limit_cents=b.limit_cents
                )
                self.db.add(new_budget)
                count += 1

        return count
