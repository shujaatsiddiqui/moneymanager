"""Rule routes."""

from typing import Optional

from fastapi import APIRouter, Depends

from ..dependencies import get_rule_service, handle_domain_exception
from ..schemas import RuleIn, IdResponse, OkResponse, SuggestOut, SuggestPatternOut, ApplyRulesOut
from ...domain.exceptions import DomainException
from ...domain.services import RuleService

router = APIRouter(prefix="/rules", tags=["rules"])


@router.get("")
def list_rules(service: RuleService = Depends(get_rule_service)):
    """List all rules."""
    return service.list_all()


@router.post("", status_code=201, response_model=IdResponse)
def create_rule(
    body: RuleIn,
    service: RuleService = Depends(get_rule_service),
):
    """Create a new rule."""
    try:
        rule_id = service.create(
            pattern=body.pattern,
            category_id=body.category_id,
            priority=body.priority,
            min_amount=body.min_amount,
            max_amount=body.max_amount,
            account_id=body.account_id,
        )
        return IdResponse(id=rule_id)
    except DomainException as e:
        raise handle_domain_exception(e)


@router.delete("/{rule_id}", response_model=OkResponse)
def delete_rule(
    rule_id: int,
    service: RuleService = Depends(get_rule_service),
):
    """Delete a rule."""
    try:
        service.delete(rule_id)
        return OkResponse()
    except DomainException as e:
        raise handle_domain_exception(e)


@router.get("/suggest", response_model=SuggestOut)
def suggest(
    text: str,
    amount: Optional[float] = None,
    service: RuleService = Depends(get_rule_service),
):
    """Suggest category based on rules."""
    return service.suggest(text, amount)


@router.get("/suggest-pattern", response_model=SuggestPatternOut)
def suggest_pattern(
    description: str,
    service: RuleService = Depends(get_rule_service),
):
    """Use AI to suggest a rule pattern."""
    pattern = service.suggest_pattern(description)
    return SuggestPatternOut(pattern=pattern)


@router.post("/apply", response_model=ApplyRulesOut)
def apply_rules(service: RuleService = Depends(get_rule_service)):
    """Apply rules to uncategorized transactions."""
    categorized = service.apply_to_uncategorized()
    return ApplyRulesOut(categorized=categorized)
