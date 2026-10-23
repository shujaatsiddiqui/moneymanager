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


class AccountsSummaryOut(BaseModel):
    """Response schema for accounts list with totals."""
    accounts: list[AccountOut]
    assets: Optional[float]
    liabilities: Optional[float]
    total: Optional[float]
