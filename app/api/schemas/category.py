"""Category schemas."""

from typing import Optional

from pydantic import BaseModel


class CategoryIn(BaseModel):
    """Request schema for creating a category."""
    name: str
    parent_id: Optional[int] = None
    emoji: str = ""
    exclude_from_budget: bool = False


class CategoryPatch(BaseModel):
    """Request schema for updating a category."""
    name: Optional[str] = None
    emoji: Optional[str] = None
    exclude_from_budget: Optional[bool] = None


class CategoryChildOut(BaseModel):
    """Response schema for a subcategory."""
    id: int
    name: str
    parent_id: int


class CategoryOut(BaseModel):
    """Response schema for a category with children."""
    id: int
    name: str
    emoji: str
    exclude_from_budget: bool
    children: list[CategoryChildOut]


# Note: CategoryTreeOut is just list[CategoryOut] in the route response
# We don't need a wrapper class for Pydantic v2


class CategoryTransactionCount(BaseModel):
    """Transaction count for a category."""
    id: int
    name: str
    count: int


class CategoryTransactionsOut(BaseModel):
    """Response schema for category transaction counts."""
    categories: list[CategoryTransactionCount]
    total: int
    child_count: int


class MoveTransactionsOut(BaseModel):
    """Response schema for move transactions operation."""
    moved: int


class DeleteCategoryOut(BaseModel):
    """Response schema for cascade delete."""
    ok: bool = True
    deleted: int
