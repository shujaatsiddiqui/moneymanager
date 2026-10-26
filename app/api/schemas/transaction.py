"""Transaction schemas."""

from datetime import date as Date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class TransactionIn(BaseModel):
    """Request schema for creating a transaction."""
    date: Date
    kind: Literal["expense", "income", "refund", "transfer"] = "expense"
    amount: float = Field(gt=0)
    account_id: int
    to_account_id: Optional[int] = None  # transfers only
    category_id: Optional[int] = None
    description: str = ""
    note: str = ""
    is_business: bool = False


class TransactionPatch(BaseModel):
    """Request schema for updating a transaction."""
    date: Optional[Date] = None
    kind: Optional[Literal["expense", "income", "refund", "transfer"]] = None
    amount: Optional[float] = Field(default=None, gt=0)
    category_id: Optional[int] = None
    to_account_id: Optional[int] = None  # For transfers
    description: Optional[str] = None
    note: Optional[str] = None
    account_id: Optional[int] = None


class TransactionOut(BaseModel):
    """Response schema for a transaction."""
    id: int
    date: str
    kind: str
    amount: Optional[float]
    account_id: int
    account: Optional[str]
    to_account_id: Optional[int]
    to_account: Optional[str]
    category_id: Optional[int]
    category: Optional[str]
    description: str
    note: str
    is_business: bool
    auto_categorized: bool = False


class DetectTransfersOut(BaseModel):
    """Response schema for detect transfers operation."""
    updated: int
