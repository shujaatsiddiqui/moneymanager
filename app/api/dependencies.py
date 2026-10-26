"""API dependencies for dependency injection."""

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..domain.exceptions import (
    DomainException,
    NotFoundError,
    DuplicateError,
    ValidationError,
    TransferError,
    CategoryError,
)
from ..domain.services import (
    AccountService,
    CategoryService,
    BudgetService,
    TransactionService,
    RuleService,
    ImportService,
    ReportService,
)


def get_account_service(db: Session = Depends(get_db)) -> AccountService:
    """Get AccountService instance."""
    return AccountService(db)


def get_category_service(db: Session = Depends(get_db)) -> CategoryService:
    """Get CategoryService instance."""
    return CategoryService(db)


def get_budget_service(db: Session = Depends(get_db)) -> BudgetService:
    """Get BudgetService instance."""
    return BudgetService(db)


def get_transaction_service(db: Session = Depends(get_db)) -> TransactionService:
    """Get TransactionService instance."""
    return TransactionService(db)


def get_rule_service(db: Session = Depends(get_db)) -> RuleService:
    """Get RuleService instance."""
    return RuleService(db)


def get_import_service(db: Session = Depends(get_db)) -> ImportService:
    """Get ImportService instance."""
    return ImportService(db)


def get_report_service(db: Session = Depends(get_db)) -> ReportService:
    """Get ReportService instance."""
    return ReportService(db)


def handle_domain_exception(exc: DomainException) -> HTTPException:
    """Convert domain exception to HTTP exception."""
    if isinstance(exc, NotFoundError):
        return HTTPException(status_code=404, detail=exc.message)
    elif isinstance(exc, DuplicateError):
        return HTTPException(status_code=409, detail=exc.message)
    elif isinstance(exc, (ValidationError, TransferError)):
        return HTTPException(status_code=400, detail=exc.message)
    elif isinstance(exc, CategoryError):
        return HTTPException(status_code=400, detail=exc.message)
    else:
        return HTTPException(status_code=500, detail=exc.message)
