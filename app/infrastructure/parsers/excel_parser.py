"""Excel file parser."""

import io
from datetime import date, datetime

import pandas as pd

from ...domain.utils import parse_date
from .base import BaseParser, ParsedTransaction


class ExcelParser(BaseParser):
    """Parser for Excel bank statement exports."""

    def __init__(self):
        super().__init__()
        self._detected_format = "Excel"

    @classmethod
    def get_format_name(cls) -> str:
        return "Excel"

    def get_detected_format(self) -> str:
        """Return the detected bank format."""
        return self._detected_format

    def parse(self, content: bytes) -> list[ParsedTransaction]:
        """Parse Excel content (as bytes)."""
        transactions = []

        try:
            df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
        except Exception:
            return []

        # Normalize column names
        df.columns = [str(c).strip().lower() for c in df.columns]

        # Try to detect format and find relevant columns
        date_col = None
        desc_col = None
        amount_col = None

        for col in df.columns:
            if 'date' in col and date_col is None:
                date_col = col
            if 'description' in col or 'details' in col or 'memo' in col:
                desc_col = col
            if 'amount' in col and amount_col is None:
                amount_col = col

        # Fallback: use first few columns
        if date_col is None and len(df.columns) > 0:
            date_col = df.columns[0]
        if desc_col is None and len(df.columns) > 1:
            desc_col = df.columns[1]
        if amount_col is None and len(df.columns) > 2:
            # Look for numeric column
            for col in df.columns:
                if df[col].dtype in ['float64', 'int64']:
                    amount_col = col
                    break

        if not all([date_col, desc_col, amount_col]):
            return []

        # Detect bank format
        cols_str = " ".join(df.columns)
        if 'posting' in cols_str or 'post date' in cols_str:
            self._detected_format = "Chase (Excel)"
        elif 'running' in cols_str:
            self._detected_format = "Bank of America (Excel)"

        for _, row in df.iterrows():
            try:
                # Parse date
                date_val = row[date_col]
                if pd.isna(date_val):
                    continue

                if isinstance(date_val, datetime):
                    tx_date = date_val.date()
                elif isinstance(date_val, date):
                    tx_date = date_val
                else:
                    tx_date = parse_date(str(date_val))

                if not tx_date:
                    continue

                # Parse description
                description = str(row[desc_col]).strip() if pd.notna(row[desc_col]) else ""
                if not description or description == 'nan':
                    continue

                # Parse amount
                amount_val = row[amount_col]
                if pd.isna(amount_val):
                    continue

                if isinstance(amount_val, str):
                    amount_val = amount_val.replace(",", "").replace("$", "")

                amount = float(amount_val)

                if amount == 0:
                    continue

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
            except Exception:
                continue

        return transactions
