"""Budget routes."""

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_budget_service, handle_domain_exception
from ..schemas import BudgetIn, IdResponse, OkResponse, CopyBudgetsOut
from ...domain.exceptions import DomainException
from ...domain.services import BudgetService

router = APIRouter(prefix="/budgets", tags=["budgets"])

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


@router.get("/status")
def budget_status(
    month: str = Query(pattern=MONTH_PATTERN),
    service: BudgetService = Depends(get_budget_service),
):
    """Get budget status for a month."""
    return service.get_status(month)


@router.put("", response_model=IdResponse)
def set_budget(
    body: BudgetIn,
    service: BudgetService = Depends(get_budget_service),
):
    """Set or update a budget."""
    try:
        budget_id = service.set_budget(
            category_id=body.category_id,
            month=body.month,
            limit=body.limit,
        )
        return IdResponse(id=budget_id)
    except DomainException as e:
        raise handle_domain_exception(e)


@router.delete("", response_model=OkResponse)
def delete_budget(
    category_id: int,
    month: str = Query(pattern=MONTH_PATTERN),
    service: BudgetService = Depends(get_budget_service),
):
    """Delete a budget."""
    service.delete_budget(category_id, month)
    return OkResponse()


@router.post("/copy", response_model=CopyBudgetsOut)
def copy_budgets(
    from_month: str = Query(pattern=MONTH_PATTERN),
    to_month: str = Query(pattern=MONTH_PATTERN),
    service: BudgetService = Depends(get_budget_service),
):
    """Copy budgets from one month to another."""
    copied = service.copy_budgets(from_month, to_month)
    return CopyBudgetsOut(copied=copied)
