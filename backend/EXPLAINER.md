# EXPLAINER.md

## 1. The Ledger

**Balance calculation:**
```python
result = self.ledger_entries.aggregate(
    total_credits=Sum('amount', filter=Q(entry_type='credit')),
    total_debits=Sum('amount', filter=Q(entry_type='debit')),
)
balance = (result['total_credits'] or 0) - (result['total_debits'] or 0)
```

Credits and debits are immutable append-only rows in `LedgerEntry`. Balance is never stored as a mutable field — it's always derived. This means there's no way to corrupt the balance; the source of truth is always the ledger.

A debit entry is only written when a payout reaches `completed`. A failed payout writes no debit — funds are automatically available again because `held = sum of pending/processing payouts` and a failed payout is excluded from that sum. No compensating transactions needed.

All amounts are `BigIntegerField` in paise. No floats anywhere. `1000` means ₹10.00.

---

## 2. The Lock

```python
with transaction.atomic():
    merchant_locked = Merchant.objects.select_for_update().get(id=merchant_id)
    balance_data = merchant_locked.get_available_balance()

    if balance_data['available_paise'] < amount_paise:
        return Response({'error': 'Insufficient balance'}, status=422)

    payout = Payout.objects.create(...)
```

`select_for_update()` issues `SELECT ... FOR UPDATE` in PostgreSQL. This acquires a row-level exclusive lock on the merchant row. The second concurrent request blocks at the database level — not Python — until the first transaction commits. Only then does it acquire the lock and re-read the balance, which now correctly reflects the first payout being held. This makes the check-then-deduct atomic.

Python-level locks (threading.Lock, etc.) would fail under multiple processes/workers. Only database-level locking is correct here.

---

## 3. The Idempotency

Three layers of protection:

**Layer 1 (fast path):** Before acquiring any lock, query for existing payout with this `(merchant, idempotency_key)`. If found and within 24h, return immediately — HTTP 200.

**Layer 2 (inside lock):** After acquiring `select_for_update`, check again. This handles the race where two identical requests both pass Layer 1 simultaneously. The second one now sees the first's payout and returns it.

**Layer 3 (database constraint):** `unique_together = [('merchant', 'idempotency_key')]` on the Payout model. If somehow both requests slip through Layer 1 and Layer 2, the database rejects the second INSERT with `IntegrityError`. We catch this and return the existing payout.

Keys are scoped per merchant and expire after 24 hours (checked in application logic).

---

## 4. The State Machine

Illegal transitions are blocked in `Payout.transition_to()`:

```python
VALID_TRANSITIONS = {
    'pending':    ['processing'],
    'processing': ['completed', 'failed'],
    'completed':  [],  # terminal
    'failed':     [],  # terminal
}

def transition_to(self, new_status):
    allowed = self.VALID_TRANSITIONS.get(self.status, [])
    if new_status not in allowed:
        raise ValueError(f"Illegal transition: {self.status} → {new_status}")
    self.status = new_status
```

`completed` and `failed` map to empty lists. Any transition out of them raises `ValueError`. This check lives on the model — not in view logic — so every code path that touches payout status is protected regardless of how it's called.

Fund return on failure is atomic with the state transition because: no debit `LedgerEntry` is ever written for a failed payout. Since `available = credits - debits - held`, and a failed payout is excluded from `held`, the funds become available the moment the status becomes `failed` within the same transaction.

---

## 5. The AI Audit

**What AI generated:**
```python
# Summing balance in Python — WRONG
entries = LedgerEntry.objects.filter(merchant=merchant)
balance = sum(e.amount if e.entry_type == 'credit' else -e.amount for e in entries)
```

**Why it's wrong:** This fetches every ledger row into Python memory and iterates. For a merchant with 50,000 transactions this is a full table scan. Worse — it has a consistency window: rows can be inserted between the fetch and the sum, giving a stale balance. Under concurrent load this becomes a real bug.

**What I replaced it with:**
```python
result = self.ledger_entries.aggregate(
    total_credits=Sum('amount', filter=Q(entry_type='credit')),
    total_debits=Sum('amount', filter=Q(entry_type='debit')),
)
balance = (result['total_credits'] or 0) - (result['total_debits'] or 0)
```

One SQL query, computed in the database, consistent within the transaction. O(1) network round trips regardless of ledger size.
