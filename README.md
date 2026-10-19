# Money Manager

Personal budget tracker. FastAPI + SQLAlchemy + SQLite, Streamlit UI.

## Run
```
pip install -r requirements.txt
./run.sh            # API on :8000, UI on :8501
python -m pytest    # tests
```

Data lives in `moneymanager.db`. Set `DATABASE_URL` to switch to Postgres later.
API docs: http://127.0.0.1:8000/docs

## Notes
- Money is stored as integer cents.
- Budgets on a parent category include its subcategories.
- Transfers (e.g. paying a card) never count as expenses.
- Categories flagged `exclude_from_budget` (Non Budget, Income Tax, LLC, Loan, Business Investment) are kept out of "left to spend".
