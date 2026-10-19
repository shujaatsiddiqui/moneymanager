import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from datetime import date, datetime
from typing import Optional, Union

import pandas as pd
import requests
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import USER_ID, Account, Budget, Category, Rule, Transaction

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "moneymanager"  # Custom model with categorization context

MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def to_cents(amount: float) -> int:
    return int(round(amount * 100))


def from_cents(cents: Optional[int]) -> Optional[float]:
    return None if cents is None else cents / 100


def month_range(month: str):
    y, m = int(month[:4]), int(month[5:7])
    start = date(y, m, 1)
    end = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    return start, end


# ---------- accounts ----------

def account_balances(db: Session) -> dict:
    """Signed balance per account. Cards go negative when you owe money."""
    bal = {a.id: a.opening_cents for a in db.scalars(select(Account).where(Account.user_id == USER_ID))}
    rows = db.execute(
        select(Transaction.account_id, Transaction.to_account_id, Transaction.kind,
               func.sum(Transaction.amount_cents))
        .where(Transaction.user_id == USER_ID)
        .group_by(Transaction.account_id, Transaction.to_account_id, Transaction.kind)
    ).all()
    for acc, to_acc, kind, total in rows:
        if kind == "expense":
            bal[acc] -= total
        elif kind == "income":
            bal[acc] += total
        elif kind == "transfer":
            bal[acc] -= total
            if to_acc in bal:
                bal[to_acc] += total
    return bal


def accounts_summary(db: Session) -> dict:
    bal = account_balances(db)
    accounts = db.scalars(select(Account).where(Account.user_id == USER_ID).order_by(Account.sort)).all()
    out, assets, liabilities = [], 0, 0
    for a in accounts:
        b = bal[a.id]
        out.append({
            "id": a.id, "name": a.name, "group": a.group_name, "is_liability": a.is_liability,
            "include_in_totals": a.include_in_totals, "is_business": a.is_business,
            "opening": from_cents(a.opening_cents), "balance": from_cents(b),
        })
        if a.include_in_totals:
            if a.is_liability:
                liabilities += b
            else:
                assets += b
    return {"accounts": out, "assets": from_cents(assets),
            "liabilities": from_cents(liabilities), "total": from_cents(assets + liabilities)}


# ---------- categories ----------

def category_tree(db: Session) -> list:
    cats = db.scalars(select(Category).where(Category.user_id == USER_ID).order_by(Category.sort, Category.id)).all()
    kids = defaultdict(list)
    for c in cats:
        if c.parent_id:
            kids[c.parent_id].append(c)
    return [{
        "id": c.id, "name": c.name, "emoji": c.emoji, "exclude_from_budget": c.exclude_from_budget,
        "children": [{"id": k.id, "name": k.name, "parent_id": c.id} for k in kids[c.id]],
    } for c in cats if c.parent_id is None]


# ---------- budgets ----------

def budget_status(db: Session, month: str) -> dict:
    """Spent / left per budgeted category. A parent budget includes its subcategories."""
    start, end = month_range(month)
    cats = {c.id: c for c in db.scalars(select(Category).where(Category.user_id == USER_ID))}
    children = defaultdict(list)
    for c in cats.values():
        if c.parent_id:
            children[c.parent_id].append(c.id)

    spent_by_cat = dict(db.execute(
        select(Transaction.category_id, func.sum(Transaction.amount_cents))
        .where(Transaction.user_id == USER_ID, Transaction.kind == "expense",
               Transaction.date >= start, Transaction.date < end)
        .group_by(Transaction.category_id)
    ).all())

    def spent(cid: int) -> int:
        return sum(spent_by_cat.get(i, 0) for i in [cid] + children.get(cid, []))

    def excluded(cid: Optional[int]) -> bool:
        c = cats.get(cid)
        if c is None:
            return False
        return c.exclude_from_budget or (c.parent_id is not None and cats[c.parent_id].exclude_from_budget)

    budgets = db.scalars(select(Budget).where(Budget.user_id == USER_ID, Budget.month == month)).all()
    rows, covered = [], set()
    for b in budgets:
        c = cats[b.category_id]
        s = spent(b.category_id)
        covered.update([b.category_id] + children.get(b.category_id, []))
        rows.append({
            "category_id": c.id, "category": c.name, "emoji": c.emoji,
            "limit": from_cents(b.limit_cents), "spent": from_cents(s),
            "left": from_cents(b.limit_cents - s),
            "pct": round(s / b.limit_cents * 100, 1) if b.limit_cents else None,
        })
    rows.sort(key=lambda r: (r["left"] is None, r["left"]))

    uncategorized = spent_by_cat.get(None, 0)
    unbudgeted = sum(v for cid, v in spent_by_cat.items()
                     if cid is not None and cid not in covered and not excluded(cid))
    excluded_total = sum(v for cid, v in spent_by_cat.items() if cid is not None and excluded(cid))
    total_limit = sum(b.limit_cents for b in budgets)
    total_spent = sum(to_cents(r["spent"]) for r in rows)
    return {
        "month": month, "rows": rows,
        "total_limit": from_cents(total_limit), "total_spent": from_cents(total_spent),
        "total_left": from_cents(total_limit - total_spent),
        "unbudgeted_spent": from_cents(unbudgeted),
        "uncategorized_spent": from_cents(uncategorized),
        "excluded_spent": from_cents(excluded_total),
    }


