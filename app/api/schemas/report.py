"""Report schemas."""

from typing import Literal, Optional

from pydantic import BaseModel


class CategoryAmount(BaseModel):
    """Amount by category."""
    category_id: int
    category: str
    emoji: str
    amount: float


class RevenueSection(BaseModel):
    """Revenue section of P&L."""
    total: float
    categories: list[CategoryAmount]
    uncategorized: float


class ExpenseSubSection(BaseModel):
    """Operating or non-operating expenses."""
    total: float
    categories: list[CategoryAmount]
    uncategorized: float = 0


class ExpensesSection(BaseModel):
    """Expenses section of P&L."""
    operating: ExpenseSubSection
    non_operating: ExpenseSubSection


class RefundsSection(BaseModel):
    """Refunds section of P&L."""
    total: float
    categories: list[CategoryAmount]


class PeriodInfo(BaseModel):
    """Period information."""
    start: str
    end: str


class FilterInfo(BaseModel):
    """Filter information."""
    is_business: Optional[bool]


class SummaryInfo(BaseModel):
    """Summary totals."""
    gross_profit: float
    operating_income: float
    net_income: float


class ProfitLossOut(BaseModel):
    """Response schema for P&L report."""
    period: PeriodInfo
    filter: FilterInfo
    revenue: RevenueSection
    expenses: ExpensesSection
    refunds: RefundsSection
    summary: SummaryInfo
