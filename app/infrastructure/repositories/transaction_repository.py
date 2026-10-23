"""Transaction repository."""

from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import USER_ID, Transaction
from .base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """Repository for Transaction entities."""

    def __init__(self, db: Session):
        super().__init__(db, Transaction)

    def get_by_filters(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        account_id: Optional[int] = None,
        category_ids: Optional[list[int]] = None,
        kind: Optional[str] = None,
        kinds: Optional[list[str]] = None,
        uncategorized: bool = False,
        exclude_category_ids: Optional[list[int]] = None,
        limit: int = 500,
    ) -> list[Transaction]:
        """Get transactions with various filters."""
        q = select(Transaction).where(Transaction.user_id == self.user_id)

        if start_date:
            q = q.where(Transaction.date >= start_date)
        if end_date:
            q = q.where(Transaction.date < end_date)
        if account_id:
            q = q.where(Transaction.account_id == account_id)
        if category_ids:
            q = q.where(Transaction.category_id.in_(category_ids))
        if kind:
            q = q.where(Transaction.kind == kind)
        if kinds:
            q = q.where(Transaction.kind.in_(kinds))
        if uncategorized:
            q = q.where(Transaction.category_id.is_(None))
        if exclude_category_ids:
            q = q.where(Transaction.category_id.notin_(exclude_category_ids))

        q = q.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(limit)
        return list(self.db.scalars(q).all())

    def get_uncategorized(self, kinds: Optional[list[str]] = None) -> list[Transaction]:
        """Get uncategorized transactions."""
        kinds = kinds or ["expense", "income"]
        return list(self.db.scalars(
            select(Transaction).where(
                Transaction.user_id == self.user_id,
                Transaction.kind.in_(kinds),
                Transaction.category_id.is_(None)
            )
        ).all())

    def get_by_kind(self, kinds: list[str]) -> list[Transaction]:
        """Get transactions by kind(s)."""
        return list(self.db.scalars(
            select(Transaction).where(
                Transaction.user_id == self.user_id,
                Transaction.kind.in_(kinds)
            )
        ).all())

    def get_existing_hashes(self) -> set[str]:
        """Get all existing import hashes."""
        return set(
            h for (h,) in self.db.execute(
                select(Transaction.import_hash)
                .where(
                    Transaction.user_id == self.user_id,
                    Transaction.import_hash.isnot(None)
                )
            ).all()
        )

    def find_existing_transfer(
        self,
        tx_date: date,
        amount_cents: int,
        source_account_id: int,
        dest_account_id: int
    ) -> Optional[Transaction]:
        """Find an existing transfer_out transaction."""
        return self.db.scalars(
            select(Transaction).where(
                Transaction.user_id == self.user_id,
                Transaction.kind == "transfer_out",
                Transaction.date == tx_date,
                Transaction.amount_cents == amount_cents,
                Transaction.account_id == source_account_id,
                Transaction.to_account_id == dest_account_id
            )
        ).first()

    def count_by_category(self, category_id: int) -> int:
        """Count transactions for a category."""
        return self.db.scalar(
            select(func.count(Transaction.id))
            .where(Transaction.category_id == category_id)
        ) or 0

    def count_by_categories(self, category_ids: list[int]) -> int:
        """Count transactions for multiple categories."""
        return self.db.scalar(
            select(func.count(Transaction.id))
            .where(Transaction.category_id.in_(category_ids))
        ) or 0

    def get_spending_by_category(
        self,
        start_date: date,
        end_date: date
    ) -> dict[Optional[int], int]:
        """Get total spending (in cents) grouped by category for a date range."""
        rows = self.db.execute(
            select(Transaction.category_id, func.sum(Transaction.amount_cents))
            .where(
                Transaction.user_id == self.user_id,
                Transaction.kind == "expense",
                Transaction.date >= start_date,
                Transaction.date < end_date
            )
            .group_by(Transaction.category_id)
        ).all()
        return dict(rows)

    def get_total_by_kind(self, kind: str, start_date: date, end_date: date) -> int:
        """Get total amount (in cents) for a kind in a date range."""
        return self.db.scalar(
            select(func.coalesce(func.sum(Transaction.amount_cents), 0))
            .where(
                Transaction.user_id == self.user_id,
                Transaction.kind == kind,
                Transaction.date >= start_date,
                Transaction.date < end_date
            )
        ) or 0

    def move_to_category(self, from_category_ids: list[int], to_category_id: int) -> int:
        """Move all transactions from one set of categories to another."""
        count = 0
        for tx in self.db.scalars(
            select(Transaction).where(Transaction.category_id.in_(from_category_ids))
        ):
            tx.category_id = to_category_id
            count += 1
        return count
