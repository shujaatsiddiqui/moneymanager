"""Base parser and common types."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class ParsedTransaction:
    """A parsed transaction from a bank statement."""
    date: date
    description: str
    amount: float  # Absolute value
    kind: str  # "expense", "income", or "transfer"
    is_inflow: bool  # True if money coming in
    import_hash: str


class BaseParser(ABC):
    """Base class for bank statement parsers."""

    # Patterns for detecting transfers
    TRANSFER_PATTERNS = [
        # Credit card payments from checking
        r"PAYMENT TO ACCT[#\s]*\d+",
        r"ONLINE/MOBILE RECURRING FROM CHK",
        r"ONLINE PAYMENT FROM CHK",
        r"PAYMENT FROM CHK",
        r"MOBILE PAYMENT.*TO ACCT",
        r"AUTOMATIC PAYMENT.*THANK",
        r"AUTOPAY PAYMENT.*THANK",
        r"Online Banking payment to CRD",
        r"PAYMENT TO CRD",
        # Online transfers between accounts
        r"Online Transfer from\s+CHK",
        r"Online Transfer to\s+CHK",
        r"Online Transfer from\s+SAV",
        r"Online Transfer to\s+SAV",
        r"Online Transfer from.*transaction",
        r"Online Transfer to.*transaction",
        # ACH transfers
        r"ACH TRANSFER",
        r"INTERNAL TRANSFER",
        r"TRANSFER TO.*SAVINGS",
        r"TRANSFER FROM.*SAVINGS",
        r"TRANSFER TO.*CHECKING",
        r"TRANSFER FROM.*CHECKING",
        # Credit card payments (Chase)
        r"ORIG CO NAME:CHASE CREDIT",
        r"CHASE CREDIT CRD",
        # Apple Card payments
        r"APPLECARD.*PAYMENT",
        r"APPLECARD GSBANK",
        # Amazon card payments
        r"AMAZON.*PAYMENT",
        r"SYNCB/AMAZON",
        # Generic card payment patterns
        r"DES:PAYMENT.*GSBANK",
        r"DES:PAYMENT.*CARD",
    ]

    TRANSFER_PATTERNS_COMPILED = [re.compile(p, re.IGNORECASE) for p in TRANSFER_PATTERNS]

    def __init__(self):
        self.hash_counts: dict[str, int] = {}

    @abstractmethod
    def parse(self, content: str) -> list[ParsedTransaction]:
        """Parse content and return list of transactions."""
        pass

    @classmethod
    def get_format_name(cls) -> str:
        """Return the human-readable format name."""
        return "Unknown"

    def is_likely_transfer(self, description: str) -> bool:
        """Check if a transaction description looks like an inter-account transfer."""
        for pattern in self.TRANSFER_PATTERNS_COMPILED:
            if pattern.search(description):
                return True
        return False

    def _generate_hash(self, tx_date: date, amount: float, description: str) -> str:
        """Generate unique import hash, handling duplicates."""
        import hashlib

        base_key = f"{tx_date.isoformat()}|{amount:.2f}|{description}"
        counter = self.hash_counts.get(base_key, 0)
        self.hash_counts[base_key] = counter + 1

        data = f"{base_key}|{counter}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def _determine_kind(self, amount: float, description: str) -> tuple[str, bool]:
        """Determine transaction kind and inflow status.

        Returns:
            Tuple of (kind, is_inflow)
        """
        is_inflow = amount > 0
        if self.is_likely_transfer(description):
            kind = "transfer"
        else:
            kind = "income" if is_inflow else "expense"
        return kind, is_inflow
