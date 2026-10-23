"""Rule schemas."""

from typing import Optional

from pydantic import BaseModel, Field


class RuleIn(BaseModel):
    """Request schema for creating a rule."""
    pattern: str = Field(min_length=1)
    category_id: int
    priority: int = 100
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    account_id: Optional[int] = None


class RuleOut(BaseModel):
    """Response schema for a rule."""
    id: int
    pattern: str
    priority: int
    category_id: int
    category: str
    min_amount: Optional[float]
    max_amount: Optional[float]
    account_id: Optional[int]


class SuggestOut(BaseModel):
    """Response schema for rule suggestion."""
    category_id: Optional[int]
    rule_id: Optional[int]


class SuggestPatternOut(BaseModel):
    """Response schema for pattern suggestion."""
    pattern: Optional[str]


class ApplyRulesOut(BaseModel):
    """Response schema for apply rules operation."""
    categorized: int
