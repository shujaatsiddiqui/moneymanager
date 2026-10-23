"""Chase bank CSV parser."""

import csv
import io

from ...domain.utils import parse_date
from .base import BaseParser, ParsedTransaction


class ChaseParser(BaseParser):
    """Parser for Chase bank/credit card CSV exports."""

    @classmethod
    def get_format_name(cls) -> str:
        return "Chase"

    def parse(self, content: str) -> list[ParsedTransaction]:
        """Parse Chase CSV content."""
        transactions = []
        reader = csv.DictReader(io.StringIO(content))

        for row in reader:
            # Chase format: Details, Posting Date, Description, Amount, Type, Balance, Check or Slip #
            # Or: Transaction Date, Post Date, Description, Category, Type, Amount, Memo
            date_str = row.get("Posting Date") or row.get("Post Date") or row.get("Transaction Date", "")
            description = row.get("Description", "").strip()
            amount_str = row.get("Amount", "0").replace(",", "").replace("$", "")

            tx_date = parse_date(date_str)
            if not tx_date:
                continue

            try:
                amount = float(amount_str)
            except ValueError:
                continue

            if amount == 0:
                continue

            # Chase: negative = expense/outflow, positive = income/inflow
            kind, is_inflow = self._determine_kind(amount, description)
            abs_amount = abs(amount)

            transactions.append(ParsedTransaction(
                date=tx_date,
                description=description,
                amount=abs_amount,
                kind=kind,
                is_inflow=is_inflow,
                import_hash=self._generate_hash(tx_date, abs_amount, description),
            ))

        return transactions
