# EXPLAINER.md

## 1. The Ledger

ok so basically every rupee movement is a row in `LedgerEntry` — either a credit (money came in) or a debit (payout went out). balance is never stored anywhere, its always calculated fresh:

```python
result = self.ledger_entries.aggregate(
    total_credits=Sum('amount', filter=Q(entry_type='credit')),
    total_debits=Sum('amount', filter=Q(entry_type='debit')),
)
balance = (result['total_credits'] or 0) - (result['total_debits'] or 0)
```

why this way? because if you store balance as a column, two requests hitting at the same time can both read ₹100, both subtract ₹60, both think they're fine, and now you've paid out ₹120 from ₹100. with a ledger you just count the rows — theres no way to corrupt it.

also debit only gets written when payout actually completes. if it fails, no debit = money automatically comes back. no reversal code needed.

---

## 2. The Lock

this is the part i actually spent time thinking about:

```python
with transaction.atomic():
    merchant_locked = Merchant.objects.select_for_update().get(id=merchant_id)
    balance_data = merchant_locked.get_available_balance()

    if balance_data['available_paise'] < amount_paise:
        return Response({'error': 'Insufficient balance'}, status=422)

    payout = Payout.objects.create(...)
```

`select_for_update()` tells postgres — lock this row, nobody else touches it until i'm done. so if two requests come in at the same time, the second one literally waits at the database level until the first one finishes. then it reads the balance again and sees the first payout already took the funds.

the key thing — this is a **database** lock not a python lock. python locks break the moment you have multiple workers. postgres lock works across everything.

---

## 3. The Idempotency

three layers because networks are weird and clients retry:

**first check** — before doing anything, just query if this key exists:
```python
existing = Payout.objects.filter(
    merchant=merchant, idempotency_key=idempotency_key
).first()
if existing:
    return Response(PayoutSerializer(existing).data, status=200)
```

**second check** — inside the lock, check again. handles the case where two identical requests both passed the first check at the same time:
```python
existing_inside = Payout.objects.filter(
    merchant=merchant_locked, idempotency_key=idempotency_key
).first()
if existing_inside:
    return Response(PayoutSerializer(existing_inside).data, status=200)
```

**third layer** — database `unique_together` on `(merchant, idempotency_key)`. if somehow both slip through, the second INSERT just fails and we catch the IntegrityError and return the first one.

keys are per merchant, expire after 24h. same key from different merchant = different payout, that's fine.

---

## 4. The State Machine

blocked right here on the model:

```python
VALID_TRANSITIONS = {
    'pending':    ['processing'],
    'processing': ['completed', 'failed'],
    'completed':  [],
    'failed':     [],
}

def transition_to(self, new_status):
    allowed = self.VALID_TRANSITIONS.get(self.status, [])
    if new_status not in allowed:
        raise ValueError(f"Illegal transition: {self.status} → {new_status}")
    self.status = new_status
```

`failed` maps to empty list. trying to go `failed → completed` hits the ValueError immediately, nothing gets saved.

put this on the model not in views so every single place that changes status is automatically protected. can't accidentally bypass it.

---

## 5. The AI Audit

AI gave me this for balance calculation:

```python
# what the AI wrote
entries = LedgerEntry.objects.filter(merchant=merchant)
balance = sum(e.amount if e.entry_type == 'credit' else -e.amount for e in entries)
```

looks fine right? i almost missed it. the problem:

- fetches every single ledger row into python memory. merchant with 50k transactions = 50k rows loaded for no reason
- there's a gap between the fetch and the sum where new rows can sneak in — so the number you get is already wrong
- completely breaks inside a transaction with `select_for_update` because the rows are read outside the lock scope

what i actually used:

```python
result = self.ledger_entries.aggregate(
    total_credits=Sum('amount', filter=Q(entry_type='credit')),
    total_debits=Sum('amount', filter=Q(entry_type='debit')),
)
balance = (result['total_credits'] or 0) - (result['total_debits'] or 0)
```

one query, done in the database, consistent, fast regardless of how many transactions exist.
