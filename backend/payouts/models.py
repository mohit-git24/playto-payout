from django.db import models
from django.db.models import Sum
import uuid


class Merchant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_available_balance(self):
        """
        Balance = sum of all credits - sum of all debits (completed payouts)
        Held = sum of pending + processing payouts
        Available = balance - held
        ALL done at DB level via aggregation. Never fetch rows and sum in Python.
        """
        from django.db.models import Sum, Q
        result = self.ledger_entries.aggregate(
            total_credits=Sum('amount', filter=Q(entry_type='credit')),
            total_debits=Sum('amount', filter=Q(entry_type='debit')),
        )
        credits = result['total_credits'] or 0
        debits = result['total_debits'] or 0
        balance = credits - debits

        held = self.payouts.filter(
            status__in=['pending', 'processing']
        ).aggregate(total=Sum('amount_paise'))['total'] or 0

        return {
            'balance_paise': balance,
            'held_paise': held,
            'available_paise': balance - held,
        }

    def __str__(self):
        return self.name


class BankAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='bank_accounts')
    account_number = models.CharField(max_length=20)
    ifsc_code = models.CharField(max_length=11)
    account_holder_name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.account_holder_name} - {self.account_number}"


class LedgerEntry(models.Model):
    ENTRY_TYPES = [('credit', 'Credit'), ('debit', 'Debit')]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='ledger_entries')
    amount = models.BigIntegerField()  # always paise, always positive
    entry_type = models.CharField(max_length=10, choices=ENTRY_TYPES)
    description = models.CharField(max_length=500)
    reference_id = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.entry_type} {self.amount} for {self.merchant.name}"


class Payout(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    # Valid transitions — illegal ones get rejected
    VALID_TRANSITIONS = {
        'pending': ['processing'],
        'processing': ['completed', 'failed'],
        'completed': [],   # terminal
        'failed': [],      # terminal
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    merchant = models.ForeignKey(Merchant, on_delete=models.CASCADE, related_name='payouts')
    bank_account = models.ForeignKey(BankAccount, on_delete=models.PROTECT)
    amount_paise = models.BigIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    idempotency_key = models.CharField(max_length=255)
    attempt_count = models.IntegerField(default=0)
    processing_started_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    failure_reason = models.CharField(max_length=500, blank=True)

    class Meta:
        # One idempotency key per merchant
        unique_together = [('merchant', 'idempotency_key')]
        ordering = ['-created_at']

    def transition_to(self, new_status):
        """
        Enforces the state machine at the model level.
        Every code path that changes payout status MUST go through here.
        This means illegal transitions are impossible regardless of caller.
        """
        allowed = self.VALID_TRANSITIONS.get(self.status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Illegal state transition: {self.status} → {new_status}. "
                f"Allowed from '{self.status}': {allowed or 'none (terminal state)'}"
            )
        self.status = new_status

    def __str__(self):
        return f"Payout {self.id} - {self.status}"