"""Category routes."""

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_category_service, handle_domain_exception
from ..schemas import (
    CategoryIn, CategoryPatch, IdResponse, OkResponse,
    CategoryTransactionsOut, MoveTransactionsOut, DeleteCategoryOut,
)
from ...domain.exceptions import DomainException
from ...domain.services import CategoryService

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
def list_categories(service: CategoryService = Depends(get_category_service)):
    """List all categories as a tree structure."""
    return service.get_tree()


@router.post("", status_code=201, response_model=IdResponse)
def create_category(
    body: CategoryIn,
    service: CategoryService = Depends(get_category_service),
):
    """Create a new category."""
    try:
        category_id = service.create(
            name=body.name,
            parent_id=body.parent_id,
            emoji=body.emoji,
            exclude_from_budget=body.exclude_from_budget,
        )
        return IdResponse(id=category_id)
    except DomainException as e:
        raise handle_domain_exception(e)


@router.patch("/{category_id}", response_model=OkResponse)
def update_category(
    category_id: int,
    body: CategoryPatch,
    service: CategoryService = Depends(get_category_service),
):
    """Update a category."""
    try:
        data = body.model_dump(exclude_unset=True)
        service.update(category_id, **data)
        return OkResponse()
    except DomainException as e:
        raise handle_domain_exception(e)


@router.get("/{category_id}/transactions", response_model=CategoryTransactionsOut)
def get_category_transactions(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
):
    """Get transaction counts for a category and its subcategories."""
    try:
        return service.get_transaction_counts(category_id)
    except DomainException as e:
        raise handle_domain_exception(e)


@router.post("/{category_id}/move-transactions", response_model=MoveTransactionsOut)
def move_category_transactions(
    category_id: int,
    target_id: int = Query(...),
    service: CategoryService = Depends(get_category_service),
):
    """Move all transactions from one category to another."""
    try:
        moved = service.move_transactions(category_id, target_id)
        return MoveTransactionsOut(moved=moved)
    except DomainException as e:
        raise handle_domain_exception(e)


@router.delete("/{category_id}/cascade", response_model=DeleteCategoryOut)
def delete_category_cascade(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
):
    """Delete a category and all its subcategories."""
    try:
        deleted = service.delete_cascade(category_id)
        return DeleteCategoryOut(deleted=deleted)
    except DomainException as e:
        raise handle_domain_exception(e)


@router.delete("/{category_id}", response_model=OkResponse)
def delete_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
):
    """Delete a category (only if empty)."""
    try:
        service.delete(category_id)
        return OkResponse()
    except DomainException as e:
        raise handle_domain_exception(e)
