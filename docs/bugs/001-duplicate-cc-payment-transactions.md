# BUG-001: Duplicate Credit Card Payment Transactions

**Date:** 2026-11-04
**Status:** Fixed
**Severity:** High
**Component:** Import Service, Transaction Balance Calculation

---

## Summary

Credit card payments were being counted twice in account balances, causing incorrect balance calculations. The same payment appeared as both a `transfer_in` and an `income` transaction.

---

## Bug Description

### Symptoms
- Chase CC account showing incorrect running balance
- Balance inflated by payment amounts (e.g., $5,667.42 counted twice)
- October transactions appearing in November view (secondary issue)

### Example
When viewing Chase CC transactions for October 2026:

| Date | Type | Amount | Description |
|------|------|--------|-------------|
| 2026-10-30 | transfer_in | $5,667.42 | CHASE CREDIT CRD DES:EPAY... |
| 2026-10-29 | income | $5,667.42 | Payment Thank You - Web |

Both records represent the **same credit card payment** but were counted separately, adding $11,334.84 to the balance instead of $5,667.42.

### Root Cause

When importing bank statements from multiple accounts, the same payment creates duplicate records:

1. **BOFA Statement Import:**
   - Transaction: "CHASE CREDIT CRD DES:EPAY ID:..."
   - System correctly detects transfer to Chase CC
   - Creates: `transfer_out` on BOFA + `transfer_in` on Chase CC

2. **Chase CC Statement Import:**
   - Transaction: "Payment Thank You - Web"
   - System did NOT recognize this as a transfer
   - Creates: `income` on Chase CC (DUPLICATE)

The "Payment Thank You" pattern was not in the transfer detection patterns, so it was imported as regular income.

---

## Investigation

### Files Examined

1. `app/infrastructure/parsers/base.py` - Transfer pattern detection
2. `app/domain/services/import_service.py` - Import logic and duplicate detection
3. `app/infrastructure/repositories/transaction_repository.py` - Database queries
4. `frontend/src/pages/Transactions.jsx` - Balance calculation (secondary issue)

### Key Findings

1. **Missing Transfer Pattern:** The `TRANSFER_PATTERNS` list in `base.py` did not include "Payment Thank You" style descriptions that appear on credit card statements.

2. **No Cross-Account Duplicate Detection:** When importing a credit card statement, the system didn't check if a corresponding `transfer_in` already existed from a bank account import.

3. **Secondary Issue - Month Filter Bug:** The transactions page wasn't applying the month filter when an account filter was active, causing October transactions to appear in November view.

---

## Decision

### Options Considered

1. **Manual cleanup only** - Delete duplicates manually each time
   - Rejected: Not sustainable, error-prone

2. **Post-import deduplication** - Run a cleanup job after all imports
   - Rejected: Complex, could accidentally delete legitimate transactions

3. **Import-time duplicate detection** - Detect and skip duplicates during import
   - Selected: Prevents duplicates at the source, cleanest solution

### Solution Design

The fix has two parts:

**Part A: Recognize "Payment Thank You" as a transfer**
- Add pattern to `TRANSFER_PATTERNS` in base parser
- Transactions matching this pattern get `kind="transfer"` during parsing

**Part B: Skip duplicate CC payments during import**
- When importing a transfer-type inflow to a liability account (credit card)
- Check for existing `transfer_in` with same amount within ±3 days
- If found, skip the transaction as a duplicate

---

## Solution Implementation

### Changes Made

#### 1. `app/infrastructure/parsers/base.py`

Added transfer patterns for credit card payment confirmations:

```python
TRANSFER_PATTERNS = [
    # ... existing patterns ...
    # Credit card payment confirmations (on the CC statement side)
    r"PAYMENT THANK YOU",
    r"PAYMENT\s*-\s*THANK YOU",
]
```

#### 2. `app/infrastructure/repositories/transaction_repository.py`

Added method to find existing transfer_in by amount and date range:

```python
def find_transfer_in_by_amount(
    self,
    account_id: int,
    amount_cents: int,
    start_date: date,
    end_date: date
) -> Optional[Transaction]:
    """Find an existing transfer_in to an account within a date range."""
    return self.db.scalars(
        select(Transaction).where(
            Transaction.user_id == self.user_id,
            Transaction.kind == "transfer_in",
            Transaction.account_id == account_id,
            Transaction.amount_cents == amount_cents,
            Transaction.date >= start_date,
            Transaction.date <= end_date
        )
    ).first()
```