# ---------- rules / categorizer ----------

def _matches(rule: Rule, text: str, amount_cents: Optional[int], account_id: Optional[int]) -> bool:
    if rule.account_id is not None and rule.account_id != account_id:
        return False
    if amount_cents is not None:
        if rule.min_cents is not None and amount_cents < rule.min_cents:
            return False
        if rule.max_cents is not None and amount_cents > rule.max_cents:
            return False
    if rule.pattern.lower().startswith("re:"):
        try:
            return re.search(rule.pattern[3:], text, re.IGNORECASE) is not None
        except re.error:
            return False
    return rule.pattern.lower() in text.lower()


def categorize(db: Session, text: str, amount_cents: Optional[int] = None,
               account_id: Optional[int] = None) -> Optional[Rule]:
    if not text.strip():
        return None
    rules = db.scalars(select(Rule).where(Rule.user_id == USER_ID).order_by(Rule.priority, Rule.id))
    for r in rules:
        if _matches(r, text, amount_cents, account_id):
            return r
    return None


def apply_rules_to_uncategorized(db: Session) -> int:
    txs = db.scalars(select(Transaction).where(
        Transaction.user_id == USER_ID, Transaction.kind == "expense",
        Transaction.category_id.is_(None))).all()
    n = 0
    for t in txs:
        r = categorize(db, f"{t.merchant} {t.note}", t.amount_cents, t.account_id)
        if r:
            t.category_id = r.category_id
            n += 1
    db.commit()
    return n


# ---------- AI categorization ----------

def get_category_list(db: Session) -> list[dict]:
    """Get flat list of categories with their IDs for AI prompt."""
    cats = db.scalars(select(Category).where(Category.user_id == USER_ID)).all()
    result = []
    parent_map = {c.id: c.name for c in cats if c.parent_id is None}

    for c in cats:
        if c.parent_id is None:
            result.append({"id": c.id, "name": c.name, "parent": None})
        else:
            parent_name = parent_map.get(c.parent_id, "")
            result.append({"id": c.id, "name": f"{parent_name} > {c.name}", "parent": c.parent_id})

    return result


def ai_categorize_single(description: str, categories: list[dict]) -> Optional[int]:
    """Use Ollama to categorize a single transaction."""
    cat_list = "\n".join([f"- ID {c['id']}: {c['name']}" for c in categories])

    prompt = f"""You are a financial transaction categorizer. Given a transaction description, return ONLY the category ID number that best matches.

Examples of correct categorizations:
- "WALMART" or "WM SUPERCENTER" → Household > Groceries
- "TOM THUMB", "SPROUTS", "INDIA METRO" → Household > Groceries
- "7-ELEVEN" → Food & Outing (snacks/convenience)
- "STARBUCKS", "KED'S ICE CREAM" → Food & Outing
- "TST*" restaurants → Food & Outing > Eating out
- "ROSS STORES", "DOLLAR TREE", "BATH & BODY" → Shopping/LTE
- "AMAZON" purchases → Shopping/LTE (default)
- "Supercuts" → Beauty > Grooming
- "ISLAMIC ASSOCIATION" → Social work > Charity
- "MASTERKANG" martial arts → Bill Payment > Taekwondo
- "Google One", "YouTube Premium" → Apps
- "EPIC PIZZA" → Food & Outing > Eating out

Categories:
{cat_list}

Transaction: "{description}"

Rules:
- Return ONLY the numeric ID, nothing else
- Choose the most specific subcategory when available
- If unsure, return 0

Category ID:"""

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=30
        )
        if resp.status_code == 200:
            result = resp.json().get("response", "").strip()
            # Extract just the number
            match = re.search(r'\d+', result)
            if match:
                cat_id = int(match.group())
                # Verify it's a valid category
                valid_ids = {c["id"] for c in categories}
                if cat_id in valid_ids:
                    return cat_id
    except Exception:
        pass

    return None


