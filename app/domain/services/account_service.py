"""Account service - business logic for accounts."""

from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ...models import USER_ID, Account
from ...infrastructure.repositories import AccountRepository
from ..exceptions import DuplicateError, NotFoundError
from ..utils import from_cents, to_cents


class AccountService:
    """Service for account-related business logic."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AccountRepository(db)

    def get(self, account_id: int) -> Account:
        """Get account by ID or raise NotFoundError."""
        account = self.repo.get(account_id)
        if account is None:
            raise NotFoundError("Account", account_id)
        return account

    def get_summary(self) -> dict:
        """Get accounts summary with balances and totals."""
        balances = self.repo.calculate_balances()
        accounts = self.repo.get_all_ordered()

        out = []
        assets = 0
        liabilities = 0

        for a in accounts:
            balance = balances.get(a.id, 0)
            out.append({
                "id": a.id,
                "name": a.name,
                "group": a.group_name,
                "is_liability": a.is_liability,
                "include_in_totals": a.include_in_totals,
                "is_business": a.is_business,
                "opening": from_cents(a.opening_cents),
                "balance": from_cents(balance),
                "account_suffix": a.account_suffix,
                "last_import_at": a.last_import_at.isoformat() if a.last_import_at else None,
                "last_tx_date": a.last_tx_date.isoformat() if a.last_tx_date else None,
                "due_day": a.due_day,
                "statement_day": a.statement_day,
            })

            if a.include_in_totals:
                if a.is_liability:
                    liabilities += balance
                else:
                    assets += balance

        return {
            "accounts": out,
            "assets": from_cents(assets),
            "liabilities": from_cents(liabilities),
            "total": from_cents(assets + liabilities),
        }

    def create(
        self,
        name: str,
        group: str = "Accounts",
        is_liability: bool = False,
        opening: float = 0.0,
        include_in_totals: bool = True,
        is_business: bool = False,
        account_suffix: Optional[str] = None,
    ) -> int:
        """Create a new account."""
        # Auto-set is_liability for cards
        if group == "Card":
            is_liability = True

        account = Account(
            user_id=USER_ID,
            name=name,
            group_name=group,
            is_liability=is_liability,
            opening_cents=to_cents(opening),
            include_in_totals=include_in_totals,
            is_business=is_business,
            account_suffix=account_suffix,
        )

        self.repo.add(account)
        try:
            self.repo.commit()
        except IntegrityError:
            self.repo.rollback()
            raise DuplicateError("An account with that name already exists")

        return account.id

    def update(
        self,
        account_id: int,
        name: Optional[str] = None,
        opening: Optional[float] = None,
        include_in_totals: Optional[bool] = None,
        is_business: Optional[bool] = None,
        account_suffix: Optional[str] = None,
        due_day: Optional[int] = None,
        statement_day: Optional[int] = None,
    ) -> None:
        """Update an account."""
        account = self.get(account_id)

        if name is not None:
            account.name = name
        if opening is not None:
            account.opening_cents = to_cents(opening)
        if include_in_totals is not None:
            account.include_in_totals = include_in_totals
        if is_business is not None:
            account.is_business = is_business
        if account_suffix is not None:
            account.account_suffix = account_suffix
        if due_day is not None:
            account.due_day = due_day
        if statement_day is not None:
            account.statement_day = statement_day

        self.repo.commit()

    def get_credit_card_dues(self) -> list[dict]:
        """Get credit card accounts with due date info."""
        from datetime import date, timedelta

        balances = self.repo.calculate_balances()
        accounts = self.repo.get_all_ordered()

        today = date.today()
        result = []

        for a in accounts:
            # Only include credit cards (liabilities in Card group)
            if not a.is_liability or a.group_name != "Card":
                continue

            balance = balances.get(a.id, 0)

            # Calculate next due date and days until due
            next_due_date = None
            days_until_due = None
            is_overdue = False

            if a.due_day:
                # Calculate next due date
                year = today.year
                month = today.month

                # Handle months with fewer days
                import calendar
                last_day = calendar.monthrange(year, month)[1]
                due_day = min(a.due_day, last_day)

                next_due = date(year, month, due_day)

                # If already past this month's due date, use next month
                if next_due < today:
                    if month == 12:
                        month = 1
                        year += 1
                    else:
                        month += 1
                    last_day = calendar.monthrange(year, month)[1]
                    due_day = min(a.due_day, last_day)
                    next_due = date(year, month, due_day)

                next_due_date = next_due.isoformat()
                days_until_due = (next_due - today).days
                is_overdue = days_until_due < 0

            result.append({
                "id": a.id,
                "name": a.name,
                "balance": from_cents(balance),
                "due_day": a.due_day,
                "statement_day": a.statement_day,
                "next_due_date": next_due_date,
                "days_until_due": days_until_due,
                "is_overdue": is_overdue,
            })

        # Sort by days_until_due (None at end)
        result.sort(key=lambda x: (x["days_until_due"] is None, x["days_until_due"] or 0))

        return result

    def get_by_suffix(self, suffix: str) -> Optional[Account]:
        """Get account by suffix."""
        return self.repo.get_by_suffix(suffix)

    def get_all_suffixes(self) -> set[str]:
        """Get all account suffixes."""
        return self.repo.get_all_suffixes()

    def detect_from_content(self, content: str, filename: str = "") -> Optional[int]:
        """Try to detect which account a file belongs to based on content/filename."""
        from ...infrastructure.parsers.statement_parser import (
            extract_account_suffixes,
            extract_suffix_from_filename,
        )

        suffixes = extract_account_suffixes(content)

        # Also check filename for suffix
        filename_suffix = extract_suffix_from_filename(filename)
        if filename_suffix:
            suffixes.add(filename_suffix)

        if not suffixes:
            return None

        # Find accounts with matching suffixes
        accounts = self.repo.get_by_suffixes(suffixes)

        # If exactly one account matches, return it
        if len(accounts) == 1:
            return accounts[0].id

        # If filename suffix matched an account, prefer that one
        if filename_suffix and len(accounts) > 1:
            for acc in accounts:
                if acc.account_suffix == filename_suffix:
                    return acc.id

        # If multiple match, return the first one
        if accounts:
            return accounts[0].id

        return None
