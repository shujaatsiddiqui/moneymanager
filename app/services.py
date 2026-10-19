import re
from collections import defaultdict
from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import USER_ID, Account, Budget, Category, Rule, Transaction

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
