from contextlib import asynccontextmanager
from datetime import date
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import schemas, services
from .database import Base, SessionLocal, engine, get_db
from .models import USER_ID, Account, Budget, Category, Rule, Transaction
from .seed import seed

MONTH_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed(db)
    yield


app = FastAPI(title="Money Manager API", lifespan=lifespan)


def _get(db: Session, model, id_: int):
    obj = db.get(model, id_)
    if obj is None or obj.user_id != USER_ID:
        raise HTTPException(404, f"{model.__name__} {id_} not found")
    return obj


def _tx_out(db: Session, t: Transaction, auto: bool = False) -> dict:
    cat = db.get(Category, t.category_id) if t.category_id else None
    parent = db.get(Category, cat.parent_id) if cat and cat.parent_id else None
    acc = db.get(Account, t.account_id)
    to_acc = db.get(Account, t.to_account_id) if t.to_account_id else None
    return {
        "id": t.id, "date": t.date.isoformat(), "kind": t.kind,
        "amount": services.from_cents(t.amount_cents),
        "account_id": t.account_id, "account": acc.name if acc else None,
        "to_account_id": t.to_account_id, "to_account": to_acc.name if to_acc else None,
        "category_id": t.category_id,
        "category": (f"{parent.name} > {cat.name}" if parent else cat.name) if cat else None,
        "merchant": t.merchant, "description": t.description, "note": t.note, "is_business": t.is_business,
        "auto_categorized": auto,
    }


# ---------- accounts ----------

@app.get("/accounts")
def list_accounts(db: Session = Depends(get_db)):
    return services.accounts_summary(db)


@app.post("/accounts", status_code=201)
def create_account(body: schemas.AccountIn, db: Session = Depends(get_db)):
    a = Account(user_id=USER_ID, name=body.name, group_name=body.group,
                is_liability=body.is_liability or body.group == "Card",
                opening_cents=services.to_cents(body.opening),
                include_in_totals=body.include_in_totals, is_business=body.is_business,
                account_suffix=body.account_suffix)
    db.add(a)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "An account with that name already exists")
    return {"id": a.id}


@app.patch("/accounts/{account_id}")
def update_account(account_id: int, body: schemas.AccountPatch, db: Session = Depends(get_db)):
    a = _get(db, Account, account_id)
    data = body.model_dump(exclude_unset=True)
    if "opening" in data:
        a.opening_cents = services.to_cents(data.pop("opening"))
    for k, v in data.items():
        setattr(a, k, v)
    db.commit()
    return {"ok": True}


# ---------- categories ----------

@app.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    return services.category_tree(db)


@app.post("/categories", status_code=201)
def create_category(body: schemas.CategoryIn, db: Session = Depends(get_db)):
    if body.parent_id is not None:
        parent = _get(db, Category, body.parent_id)
        if parent.parent_id is not None:
            raise HTTPException(400, "Only two levels are supported (category > subcategory)")
    c = Category(user_id=USER_ID, name=body.name, parent_id=body.parent_id, emoji=body.emoji,
                 exclude_from_budget=body.exclude_from_budget)
    db.add(c)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That category already exists under this parent")
    return {"id": c.id}


