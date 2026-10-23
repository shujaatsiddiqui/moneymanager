"""Statement parser - facade for all parsers."""

import re
from typing import Optional

from .base import ParsedTransaction
from .bofa_parser import BofaParser
from .chase_parser import ChaseParser
from .excel_parser import ExcelParser

# Patterns to extract account suffix (last 4 digits) from file content
ACCOUNT_SUFFIX_PATTERNS = [
    r"ACCT[#\s]*(\d{4})",           # "ACCT# 8747" or "ACCT 8747"
    r"FROM CHK[#\s]*(\d{4})",       # "FROM CHK 1655"
    r"TO CHK[#\s]*(\d{4})",         # "TO CHK 1655"
    r"Account.*?(\d{4})\s*$",       # "Account Number: ****1234"
    r"ending in (\d{4})",           # "ending in 1234"
]

ACCOUNT_SUFFIX_PATTERNS_COMPILED = [re.compile(p, re.IGNORECASE) for p in ACCOUNT_SUFFIX_PATTERNS]

# Patterns to extract account suffix from transfer descriptions
TRANSFER_SUFFIX_PATTERNS = [
    r"payment to (?:CRD|card|acct)[#\s]*(\d{4})",
    r"payment to.*ACCT#?\s*(\d{4})",
    r"to (?:CRD|card|acct|SAV|CHK)[#\s\.]*(\d{4})",
    r"from (?:CRD|card|acct|SAV|CHK)[#\s\.]*(\d{4})",
    r"CRD[#\s]*(\d{4})",
    r"ACCT#?\s*(\d{4})",
    r"SAV\s*[\.]*(\d{4})",
    r"CHK\s*[\.]*(\d{4})",
    r"[\.\s]+(\d{4})\s+trans",  # "...5096 transaction"
]

TRANSFER_SUFFIX_PATTERNS_COMPILED = [re.compile(p, re.IGNORECASE) for p in TRANSFER_SUFFIX_PATTERNS]


def detect_csv_format(headers: list[str]) -> str:
    """Detect if CSV is from Chase or Bank of America."""
    headers_lower = [h.lower().strip() for h in headers]

    # BOFA format: Posted Date, Reference Number, Payee, Address, Amount
    if "posted date" in headers_lower and "payee" in headers_lower:
        return "bofa"

    # BOFA format with Running Bal: Date, Description, Amount, Running Bal.
    if "date" in headers_lower and "running bal." in headers_lower:
        return "bofa"

    # Chase checking format: Details, Posting Date, Description, Amount
    if "details" in headers_lower or "posting date" in headers_lower:
        return "chase"

    # Chase CC format: Transaction Date, Post Date, Description, Category, Type, Amount
    if "transaction date" in headers_lower and "post date" in headers_lower:
        return "chase"

    if "running bal." in headers_lower or "running balance" in headers_lower:
        return "bofa"

    if "description" in headers_lower and "amount" in headers_lower:
        return "generic"

    return "unknown"


def parse_csv_statement(content: str) -> tuple[list[ParsedTransaction], str]:
    """Parse CSV and return transactions with detected format."""
    lines = content.split("\n")

    # Find the actual header row (some BOFA files have summary at top)
    header_idx = 0
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if "date" in line_lower and ("description" in line_lower or "payee" in line_lower):
            header_idx = i
            break

    # If we found a header row that's not the first line, use content from there
    if header_idx > 0:
        content = "\n".join(lines[header_idx:])

    first_line = content.split("\n")[0]
    headers = [h.strip() for h in first_line.split(",")]

    fmt = detect_csv_format(headers)

    if fmt == "chase":
        parser = ChaseParser()
        return parser.parse(content), parser.get_format_name()
    elif fmt in ("bofa", "generic", "unknown"):
        parser = BofaParser()
        return parser.parse(content), parser.get_format_name()
    else:
        parser = BofaParser()
        return parser.parse(content), parser.get_format_name()


def parse_statement(content: bytes, filename: str) -> tuple[list[ParsedTransaction], str]:
    """Parse statement file (CSV or Excel) and return transactions."""
    filename_lower = filename.lower()

    if filename_lower.endswith(('.xlsx', '.xls')):
        parser = ExcelParser()
        transactions = parser.parse(content)
        return transactions, parser.get_detected_format()
    else:
        # Try CSV
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        return parse_csv_statement(text)


def extract_account_suffixes(content: str) -> set[str]:
    """Extract all account number suffixes (last 4 digits) found in file content."""
    suffixes = set()
    for pattern in ACCOUNT_SUFFIX_PATTERNS_COMPILED:
        for match in pattern.finditer(content):
            suffixes.add(match.group(1))
    return suffixes


def extract_suffix_from_filename(filename: str) -> Optional[str]:
    """Extract account suffix from filename like 'Chase3518_Activity.csv'."""
    # Find any 4-digit sequence in the filename
    matches = re.findall(r'(\d{4})', filename)
    # Return the first 4-digit match (usually the account suffix)
    # Skip if it looks like a date (year like 2026)
    for m in matches:
        if not m.startswith('20') and not m.startswith('19'):
            return m
    return None


def extract_account_suffix_from_description(description: str) -> Optional[str]:
    """Extract potential account suffix (last 4 digits) from a transfer description."""
    for pattern in TRANSFER_SUFFIX_PATTERNS_COMPILED:
        match = pattern.search(description)
        if match:
            return match.group(1)
    return None
