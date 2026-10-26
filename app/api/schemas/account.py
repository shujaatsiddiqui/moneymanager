"""Account schemas."""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


class AccountIn(BaseModel):
    """Request schema for creating an account."""
    name: str
    group: Literal["Cash", "Accounts", "Card", "Savings"] = "Accounts"
    is_liability: bool = False
    opening: float = 0.0  # signed; negative on a card = you owe it
    include_in_totals: bool = True
    is_business: bool = False
    account_suffix: Optional[str] = None  # Last 4 digits for auto-detection


class AccountPatch(BaseModel):
    """Request schema for updating an account."""
    name: Optional[str] = None
    opening: Optional[float] = None
    include_in_totals: Optional[bool] = None
    is_business: Optional[bool] = None
    account_suffix: Optional[str] = None
    due_day: Optional[int] = None  # Payment due day (1-31) for credit cards


class AccountOut(BaseModel):
    """Response schema for a single account."""
    id: int
    name: str
    group: str
    is_liability: bool
    include_in_totals: bool
    is_business: bool
    opening: Optional[float]
    balance: Optional[float]
    account_suffix: Optional[str]
    last_import_at: Optional[datetime]
    last_tx_date: Optional[date]
    due_day: Optional[int]


class AccountsSummaryOut(BaseModel):
    """Response schema for accounts list with totals."""
    accounts: list[AccountOut]
    assets: Optional[float]
    liabilities: Optional[float]
    total: Optional[float]


class CreditCardDueOut(BaseModel):
    """Response schema for credit card due date info."""
    id: int
    name: str
    balance: float
    due_day: Optional[int]
    next_due_date: Optional[str]
    days_until_due: Optional[int]
    is_overdue: bool = False
