"""Account repository."""

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ...models import USER_ID, Account, Transaction
from .base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    """Repository for Account entities."""

    def __init__(self, db: Session):
        super().__init__(db, Account)

    def get_all_ordered(self) -> list[Account]:
        """Get all accounts ordered by sort field."""
        return list(self.db.scalars(
            select(Account)
            .where(Account.user_id == self.user_id)
            .order_by(Account.sort)
        ).all())

    def get_by_name(self, name: str) -> Optional[Account]:
        """Get account by name."""
        return self.db.scalars(
            select(Account).where(
                Account.user_id == self.user_id,
                Account.name == name
            )
        ).first()

    def get_by_suffix(self, suffix: str) -> Optional[Account]:
        """Get account by account suffix (last 4 digits)."""
        if not suffix:
            return None
        return self.db.scalars(
            select(Account).where(
                Account.user_id == self.user_id,
                Account.account_suffix == suffix
            )
        ).first()

    def get_by_suffixes(self, suffixes: set[str]) -> list[Account]:
        """Get accounts matching any of the given suffixes."""
        if not suffixes:
            return []
        return list(self.db.scalars(
            select(Account).where(
                Account.user_id == self.user_id,
                Account.account_suffix.in_(suffixes)
            )
        ).all())

    def get_all_suffixes(self) -> set[str]:
        """Get all account suffixes."""
        accounts = self.get_all()
        return {a.account_suffix for a in accounts if a.account_suffix}

    def calculate_balances(self) -> dict[int, int]:
        """Calculate current balance for all accounts in cents."""
        # Start with opening balances
        balances = {a.id: a.opening_cents for a in self.get_all()}

        # Add/subtract transactions
        rows = self.db.execute(
            select(
                Transaction.account_id,
                Transaction.kind,
                func.sum(Transaction.amount_cents)
            )
            .where(Transaction.user_id == self.user_id)
            .group_by(Transaction.account_id, Transaction.kind)
        ).all()

        for acc_id, kind, total in rows:
            if kind in ("expense", "transfer_out"):
                balances[acc_id] -= total
            elif kind in ("income", "transfer_in"):
                balances[acc_id] += total

        return balances
