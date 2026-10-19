"""Streamlit front end. It only talks to the FastAPI backend, so a mobile app can reuse the same API."""
import os
from datetime import date

import pandas as pd
import requests
import streamlit as st

API = os.getenv("API_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Money Manager", page_icon="💰", layout="wide")


def call(method, path, **kw):
    try:
        r = requests.request(method, f"{API}{path}", timeout=10, **kw)
    except requests.ConnectionError:
        st.error(f"Can't reach the API at {API}. Start it with: uvicorn app.main:app --reload")
        st.stop()
    if r.status_code >= 400:
        try:
            detail = r.json().get("detail", r.text)
        except ValueError:
            detail = r.text
        st.error(f"{r.status_code}: {detail}")
        return None
    return r.json()


def money(x):
    return f"${x:,.2f}" if x >= 0 else f"-${abs(x):,.2f}"


def month_options(n=18):
    t, out = date.today(), []
    y, m = t.year, t.month
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    return out


def label(c):
    return f"{c['emoji']} {c['name']}".strip()


def category_picker(cats, key, optional=True):
    """Two-level picker. Returns the subcategory id if chosen, else the parent id."""
    parents = {label(c): c for c in cats}
    names = ([""] if optional else []) + list(parents)
    p = st.selectbox("Category", names, key=f"{key}_p")
    if not p:
        return None
    parent = parents[p]
    subs = {k["name"]: k["id"] for k in parent["children"]}
    s = st.selectbox("Subcategory", [""] + list(subs), key=f"{key}_s")
    return subs[s] if s else parent["id"]


page = st.sidebar.radio("Money Manager", ["Dashboard", "Add transaction", "Transactions",
                                          "Budgets", "Rules", "Accounts"])
month = st.sidebar.selectbox("Month", month_options())
cats = call("get", "/categories") or []
acc_data = call("get", "/accounts") or {"accounts": []}
accounts = acc_data["accounts"]
acc_by_name = {a["name"]: a["id"] for a in accounts}

# ------------------------------------------------------------------ Dashboard
if page == "Dashboard":
    st.title(f"Budget · {month}")
    s = call("get", "/budgets/status", params={"month": month})
    if s:
        c1, c2, c3 = st.columns(3)
        c1.metric("Budgeted", money(s["total_limit"]))
        c2.metric("Spent", money(s["total_spent"]))
        c3.metric("Left to spend", money(s["total_left"]))
        if not s["rows"]:
            st.info("No budgets for this month yet. Set them on the Budgets page.")
        for r in s["rows"]:
            pct = (r["spent"] / r["limit"]) if r["limit"] else 1.0
            left = f"{money(r['left'])} left" if r["left"] >= 0 else f"⚠️ {money(-r['left'])} over"
            st.write(f"**{r['emoji']} {r['category']}**  ·  {money(r['spent'])} of {money(r['limit'])}  ·  {left}")
            st.progress(min(max(pct, 0.0), 1.0))
        st.divider()
        d1, d2, d3 = st.columns(3)
        d1.metric("Unbudgeted spending", money(s["unbudgeted_spent"]),
                  help="Spent in categories that have no budget this month")
        d2.metric("Uncategorized", money(s["uncategorized_spent"]),
                  help="Expenses with no category. Fix them on the Transactions page.")
        d3.metric("Excluded (Income Tax, LLC, Loan…)", money(s["excluded_spent"]))

# ------------------------------------------------------------ Add transaction
elif page == "Add transaction":
    st.title("Add transaction")
    kind = st.radio("Type", ["expense", "income", "transfer"], horizontal=True)
    c1, c2 = st.columns(2)
    d = c1.date_input("Date", date.today())
    amount = c2.number_input("Amount", min_value=0.0, step=1.0, format="%.2f")
    acc = st.selectbox("From account" if kind == "transfer" else "Account", list(acc_by_name))
    to_acc = st.selectbox("To account", list(acc_by_name)) if kind == "transfer" else None
    cat_id = category_picker(cats, "add") if kind != "transfer" else None
    merchant = st.text_input("Merchant / description", help="Used by your rules to pick a category automatically")
    note = st.text_input("Note")
    biz = st.checkbox("Business")
    if st.button("Save", type="primary", disabled=amount <= 0):
        body = {"date": d.isoformat(), "kind": kind, "amount": amount, "account_id": acc_by_name[acc],
                "to_account_id": acc_by_name[to_acc] if to_acc else None, "category_id": cat_id,
                "merchant": merchant, "note": note, "is_business": biz}
        r = call("post", "/transactions", json=body)
        if r:
            msg = f"Saved {money(r['amount'])}"
            if r["category"]:
                msg += f" → {r['category']}" + (" (auto)" if r["auto_categorized"] else "")
            st.success(msg)