#### 3. `app/domain/services/import_service.py`

Added duplicate detection before creating regular transactions:

```python
# Check for duplicate CC payment
if tx.kind == "transfer" and tx.is_inflow and account.is_liability:
    amount_cents = to_cents(tx.amount)
    start = tx.date - timedelta(days=3)
    end = tx.date + timedelta(days=3)
    existing_transfer = self.transaction_repo.find_transfer_in_by_amount(
        account_id, amount_cents, start, end
    )
    if existing_transfer:
        skipped += 1
        continue
```

#### 4. `frontend/src/pages/Transactions.jsx` (Secondary Fix)

Fixed month filter to always apply regardless of account filter:

```javascript
// Before (bug)
if (!accountId) params.month = month

// After (fixed)
params.month = month
```

### Data Cleanup

Deleted existing duplicate transactions:
- ID 188: $5,667.42 on Chase CC (2026-10-30)
- ID 134: $2,328.38 on Chase CC (2026-10-21)
- ID 181: $207.00 on Chase Business CC (2026-10-29)

---

## Testing

### Verification Steps

1. Import BOFA statement with Chase CC payment
2. Import Chase CC statement with "Payment Thank You" for same payment
3. Verify only one transaction appears (the transfer_in)
4. Verify account balance is calculated correctly

### Edge Cases

- Payments on same day: Handled (amount matching)
- Payments 1-3 days apart: Handled (date range ±3 days)
- Multiple payments same amount same week: May need manual review
- Legitimate income that looks like payment: Rare, description must match pattern

---

## Prevention

To prevent similar issues in the future:

1. **Test multi-account imports** - Always test importing from both sides of a transfer
2. **Add patterns promptly** - When new payment description formats are found, add them to `TRANSFER_PATTERNS`
3. **Consider import order** - Import bank accounts before credit cards for best duplicate detection

---

## Related Issues

- Month filter not applied with account filter (fixed in same PR)

---

## Post-Fix Issue: Incorrectly Deleted Transaction

**Date:** 2026-11-04
**Status:** Fixed

### What Happened

During the initial fix, transaction ID 134 ("Payment Thank You - Web" for $2,328.38 on Oct 21) was incorrectly deleted as a "duplicate."

### Why It Was Wrong

The deletion logic assumed that if a `transfer_out` exists from BOFA to Chase CC, there would be a corresponding `transfer_in` on Chase CC. However:

| transfer_out (from BOFA) | transfer_in (on Chase CC) |
|--------------------------|---------------------------|
| ID 224: $5,667.42 (Oct 30) | ID 225: $5,667.42 ✓ Paired |
| ID 157: $2,328.38 (Oct 22) | **MISSING** ✗ |

The `transfer_out` ID 157 was created, but its `transfer_in` counterpart was never created. The "Payment Thank You - Web" (ID 134) was the only record of this payment on the Chase CC side, and deleting it caused a $2,328.38 discrepancy.

### Symptoms

- Chase CC balance showed -$2,465.01
- Statement showed $116.64 owed
- Difference: ~$2,348 (matching the deleted transaction)

### Root Cause Analysis

The original import likely failed to create the transfer pair correctly. When the BOFA statement was imported:
1. System detected "CHASE CREDIT CRD" as a transfer to Chase CC
2. Created `transfer_out` on BOFA (ID 157)
3. **Failed to create** `transfer_in` on Chase CC (unknown reason - possibly a bug in the transfer pair creation)

Later, when Chase CC statement was imported:
1. "Payment Thank You - Web" was imported as `income` (not recognized as transfer at the time)
2. This was the only record of the payment on the CC side

During the bug fix:
1. We deleted ID 134 thinking it duplicated a transfer_in
2. But the transfer_in never existed
3. Result: Payment not reflected on Chase CC balance

### Fix Applied

Created the missing `transfer_in` transaction:
- Account: Chase CC (ID 12)
- Amount: $2,328.38
- Date: 2026-10-22 (matching transfer_out)
- Kind: transfer_in
- To Account: BOFA (ID 2)
- Description: CHASE CREDIT CRD DES:EPAY ID:9813456492

### Lesson Learned

Before deleting "duplicate" transactions:
1. Verify the corresponding transfer_in actually exists
2. Check that transfer pairs are complete (both sides present)
3. Compare calculated balance against statement before and after cleanup

### Prevention

Added to the duplicate detection logic: only skip a "Payment Thank You" transaction if a `transfer_in` with matching amount actually exists in the database (not just a `transfer_out`).
