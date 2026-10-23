"""Domain utilities - pure functions for common operations."""

import hashlib
import re
from datetime import date, datetime
from typing import Optional

# Regex for validating YYYY-MM format
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def to_cents(amount: float) -> int:
    """Convert a float dollar amount to integer cents."""
    return int(round(amount * 100))


def from_cents(cents: Optional[int]) -> Optional[float]:
    """Convert integer cents to float dollars."""
    return None if cents is None else cents / 100


def month_range(month: str) -> tuple[date, date]:
    """Get start and end dates for a month string (YYYY-MM).

    Returns:
        Tuple of (start_date, end_date) where end_date is first day of next month.
    """
    y, m = int(month[:4]), int(month[5:7])
    start = date(y, m, 1)
    end = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    return start, end


def parse_date(date_str: str) -> Optional[date]:
    """Parse date from various formats."""
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def generate_import_hash(tx_date: date, amount: float, description: str, counter: int = 0) -> str:
    """Generate a hash to detect duplicate imports.

    Counter differentiates same-day duplicates with identical amount and description.
    """
    data = f"{tx_date.isoformat()}|{amount:.2f}|{description}|{counter}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]


def is_valid_month(month: str) -> bool:
    """Check if a string is a valid YYYY-MM format."""
    return bool(MONTH_RE.match(month))
