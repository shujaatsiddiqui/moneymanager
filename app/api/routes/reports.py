"""Report routes."""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_report_service
from ..schemas.report import ProfitLossOut
from ...domain.services import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


@router.get("/profit-loss", response_model=ProfitLossOut)
def get_profit_loss(
    month: str = Query(pattern=MONTH_PATTERN, description="Month in YYYY-MM format"),
    is_business: Optional[bool] = Query(
        default=None,
        description="Filter by business (true) or personal (false) transactions"
    ),
    service: ReportService = Depends(get_report_service),
):
    """Get Profit & Loss report for a specific month."""
    return service.get_monthly_profit_loss(month, is_business)


@router.get("/profit-loss/ytd", response_model=ProfitLossOut)
def get_ytd_profit_loss(
    year: int = Query(description="Year for YTD report"),
    is_business: Optional[bool] = Query(
        default=None,
        description="Filter by business (true) or personal (false) transactions"
    ),
    service: ReportService = Depends(get_report_service),
):
    """Get Year-to-Date Profit & Loss report."""
    return service.get_ytd_profit_loss(year, is_business)