@app.patch("/categories/{category_id}")
def update_category(category_id: int, body: schemas.CategoryPatch, db: Session = Depends(get_db)):
    c = _get(db, Category, category_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    db.commit()
    return {"ok": True}


@app.get("/categories/{category_id}/transactions")
def get_category_transactions(category_id: int, db: Session = Depends(get_db)):
    """Get transaction counts for a category and its subcategories."""
    c = _get(db, Category, category_id)
    children = db.scalars(select(Category).where(Category.parent_id == category_id)).all()

    result = []
    # Check parent
    parent_count = db.scalar(
        select(func.count(Transaction.id)).where(Transaction.category_id == category_id)
    ) or 0
    if parent_count > 0:
        result.append({"id": c.id, "name": c.name, "count": parent_count})

    # Check children
    for child in children:
        child_count = db.scalar(
            select(func.count(Transaction.id)).where(Transaction.category_id == child.id)
        ) or 0
        if child_count > 0:
            result.append({"id": child.id, "name": child.name, "count": child_count})

    total = sum(r["count"] for r in result)
    return {"categories": result, "total": total, "child_count": len(children)}


@app.post("/categories/{category_id}/move-transactions")
def move_category_transactions(category_id: int, target_id: int = Query(...), db: Session = Depends(get_db)):
    """Move all transactions from one category (and its children) to another category."""
    source = _get(db, Category, category_id)
    target = _get(db, Category, target_id)

    # Get all category IDs to move from (parent + children)
    children = db.scalars(select(Category).where(Category.parent_id == category_id)).all()
    source_ids = [category_id] + [child.id for child in children]

    # Move transactions
    count = 0
    for tx in db.scalars(select(Transaction).where(Transaction.category_id.in_(source_ids))):
        tx.category_id = target_id
        count += 1

    db.commit()
    return {"moved": count}


@app.delete("/categories/{category_id}/cascade")
def delete_category_cascade(category_id: int, db: Session = Depends(get_db)):
    """Delete a category and all its subcategories (only if none have transactions)."""
    c = _get(db, Category, category_id)
    children = db.scalars(select(Category).where(Category.parent_id == category_id)).all()

    # Check if parent or any child has transactions
    all_ids = [category_id] + [child.id for child in children]
    tx_count = db.scalar(
        select(func.count(Transaction.id)).where(Transaction.category_id.in_(all_ids))
    )
    if tx_count and tx_count > 0:
        raise HTTPException(400, f"Cannot delete: category or subcategories have {tx_count} transactions. Reassign them first.")

    # Delete budgets and rules for all
    for cat_id in all_ids:
        for b in db.scalars(select(Budget).where(Budget.category_id == cat_id)):
            db.delete(b)
        for r in db.scalars(select(Rule).where(Rule.category_id == cat_id)):
            db.delete(r)

    # Delete children first, then parent
    for child in children:
        db.delete(child)
    db.delete(c)
    db.commit()
    return {"ok": True, "deleted": len(all_ids)}


@app.delete("/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    c = _get(db, Category, category_id)
    # Check if category has children
    children = db.scalars(select(Category).where(Category.parent_id == category_id)).all()
    if children:
        # Check if any child has transactions
        child_ids = [child.id for child in children]
        child_tx_count = db.scalar(
            select(func.count(Transaction.id)).where(Transaction.category_id.in_(child_ids))
        )
        if child_tx_count and child_tx_count > 0:
            raise HTTPException(400, f"Cannot delete: subcategories have {child_tx_count} transactions. Reassign them first.")
        raise HTTPException(400, f"Cannot delete category with {len(children)} subcategories. Delete subcategories first.")
    # Check if category has transactions
    tx_count = db.scalar(
        select(func.count(Transaction.id)).where(Transaction.category_id == category_id)
    )
    if tx_count and tx_count > 0:
        raise HTTPException(400, f"Cannot delete category with {tx_count} transactions. Reassign them first.")
    # Delete any budgets for this category
    for b in db.scalars(select(Budget).where(Budget.category_id == category_id)):
        db.delete(b)
    # Delete any rules for this category
    for r in db.scalars(select(Rule).where(Rule.category_id == category_id)):
        db.delete(r)
    db.delete(c)
    db.commit()
    return {"ok": True}


# ---------- budgets ----------

@app.get("/budgets/status")
def budget_status(month: str = Query(pattern=MONTH_PATTERN), db: Session = Depends(get_db)):
    return services.budget_status(db, month)


@app.put("/budgets")
def set_budget(body: schemas.BudgetIn, db: Session = Depends(get_db)):
    _get(db, Category, body.category_id)
    b = db.scalars(select(Budget).where(Budget.user_id == USER_ID, Budget.category_id == body.category_id,
                                        Budget.month == body.month)).first()
    cents = services.to_cents(body.limit)
    if b is None:
        b = Budget(user_id=USER_ID, category_id=body.category_id, month=body.month, limit_cents=cents)
        db.add(b)
    else:
        b.limit_cents = cents
    db.commit()
    return {"id": b.id}


@app.delete("/budgets")
def delete_budget(category_id: int, month: str = Query(pattern=MONTH_PATTERN), db: Session = Depends(get_db)):
    b = db.scalars(select(Budget).where(Budget.user_id == USER_ID, Budget.category_id == category_id,
                                        Budget.month == month)).first()
    if b:
        db.delete(b)
        db.commit()
    return {"ok": True}


@app.post("/budgets/copy")
def copy_budgets(from_month: str = Query(pattern=MONTH_PATTERN),
                 to_month: str = Query(pattern=MONTH_PATTERN), db: Session = Depends(get_db)):
    """Copy last month's limits into a new month (skips categories already budgeted)."""
    src = db.scalars(select(Budget).where(Budget.user_id == USER_ID, Budget.month == from_month)).all()
    have = {b.category_id for b in db.scalars(
        select(Budget).where(Budget.user_id == USER_ID, Budget.month == to_month))}
    n = 0
    for b in src:
        if b.category_id not in have:
            db.add(Budget(user_id=USER_ID, category_id=b.category_id, month=to_month, limit_cents=b.limit_cents))
            n += 1
    db.commit()
    return {"copied": n}


# ---------- transactions ----------

@app.post("/transactions", status_code=201)
def create_transaction(body: schemas.TransactionIn, db: Session = Depends(get_db)):
    _get(db, Account, body.account_id)
    if body.kind == "transfer":
        if body.to_account_id is None:
            raise HTTPException(400, "Transfers need to_account_id")
        if body.to_account_id == body.account_id:
            raise HTTPException(400, "Transfer accounts must differ")
        _get(db, Account, body.to_account_id)
    elif body.to_account_id is not None:
        raise HTTPException(400, "to_account_id is only for transfers")
    cents = services.to_cents(body.amount)
    cat_id, auto = body.category_id, False
    if cat_id is not None:
        _get(db, Category, cat_id)
    elif body.kind == "expense":
        rule = services.categorize(db, f"{body.merchant} {body.note}", cents, body.account_id)
        if rule:
            cat_id, auto = rule.category_id, True
    t = Transaction(user_id=USER_ID, date=body.date, kind=body.kind, amount_cents=cents,
                    account_id=body.account_id, to_account_id=body.to_account_id,
                    category_id=None if body.kind == "transfer" else cat_id,
                    merchant=body.merchant, note=body.note, is_business=body.is_business)
    db.add(t)
    db.commit()
    return _tx_out(db, t, auto)


@app.get("/transactions")
def list_transactions(month: Optional[str] = Query(default=None, pattern=MONTH_PATTERN),
                      account_id: Optional[int] = None, category_id: Optional[int] = None,
                      uncategorized: bool = False, unbudgeted: bool = False,
                      excluded: bool = False, limit: int = Query(500, le=5000),
                      db: Session = Depends(get_db)):
    q = select(Transaction).where(Transaction.user_id == USER_ID)
    if month:
        start, end = services.month_range(month)
        q = q.where(Transaction.date >= start, Transaction.date < end)
    if account_id:
        q = q.where(Transaction.account_id == account_id)
    if category_id:
        ids = [category_id] + [c.id for c in db.scalars(select(Category).where(Category.parent_id == category_id))]
        q = q.where(Transaction.category_id.in_(ids))
    if uncategorized:
        q = q.where(Transaction.kind == "expense", Transaction.category_id.is_(None))
    if unbudgeted and month:
        # Get budgeted category IDs for this month
        budgeted_ids = services.get_budgeted_category_ids(db, month)
        excluded_ids = services.get_excluded_category_ids(db)
        q = q.where(
            Transaction.kind == "expense",
            Transaction.category_id.isnot(None),
            Transaction.category_id.notin_(budgeted_ids),
            Transaction.category_id.notin_(excluded_ids)
        )
    if excluded:
        excluded_ids = services.get_excluded_category_ids(db)
        q = q.where(Transaction.kind == "expense", Transaction.category_id.in_(excluded_ids))
    q = q.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(limit)
    return [_tx_out(db, t) for t in db.scalars(q)]


@app.patch("/transactions/{tx_id}")
def update_transaction(tx_id: int, body: schemas.TransactionPatch, db: Session = Depends(get_db)):
    t = _get(db, Transaction, tx_id)
    data = body.model_dump(exclude_unset=True)

    # Handle amount conversion
    if "amount" in data:
        t.amount_cents = services.to_cents(data.pop("amount"))

    # Handle kind change
    if "kind" in data:
        new_kind = data.pop("kind")
        if new_kind == "transfer":
            # Transfers require to_account_id
            to_acc_id = data.get("to_account_id")
            if not to_acc_id:
                raise HTTPException(400, "Transfers require to_account_id")
            if to_acc_id == t.account_id:
                raise HTTPException(400, "Transfer accounts must differ")
            _get(db, Account, to_acc_id)
            t.category_id = None  # Transfers don't have categories
        else:
            # If changing from transfer to expense/income, clear to_account_id
            if t.kind == "transfer":
                t.to_account_id = None
        t.kind = new_kind

    for k, v in data.items():
        setattr(t, k, v)

    db.commit()
    return _tx_out(db, t)


@app.delete("/transactions/{tx_id}")
def delete_transaction(tx_id: int, db: Session = Depends(get_db)):
    db.delete(_get(db, Transaction, tx_id))
    db.commit()
    return {"ok": True}


# ---------- import ----------

@app.get("/import/ai-status")
def ai_status():
    """Check if Ollama AI is available for categorization."""
    available = services.check_ollama_available()
    return {"available": available, "model": services.OLLAMA_MODEL}


@app.post("/import")
async def import_statement(
    files: list[UploadFile] = File(...),
    account_id: Optional[int] = Form(None),
    use_ai: bool = Form(False),
    auto_detect_account: bool = Form(True),
    db: Session = Depends(get_db)
):
    """Import transactions from CSV/Excel bank statements (Chase or Bank of America).
    Supports multiple files. Can auto-detect account from file content."""
    results = []

    for file in files:
        content = await file.read()
        filename = file.filename or "statement.csv"

        # Try to detect account from file content and filename
        detected_account_id = None
        if auto_detect_account:
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1")
            detected_account_id = services.detect_account_from_content(db, text, filename)

        # Use detected account, or fall back to provided account_id
        target_account_id = detected_account_id or account_id

        if not target_account_id:
            results.append({
                "filename": filename,
                "error": "Could not detect account. Please select manually or set account suffix.",
                "imported": 0,
            })
            continue

        # Verify account exists
        try:
            acc = _get(db, Account, target_account_id)
        except HTTPException:
            results.append({
                "filename": filename,
                "error": f"Account {target_account_id} not found",
                "imported": 0,
            })
            continue

        transactions, bank_format = services.parse_statement(content, filename)

        if not transactions:
            results.append({
                "filename": filename,
                "error": "No valid transactions found",
                "imported": 0,
            })
            continue

        result = services.import_transactions(db, transactions, target_account_id, use_ai=use_ai)
        result["filename"] = filename
        result["format"] = bank_format
        result["total_in_file"] = len(transactions)
        result["account_id"] = target_account_id
        result["account_name"] = acc.name
        result["auto_detected"] = detected_account_id is not None
        results.append(result)

    # If single file, return flat result for backward compatibility
    if len(results) == 1:
        return results[0]

    return {"files": results, "total_imported": sum(r.get("imported", 0) for r in results)}


@app.post("/import/preview")
async def preview_import(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Preview transactions from a CSV/Excel without importing."""
    content = await file.read()
    filename = file.filename or "statement.csv"

    transactions, bank_format = services.parse_statement(content, filename)

    # Try to detect account from content and filename
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")

    detected_account_id = services.detect_account_from_content(db, text, filename)
    detected_account_name = None
    if detected_account_id:
        acc = db.get(Account, detected_account_id)
        detected_account_name = acc.name if acc else None

    return {
        "filename": filename,
        "format": bank_format,
        "count": len(transactions),
        "detected_account_id": detected_account_id,
        "detected_account_name": detected_account_name,
        "transactions": [
            {
                "date": tx["date"].isoformat(),
                "description": tx["description"],
                "amount": tx["amount"],
                "kind": tx["kind"],
            }
            for tx in transactions[:50]  # Preview first 50
        ]
    }


# ---------- rules ----------

@app.get("/rules")
def list_rules(db: Session = Depends(get_db)):
    out = []
    for r in db.scalars(select(Rule).where(Rule.user_id == USER_ID).order_by(Rule.priority, Rule.id)):
        cat = db.get(Category, r.category_id)
        parent = db.get(Category, cat.parent_id) if cat.parent_id else None
        out.append({"id": r.id, "pattern": r.pattern, "priority": r.priority,
                    "category_id": r.category_id,
                    "category": f"{parent.name} > {cat.name}" if parent else cat.name,
                    "min_amount": services.from_cents(r.min_cents),
                    "max_amount": services.from_cents(r.max_cents), "account_id": r.account_id})
    return out


@app.post("/rules", status_code=201)
def create_rule(body: schemas.RuleIn, db: Session = Depends(get_db)):
    _get(db, Category, body.category_id)
    r = Rule(user_id=USER_ID, pattern=body.pattern, category_id=body.category_id, priority=body.priority,
             min_cents=None if body.min_amount is None else services.to_cents(body.min_amount),
             max_cents=None if body.max_amount is None else services.to_cents(body.max_amount),
             account_id=body.account_id)
    db.add(r)
    db.commit()
    return {"id": r.id}


@app.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    db.delete(_get(db, Rule, rule_id))
    db.commit()
    return {"ok": True}


@app.get("/rules/suggest")
def suggest(text: str, amount: Optional[float] = None, db: Session = Depends(get_db)):
    r = services.categorize(db, text, None if amount is None else services.to_cents(amount))
    return {"category_id": r.category_id if r else None, "rule_id": r.id if r else None}


@app.get("/rules/suggest-pattern")
def suggest_pattern(merchant: str):
    """Use AI to suggest a good rule pattern for a merchant description."""
    pattern = services.ai_suggest_rule_pattern(merchant)
    return {"pattern": pattern}


@app.post("/rules/apply")
def apply_rules(db: Session = Depends(get_db)):
    """Run all rules over expenses that have no category yet."""
    return {"categorized": services.apply_rules_to_uncategorized(db)}


@app.post("/transactions/detect-transfers")
def detect_transfers(db: Session = Depends(get_db)):
    """Scan existing transactions and mark transfers based on description patterns."""
    txs = db.scalars(
        select(Transaction).where(
            Transaction.user_id == USER_ID,
            Transaction.kind.in_(["expense", "income"])
        )
    ).all()

    updated = 0
    for t in txs:
        if services.is_likely_transfer(t.merchant):
            t.kind = "transfer"
            t.category_id = None  # Transfers don't have categories
            updated += 1

    db.commit()
    return {"updated": updated}
