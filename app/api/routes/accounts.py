"""Account routes."""

from fastapi import APIRouter, Depends

from ..dependencies import get_account_service, handle_domain_exception
from ..schemas import AccountIn, AccountPatch, IdResponse, OkResponse
from ...domain.exceptions import DomainException
from ...domain.services import AccountService

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
def list_accounts(service: AccountService = Depends(get_account_service)):
    """List all accounts with balances."""
    return service.get_summary()


@router.post("", status_code=201, response_model=IdResponse)
def create_account(
    body: AccountIn,
    service: AccountService = Depends(get_account_service),
):
    """Create a new account."""
    try:
        account_id = service.create(
            name=body.name,
            group=body.group,
            is_liability=body.is_liability,
            opening=body.opening,
            include_in_totals=body.include_in_totals,
            is_business=body.is_business,
            account_suffix=body.account_suffix,
        )
        return IdResponse(id=account_id)
    except DomainException as e:
        raise handle_domain_exception(e)


@router.patch("/{account_id}", response_model=OkResponse)
def update_account(
    account_id: int,
    body: AccountPatch,
    service: AccountService = Depends(get_account_service),
):
    """Update an account."""
    try:
        data = body.model_dump(exclude_unset=True)
        service.update(account_id, **data)
        return OkResponse()
    except DomainException as e:
        raise handle_domain_exception(e)
