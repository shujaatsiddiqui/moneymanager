from datetime import date as Date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class AccountIn(BaseModel):
    name: str
    group: Literal["Cash", "Accounts", "Card", "Savings"] = "Accounts"
    is_liability: bool = False
    opening: float = 0.0  # signed; negative on a card = you owe it
    include_in_totals: bool = True
    is_business: bool = False


class AccountPatch(BaseModel):
    name: Optional[str] = None
    opening: Optional[float] = None
    include_in_totals: Optional[bool] = None
    is_business: Optional[bool] = None


class CategoryIn(BaseModel):
    name: str
    parent_id: Optional[int] = None
    emoji: str = ""
    exclude_from_budget: bool = False


class CategoryPatch(BaseModel):
    name: Optional[str] = None
    emoji: Optional[str] = None
    exclude_from_budget: Optional[bool] = None


class BudgetIn(BaseModel):
    category_id: int
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    limit: float = Field(ge=0)


class TransactionIn(BaseModel):
    date: Date
    kind: Literal["expense", "income", "transfer"] = "expense"
    amount: float = Field(gt=0)
    account_id: int
    to_account_id: Optional[int] = None  # transfers only
    category_id: Optional[int] = None
    merchant: str = ""
    note: str = ""
    is_business: bool = False


class TransactionPatch(BaseModel):
    date: Optional[Date] = None
    amount: Optional[float] = Field(default=None, gt=0)
    category_id: Optional[int] = None
    merchant: Optional[str] = None
    note: Optional[str] = None
    account_id: Optional[int] = None


class RuleIn(BaseModel):
    pattern: str = Field(min_length=1)
    category_id: int
    priority: int = 100
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    account_id: Optional[int] = None