# --------------------------------------------------------------- Transactions
elif page == "Transactions":
    st.title(f"Transactions · {month}")
    only_unc = st.checkbox("Only uncategorized expenses")
    txs = call("get", "/transactions", params={"month": month, "uncategorized": only_unc}) or []
    if txs:
        df = pd.DataFrame(txs)[["id", "date", "kind", "amount", "account", "to_account", "category", "merchant", "note"]]
        st.dataframe(df, width="stretch", hide_index=True)
        st.subheader("Edit or delete")
        tx_id = st.selectbox("Transaction", [t["id"] for t in txs],
                             format_func=lambda i: next(f"{t['date']} · {money(t['amount'])} · {t['merchant'] or t['note'] or t['kind']}"
                                                        for t in txs if t["id"] == i))
        cat = category_picker(cats, "edit")
        b1, b2 = st.columns(2)
        if b1.button("Set category", disabled=cat is None):
            if call("patch", f"/transactions/{tx_id}", json={"category_id": cat}):
                st.rerun()
        if b2.button("Delete", type="secondary"):
            if call("delete", f"/transactions/{tx_id}"):
                st.rerun()
    else:
        st.info("Nothing here.")

# -------------------------------------------------------------------- Budgets
elif page == "Budgets":
    st.title(f"Budgets · {month}")
    status = call("get", "/budgets/status", params={"month": month}) or {"rows": []}
    current = {r["category_id"]: r["limit"] for r in status["rows"]}
    rows = [{"id": c["id"], "Category": label(c), "Limit": current.get(c["id"], 0.0)}
            for c in cats if not c["exclude_from_budget"]]
    edited = st.data_editor(pd.DataFrame(rows), hide_index=True, width="stretch",
                            disabled=["id", "Category"], column_config={"id": None,
                            "Limit": st.column_config.NumberColumn(min_value=0, step=10, format="$%.2f")})
    c1, c2 = st.columns(2)
    if c1.button("Save budgets", type="primary"):
        for _, row in edited.iterrows():
            old = current.get(int(row["id"]), 0.0)
            if float(row["Limit"]) != old:
                if float(row["Limit"]) > 0:
                    call("put", "/budgets", json={"category_id": int(row["id"]), "month": month,
                                                   "limit": float(row["Limit"])})
                else:
                    call("delete", "/budgets", params={"category_id": int(row["id"]), "month": month})
        st.success("Saved")
        st.rerun()
    opts = [m for m in month_options() if m != month]
    src = c2.selectbox("Copy limits from", opts, index=0)
    if c2.button("Copy"):
        r = call("post", "/budgets/copy", params={"from_month": src, "to_month": month})
        if r:
            st.success(f"Copied {r['copied']} budgets")
            st.rerun()

# ---------------------------------------------------------------------- Rules
elif page == "Rules":
    st.title("Category rules")
    st.caption("If a transaction's merchant/note contains the pattern, it gets that category. "
               "Prefix with re: for a regex. Lower priority numbers run first.")
    rules = call("get", "/rules") or []
    if rules:
        st.dataframe(pd.DataFrame(rules)[["id", "pattern", "category", "priority", "min_amount", "max_amount"]],
                     hide_index=True, width="stretch")
        rid = st.selectbox("Delete rule", [r["id"] for r in rules],
                           format_func=lambda i: next(f"{r['pattern']} → {r['category']}" for r in rules if r["id"] == i))
        if st.button("Delete"):
            if call("delete", f"/rules/{rid}"):
                st.rerun()
    st.subheader("Add rule")
    pattern = st.text_input("Pattern", placeholder="shell")
    cat = category_picker(cats, "rule", optional=False)
    prio = st.number_input("Priority", value=100, step=10)
    if st.button("Add rule", type="primary", disabled=not pattern):
        if call("post", "/rules", json={"pattern": pattern, "category_id": cat, "priority": int(prio)}):
            st.rerun()
    st.divider()
    if st.button("Apply rules to uncategorized transactions"):
        r = call("post", "/rules/apply")
        if r is not None:
            st.success(f"Categorized {r['categorized']} transactions")

# ------------------------------------------------------------------- Accounts
else:
    st.title("Accounts")
    c1, c2, c3 = st.columns(3)
    c1.metric("Assets", money(acc_data["assets"]))
    c2.metric("Liabilities", money(acc_data["liabilities"]))
    c3.metric("Total", money(acc_data["total"]))
    st.dataframe(pd.DataFrame(accounts)[["group", "name", "balance", "opening", "include_in_totals", "is_business"]],
                 hide_index=True, width="stretch")
    st.subheader("Set opening balance")
    st.caption("Enter what the account holds today. For a card, use a negative number for what you owe.")
    name = st.selectbox("Account", list(acc_by_name))
    opening = st.number_input("Opening balance", step=10.0, format="%.2f")
    if st.button("Save opening balance"):
        if call("patch", f"/accounts/{acc_by_name[name]}", json={"opening": opening}):
            st.rerun()
