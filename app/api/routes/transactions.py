"""Transaction routes."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from ..dependencies import (
    get_transaction_service,
    get_budget_service,
    get_category_service,
    handle_domain_exception,
)
from ..schemas import TransactionIn, TransactionPatch, OkResponse, DetectTransfersOut
from ...domain.exceptions import DomainException
from ...domain.services import TransactionService, BudgetService, CategoryService

router = APIRouter(prefix="/transactions", tags=["transactions"])

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


@router.post("", status_code=201)
def create_transaction(
    body: TransactionIn,
    service: TransactionService = Depends(get_transaction_service),
):
    """Create a new transaction."""
    try:
        return service.create(
            tx_date=body.date,
            kind=body.kind,
            amount=body.amount,
            account_id=body.account_id,
            to_account_id=body.to_account_id,
            category_id=body.category_id,
            description=body.description,
            note=body.note,
            is_business=body.is_business,
        )
    except DomainException as e:
        raise handle_domain_exception(e)


@router.get("")
def list_transactions(
    month: Optional[str] = Query(default=None, pattern=MONTH_PATTERN),
    account_id: Optional[int] = None,
    category_id: Optional[int] = None,
    uncategorized: bool = False,
    unbudgeted: bool = False,
    excluded: bool = False,
    limit: int = Query(500, le=5000),
    service: TransactionService = Depends(get_transaction_service),
    budget_service: BudgetService = Depends(get_budget_service),
    category_service: CategoryService = Depends(get_category_service),
):
    """List transactions with filters."""
    # Get budgeted and excluded IDs if needed
    budgeted_ids = None
    excluded_ids = None

    if unbudgeted and month:
        budgeted_ids = budget_service.get_budgeted_category_ids(month)
        excluded_ids = category_service.get_excluded_category_ids()
    elif excluded:
        excluded_ids = category_service.get_excluded_category_ids()

    return service.list_transactions(
        month=month,
        account_id=account_id,
        category_id=category_id,
        uncategorized=uncategorized,
        unbudgeted=unbudgeted,
        excluded=excluded,
        limit=limit,
        budgeted_ids=budgeted_ids,
        excluded_ids=excluded_ids,
    )


@router.patch("/{tx_id}")
def update_transaction(
    tx_id: int,
    body: TransactionPatch,
    service: TransactionService = Depends(get_transaction_service),
):
    """Update a transaction."""
    try:
        data = body.model_dump(exclude_unset=True)
        # Rename 'date' to 'tx_date' for service method
        if "date" in data:
            data["tx_date"] = data.pop("date")
        return service.update(tx_id, **data)
    except DomainException as e:
        raise handle_domain_exception(e)


@router.delete("/{tx_id}", response_model=OkResponse)
def delete_transaction(
    tx_id: int,
    service: TransactionService = Depends(get_transaction_service),
):
    """Delete a transaction."""
    try:
        service.delete(tx_id)
        return OkResponse()
    except DomainException as e:
        raise handle_domain_exception(e)


@router.post("/detect-transfers", response_model=DetectTransfersOut)
def detect_transfers(
    service: TransactionService = Depends(get_transaction_service),
):
    """Scan transactions and mark transfers."""
    updated = service.detect_transfers()
    return DetectTransfersOut(updated=updated)
