"""Budget schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class BudgetIn(BaseModel):
    """Request schema for setting a budget."""
    category_id: int
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    limit: float = Field(ge=0)


class BudgetRowOut(BaseModel):
    """Response schema for a single budget row."""
    category_id: int
    category: str
    emoji: str
    limit: Optional[float]
    spent: Optional[float]
    left: Optional[float]
    pct: Optional[float]


class BudgetStatusOut(BaseModel):
    """Response schema for budget status."""
    month: str
    rows: list[BudgetRowOut]
    total_limit: Optional[float]
    total_spent: Optional[float]
    total_left: Optional[float]
    unbudgeted_spent: Optional[float]
    uncategorized_spent: Optional[float]
    excluded_spent: Optional[float]
    total_income: Optional[float]
    total_expenses: Optional[float]
    saved: Optional[float]
    savings_rate: float


class CopyBudgetsOut(BaseModel):
    """Response schema for copy budgets operation."""
    copied: int
