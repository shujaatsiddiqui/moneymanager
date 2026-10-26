# Route handlers
from fastapi import APIRouter

from .accounts import router as accounts_router
from .categories import router as categories_router
from .budgets import router as budgets_router
from .transactions import router as transactions_router
from .rules import router as rules_router
from .imports import router as imports_router
from .reports import router as reports_router


def get_api_router() -> APIRouter:
    """Create and return the main API router with all sub-routers."""
    api_router = APIRouter()
    api_router.include_router(accounts_router)
    api_router.include_router(categories_router)
    api_router.include_router(budgets_router)
    api_router.include_router(transactions_router)
    api_router.include_router(rules_router)
    api_router.include_router(imports_router)
    api_router.include_router(reports_router)
    return api_router


__all__ = [
    "accounts_router",
    "categories_router",
    "budgets_router",
    "transactions_router",
    "rules_router",
    "imports_router",
    "reports_router",
    "get_api_router",
]
