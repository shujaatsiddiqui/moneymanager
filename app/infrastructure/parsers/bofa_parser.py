"""Bank of America CSV parser."""

import csv
import io

from ...domain.utils import parse_date
from .base import BaseParser, ParsedTransaction


class BofaParser(BaseParser):
    """Parser for Bank of America CSV exports."""

    @classmethod
    def get_format_name(cls) -> str:
        return "Bank of America"

    def parse(self, content: str) -> list[ParsedTransaction]:
        """Parse Bank of America CSV content."""
        transactions = []
        reader = csv.DictReader(io.StringIO(content))

        for row in reader:
            # BOFA format: Posted Date, Reference Number, Payee, Address, Amount
            # Or older format: Date, Description, Amount, Running Bal.
            date_str = row.get("Posted Date") or row.get("Date", "")
            description = row.get("Payee") or row.get("Description", "")
            description = description.strip() if description else ""
            amount_str = row.get("Amount", "0").replace(",", "").replace("$", "").replace('"', '')

            tx_date = parse_date(date_str)
            if not tx_date:
                continue

            try:
                amount = float(amount_str)
            except ValueError:
                continue

            if amount == 0:
                continue

            # BOFA: negative = expense/outflow, positive = income/inflow
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
