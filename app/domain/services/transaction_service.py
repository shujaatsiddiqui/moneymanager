"""Transaction service - business logic for transactions."""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from ...models import USER_ID, Account, Category, Transaction
from ...infrastructure.repositories import (
    AccountRepository,
    CategoryRepository,
    TransactionRepository,
    RuleRepository,
)
from ...infrastructure.parsers.base import BaseParser
from ..exceptions import NotFoundError, TransferError, ValidationError
from ..utils import from_cents, to_cents


class TransactionService:
    """Service for transaction-related business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = TransactionRepository(db)
        self.account_repo = AccountRepository(db)
        self.category_repo = CategoryRepository(db)
        self.rule_repo = RuleRepository(db)

    def get(self, tx_id: int) -> Transaction:
        """Get transaction by ID or raise NotFoundError."""
        tx = self.repo.get(tx_id)
        if tx is None:
            raise NotFoundError("Transaction", tx_id)
        return tx

    def format_output(self, tx: Transaction, auto_categorized: bool = False) -> dict:
        """Format transaction for API output."""
        cat = self.category_repo.get(tx.category_id) if tx.category_id else None
        parent = self.category_repo.get(cat.parent_id) if cat and cat.parent_id else None
        acc = self.account_repo.get(tx.account_id)
        to_acc = self.account_repo.get(tx.to_account_id) if tx.to_account_id else None

        return {
            "id": tx.id,
            "date": tx.date.isoformat(),
            "kind": tx.kind,
            "amount": from_cents(tx.amount_cents),
            "account_id": tx.account_id,
            "account": acc.name if acc else None,
            "to_account_id": tx.to_account_id,
            "to_account": to_acc.name if to_acc else None,
            "category_id": tx.category_id,
            "category": (f"{parent.name} > {cat.name}" if parent else cat.name) if cat else None,
            "description": tx.description,
            "note": tx.note,
            "is_business": tx.is_business,
            "auto_categorized": auto_categorized,
        }

    def create(
        self,
        tx_date: date,
        kind: str,
        amount: float,
        account_id: int,
        to_account_id: Optional[int] = None,
        category_id: Optional[int] = None,
        description: str = "",
        note: str = "",
        is_business: bool = False,
    ) -> dict:
        """Create a new transaction."""
        # Validate account
        if self.account_repo.get(account_id) is None:
            raise NotFoundError("Account", account_id)

        # Handle transfers
        if kind == "transfer":
            if to_account_id is None:
                raise TransferError("Transfers need to_account_id")
            if to_account_id == account_id:
                raise TransferError("Transfer accounts must differ")
            if self.account_repo.get(to_account_id) is None:
                raise NotFoundError("Account", to_account_id)
        elif to_account_id is not None:
            raise ValidationError("to_account_id is only for transfers")

        cents = to_cents(amount)
        cat_id = category_id
        auto = False

        # Validate category if provided
        if cat_id is not None:
            if self.category_repo.get(cat_id) is None:
                raise NotFoundError("Category", cat_id)
        elif kind in ("expense", "refund"):
            # Auto-categorize expenses and refunds
            rule = self.rule_repo.match(f"{description} {note}", cents, account_id)
            if rule:
                cat_id = rule.category_id
                auto = True

        # Transfers don't have categories
        if kind == "transfer":
            cat_id = None

        tx = Transaction(
            user_id=USER_ID,
            date=tx_date,
            kind=kind,
            amount_cents=cents,
            account_id=account_id,
            to_account_id=to_account_id,
            category_id=cat_id,
            description=description,
            note=note,
            is_business=is_business,
        )

        self.repo.add(tx)
        self.repo.commit()

        return self.format_output(tx, auto)

    def update(
        self,
        tx_id: int,
        tx_date: Optional[date] = None,
        kind: Optional[str] = None,
        amount: Optional[float] = None,
        category_id: Optional[int] = None,
        to_account_id: Optional[int] = None,
        description: Optional[str] = None,
        note: Optional[str] = None,
        account_id: Optional[int] = None,
    ) -> dict:
        """Update a transaction."""
        tx = self.get(tx_id)

        if amount is not None:
            tx.amount_cents = to_cents(amount)

        if kind is not None:
            if kind == "transfer":
                # Transfers require to_account_id
                new_to_acc = to_account_id or tx.to_account_id
                if not new_to_acc:
                    raise TransferError("Transfers require to_account_id")
                if new_to_acc == tx.account_id:
                    raise TransferError("Transfer accounts must differ")
                if self.account_repo.get(new_to_acc) is None:
                    raise NotFoundError("Account", new_to_acc)
                tx.category_id = None  # Transfers don't have categories
            else:
                # If changing from transfer to expense/income, clear to_account_id
                if tx.kind == "transfer":
                    tx.to_account_id = None
            tx.kind = kind

        if tx_date is not None:
            tx.date = tx_date
        if category_id is not None:
            tx.category_id = category_id
        if to_account_id is not None:
            tx.to_account_id = to_account_id
        if description is not None:
            tx.description = description
        if note is not None:
            tx.note = note
        if account_id is not None:
            tx.account_id = account_id

        self.repo.commit()
        return self.format_output(tx)

    def delete(self, tx_id: int) -> None:
        """Delete a transaction."""
        tx = self.get(tx_id)
        self.repo.delete(tx)
        self.repo.commit()

    def list_transactions(
        self,
        month: Optional[str] = None,
        account_id: Optional[int] = None,
        category_id: Optional[int] = None,
        uncategorized: bool = False,
        unbudgeted: bool = False,
        excluded: bool = False,
        is_business: Optional[bool] = None,
        limit: int = 500,
        budgeted_ids: Optional[set[int]] = None,
        excluded_ids: Optional[set[int]] = None,
    ) -> list[dict]:
        """List transactions with filters."""
        from ..utils import month_range

        start_date = None
        end_date = None
        if month:
            start_date, end_date = month_range(month)

        category_ids = None
        if category_id:
            category_ids = self.category_repo.get_category_with_children_ids(category_id)

        # Build filter for kinds and categories
        kinds = None
        if uncategorized or unbudgeted or excluded:
            kinds = ["expense"]

        exclude_category_ids = None
        if unbudgeted and month:
            # Get budgeted and excluded category IDs
            budgeted = budgeted_ids or set()
            excl = excluded_ids or set()
            # For unbudgeted, we want expenses that have a category
            # but that category is not budgeted and not excluded

        txs = self.repo.get_by_filters(
            start_date=start_date,
            end_date=end_date,
            account_id=account_id,
            category_ids=category_ids,
            kinds=kinds,
            uncategorized=uncategorized,
            is_business=is_business,
            limit=limit,
        )

        # Additional filtering for unbudgeted/excluded
        if unbudgeted and month and budgeted_ids is not None and excluded_ids is not None:
            txs = [
                tx for tx in txs
                if tx.category_id is not None
                and tx.category_id not in budgeted_ids
                and tx.category_id not in excluded_ids
            ]
        elif excluded and excluded_ids is not None:
            txs = [tx for tx in txs if tx.category_id in excluded_ids]

        return [self.format_output(tx) for tx in txs]

    def detect_transfers(self) -> int:
        """Scan existing transactions and mark transfers based on description patterns."""
        txs = self.repo.get_by_kind(["expense", "income"])
        parser = BaseParser.__new__(BaseParser)  # Get transfer detection logic

        updated = 0
        for tx in txs:
            if parser.is_likely_transfer(tx.description):
                tx.kind = "transfer"
                tx.category_id = None
                updated += 1

        self.repo.commit()
        return updated
