MONTH = "2026-10"


def cat_id(client, parent, sub=None):
    for c in client.get("/categories").json():
        if c["name"] == parent:
            if sub is None:
                return c["id"]
            return next(k["id"] for k in c["children"] if k["name"] == sub)
    raise AssertionError(parent)


def acct(client, name):
    return next(a for a in client.get("/accounts").json()["accounts"] if a["name"] == name)


def status(client):
    return client.get("/budgets/status", params={"month": MONTH}).json()


def test_seed_loaded(client):
    cats = client.get("/categories").json()
    assert len(cats) >= 30
    assert len(next(c for c in cats if c["name"] == "Bill Payment")["children"]) == 23
    # same subcategory name under different parents
    assert cat_id(client, "Transport", "Car") != cat_id(client, "Insurance", "Car")
    assert {a["name"] for a in client.get("/accounts").json()["accounts"]} >= {"BOFA", "Chase CC", "Apple Card"}


def test_budget_left_with_subcategories(client):
    food = cat_id(client, "Food & Outing")
    client.put("/budgets", json={"category_id": food, "month": MONTH, "limit": 500})
    chk = acct(client, "Chase Checking")["id"]
    for sub, amt in [("Lunch", 120.50), ("Dinner", 80)]:
        r = client.post("/transactions", json={"date": "2026-10-05", "amount": amt, "account_id": chk,
                                               "category_id": cat_id(client, "Food & Outing", sub)})
        assert r.status_code == 201
    row = next(r for r in status(client)["rows"] if r["category"] == "Food & Outing")
    assert row["spent"] == 200.5 and row["left"] == 299.5


def test_other_month_not_counted(client):
    chk = acct(client, "Chase Checking")["id"]
    client.post("/transactions", json={"date": "2026-09-30", "amount": 999, "account_id": chk,
                                       "category_id": cat_id(client, "Food & Outing", "Lunch")})
    row = next(r for r in status(client)["rows"] if r["category"] == "Food & Outing")
    assert row["spent"] == 200.5


def test_transfer_is_not_an_expense_and_moves_balances(client):
    chk, cc = acct(client, "Chase Checking"), acct(client, "Chase CC")
    before = status(client)
    client.post("/transactions", json={"date": "2026-10-06", "kind": "transfer", "amount": 300,
                                       "account_id": chk["id"], "to_account_id": cc["id"]})
    after = status(client)
    assert before["total_spent"] == after["total_spent"]
    assert before["uncategorized_spent"] == after["uncategorized_spent"]
    assert acct(client, "Chase CC")["balance"] == cc["balance"] + 300


def test_card_purchase_increases_debt(client):
    cc = acct(client, "BOFA CC")
    client.post("/transactions", json={"date": "2026-10-07", "amount": 50, "account_id": cc["id"],
                                       "category_id": cat_id(client, "Transport", "Fuel")})
    assert acct(client, "BOFA CC")["balance"] == cc["balance"] - 50


def test_rule_auto_categorizes(client):
    fuel = cat_id(client, "Transport", "Fuel")
    client.post("/rules", json={"pattern": "shell", "category_id": fuel})
    chk = acct(client, "Chase Checking")["id"]
    r = client.post("/transactions", json={"date": "2026-10-08", "amount": 40, "account_id": chk,
                                           "merchant": "SHELL OIL 5744"}).json()
    assert r["category_id"] == fuel and r["auto_categorized"] is True
    assert r["category"] == "Transport > Fuel"


def test_regex_rule_and_amount_filter(client):
    sub = cat_id(client, "Apps", "Chatgpt")
    client.post("/rules", json={"pattern": "re:openai|chatgpt", "category_id": sub,
                                "min_amount": 5, "max_amount": 50})
    chk = acct(client, "Chase Checking")["id"]
    ok = client.post("/transactions", json={"date": "2026-10-09", "amount": 20, "account_id": chk,
                                            "merchant": "OPENAI *CHATGPT SUBSCR"}).json()
    too_big = client.post("/transactions", json={"date": "2026-10-09", "amount": 200, "account_id": chk,
                                                 "merchant": "OPENAI *CHATGPT SUBSCR"}).json()
    assert ok["category_id"] == sub
    assert too_big["category_id"] is None


def test_apply_rules_to_existing(client):
    chk = acct(client, "Chase Checking")["id"]
    client.post("/transactions", json={"date": "2026-10-10", "amount": 33, "account_id": chk,
                                       "merchant": "x"})
    fuel = cat_id(client, "Transport", "Fuel")
    client.post("/rules", json={"pattern": "zzfuelzz", "category_id": fuel})
    client.post("/transactions", json={"date": "2026-10-10", "amount": 10, "account_id": chk,
                                       "merchant": "plain"})
    # nothing matches 'plain'; apply must not crash and returns a count
    assert client.post("/rules/apply").json()["categorized"] >= 0


def test_excluded_categories_do_not_pollute_budget(client):
    chk = acct(client, "Chase Checking")["id"]
    before = status(client)
    client.post("/transactions", json={"date": "2026-10-11", "amount": 1000, "account_id": chk,
                                       "category_id": cat_id(client, "Income Tax")})
    after = status(client)
    assert after["unbudgeted_spent"] == before["unbudgeted_spent"]
    assert after["excluded_spent"] == before["excluded_spent"] + 1000


def test_validation(client):
    chk = acct(client, "Chase Checking")["id"]
    assert client.post("/transactions", json={"date": "2026-10-01", "amount": -5, "account_id": chk}).status_code == 422
    assert client.post("/transactions", json={"date": "2026-10-01", "kind": "transfer", "amount": 5,
                                              "account_id": chk}).status_code == 400
    assert client.get("/budgets/status", params={"month": "2026-13"}).status_code == 422


def test_copy_budgets_and_delete_tx(client):
    n = client.post("/budgets/copy", params={"from_month": MONTH, "to_month": "2026-11"}).json()["copied"]
    assert n >= 1
    tx = client.get("/transactions", params={"month": MONTH}).json()[0]
    assert client.delete(f"/transactions/{tx['id']}").status_code == 200