def ai_categorize_batch(db: Session, transactions: list[dict]) -> list[dict]:
    """Categorize multiple transactions using AI."""
    categories = get_category_list(db)

    for tx in transactions:
        if tx.get("category_id") is None and tx["kind"] == "expense":
            cat_id = ai_categorize_single(tx["description"], categories)
            tx["ai_category_id"] = cat_id

    return transactions


def check_ollama_available() -> bool:
    """Check if Ollama is running and model is available."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            models = [m["name"] for m in resp.json().get("models", [])]
            return any(OLLAMA_MODEL in m for m in models)
    except Exception:
        pass
    return False


# ---------- CSV import ----------

def parse_date(date_str: str) -> Optional[date]:
    """Parse date from various formats."""
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def generate_import_hash(tx_date: date, amount: float, description: str, counter: int = 0) -> str:
    """Generate a hash to detect duplicate imports. Counter differentiates same-day duplicates."""
    data = f"{tx_date.isoformat()}|{amount:.2f}|{description}|{counter}"
    return hashlib.sha256(data.encode()).hexdigest()[:32]


def detect_csv_format(headers: list[str]) -> str:
    """Detect if CSV is from Chase or Bank of America."""
    headers_lower = [h.lower().strip() for h in headers]
    # BOFA format: Posted Date, Reference Number, Payee, Address, Amount
    if "posted date" in headers_lower and "payee" in headers_lower:
        return "bofa"
    if "details" in headers_lower or "posting date" in headers_lower:
        return "chase"
    if "running bal." in headers_lower or "running balance" in headers_lower:
        return "bofa"
    if "description" in headers_lower and "amount" in headers_lower:
        return "generic"
    return "unknown"


def parse_chase_csv(content: str) -> list[dict]:
    """Parse Chase bank/credit card CSV export."""
    transactions = []
    reader = csv.DictReader(io.StringIO(content))
    hash_counts = {}  # Track duplicates within file

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

        # Chase: negative = expense, positive = income/credit
        kind = "expense" if amount < 0 else "income"
        amount = abs(amount)

        if amount == 0:
            continue

        # Generate unique hash, handling duplicates within file
        base_key = f"{tx_date.isoformat()}|{amount:.2f}|{description}"
        counter = hash_counts.get(base_key, 0)
        hash_counts[base_key] = counter + 1

        transactions.append({
            "date": tx_date,
            "description": description,
            "amount": amount,
            "kind": kind,
            "import_hash": generate_import_hash(tx_date, amount, description, counter),
        })

    return transactions


def parse_bofa_csv(content: str) -> list[dict]:
    """Parse Bank of America CSV export."""
    transactions = []
    reader = csv.DictReader(io.StringIO(content))
    hash_counts = {}  # Track duplicates within file

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

        # BOFA: negative = expense, positive = income/credit
        kind = "expense" if amount < 0 else "income"
        amount = abs(amount)

        if amount == 0:
            continue

        # Generate unique hash, handling duplicates within file
        base_key = f"{tx_date.isoformat()}|{amount:.2f}|{description}"
        counter = hash_counts.get(base_key, 0)
        hash_counts[base_key] = counter + 1

        transactions.append({
            "date": tx_date,
            "description": description,
            "amount": amount,
            "kind": kind,
            "import_hash": generate_import_hash(tx_date, amount, description, counter),
        })

    return transactions


def parse_csv_statement(content: str) -> tuple[list[dict], str]:
    """Parse CSV and return transactions with detected format."""
    # Read first line to detect format
    first_line = content.split("\n")[0]
    headers = [h.strip() for h in first_line.split(",")]

    fmt = detect_csv_format(headers)

    if fmt == "chase":
        return parse_chase_csv(content), "Chase"
    elif fmt == "bofa":
        return parse_bofa_csv(content), "Bank of America"
    else:
        # Try generic parsing
        return parse_chase_csv(content), "Generic"


def parse_excel_statement(content: bytes) -> tuple[list[dict], str]:
    """Parse Excel file and return transactions with detected format."""
    transactions = []

    try:
        df = pd.read_excel(io.BytesIO(content), engine='openpyxl')
    except Exception:
        return [], "Unknown"

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
        return [], "Unknown"

    # Detect bank format
    bank_format = "Excel"
    cols_str = " ".join(df.columns)
    if 'posting' in cols_str or 'post date' in cols_str:
        bank_format = "Chase (Excel)"
    elif 'running' in cols_str:
        bank_format = "Bank of America (Excel)"

    hash_counts = {}  # Track duplicates within file

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

            # Determine kind
            kind = "expense" if amount < 0 else "income"
            amount = abs(amount)

            if amount == 0:
                continue

            # Generate unique hash, handling duplicates within file
            base_key = f"{tx_date.isoformat()}|{amount:.2f}|{description}"
            counter = hash_counts.get(base_key, 0)
            hash_counts[base_key] = counter + 1

            transactions.append({
                "date": tx_date,
                "description": description,
                "amount": amount,
                "kind": kind,
                "import_hash": generate_import_hash(tx_date, amount, description, counter),
            })
        except Exception:
            continue

    return transactions, bank_format


def parse_statement(content: bytes, filename: str) -> tuple[list[dict], str]:
    """Parse statement file (CSV or Excel) and return transactions."""
    filename_lower = filename.lower()

    if filename_lower.endswith(('.xlsx', '.xls')):
        return parse_excel_statement(content)
    else:
        # Try CSV
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1")
        return parse_csv_statement(text)


def import_transactions(db: Session, transactions: list[dict], account_id: int, use_ai: bool = False) -> dict:
    """Import parsed transactions into the database."""
    imported = 0
    skipped = 0
    ai_categorized = 0
    rule_categorized = 0

    # Get existing import hashes to avoid duplicates
    existing_hashes = set(
        h for (h,) in db.execute(
            select(Transaction.import_hash)
            .where(Transaction.user_id == USER_ID, Transaction.import_hash.isnot(None))
        ).all()
    )

    # Track hashes in current batch to handle duplicates within same file
    batch_hashes = set()

    # Get categories for AI
    categories = get_category_list(db) if use_ai else []

    for tx in transactions:
        import_hash = tx["import_hash"]

        # Skip if already in database
        if import_hash in existing_hashes:
            skipped += 1
            continue

        # Skip if duplicate within current batch
        if import_hash in batch_hashes:
            skipped += 1
            continue

        batch_hashes.add(import_hash)

        # Auto-categorize with rules first
        amount_cents = to_cents(tx["amount"])
        rule = categorize(db, tx["description"], amount_cents, account_id)
        category_id = rule.category_id if rule else None

        if rule:
            rule_categorized += 1
        elif use_ai and tx["kind"] == "expense" and category_id is None:
            # Try AI categorization
            ai_cat_id = ai_categorize_single(tx["description"], categories)
            if ai_cat_id:
                category_id = ai_cat_id
                ai_categorized += 1

        t = Transaction(
            user_id=USER_ID,
            date=tx["date"],
            kind=tx["kind"],
            amount_cents=amount_cents,
            account_id=account_id,
            category_id=category_id if tx["kind"] == "expense" else None,
            merchant=tx["description"][:200],
            note="",
            is_business=False,
            import_hash=tx["import_hash"],
        )
        db.add(t)
        imported += 1

    db.commit()
    return {
        "imported": imported,
        "skipped": skipped,
        "rule_categorized": rule_categorized,
        "ai_categorized": ai_categorized,
    }
