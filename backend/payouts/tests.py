from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from concurrent.futures import ThreadPoolExecutor
import threading
import uuid

from .models import Merchant, BankAccount, LedgerEntry


def create_test_merchant(name="Test Merchant", balance_paise=100_00):
    merchant = Merchant.objects.create(name=name, email=f"{uuid.uuid4()}@test.com")
    bank = BankAccount.objects.create(
        merchant=merchant,
        account_number="1234567890",
        ifsc_code="HDFC0001234",
        account_holder_name=name,
    )
    LedgerEntry.objects.create(
        merchant=merchant,
        amount=balance_paise,
        entry_type='credit',
        description='Seed credit',
    )
    return merchant, bank


class ConcurrencyTest(TestCase):
    """
    Two simultaneous 60rs requests against 100rs balance.
    Exactly one must succeed, one must fail with 422.
    """
    def test_concurrent_overdraw_prevention(self):
        merchant, bank = create_test_merchant(balance_paise=100_00)  # 100rs
        client = APIClient()
        results = []
        lock = threading.Lock()

        def make_request():
            response = client.post(
                '/api/v1/payouts/',
                data={
                    'merchant_id': str(merchant.id),
                    'amount_paise': 60_00,  # 60rs
                    'bank_account_id': str(bank.id),
                },
                format='json',
                headers={'Idempotency-Key': str(uuid.uuid4())}
            )
            with lock:
                results.append(response.status_code)

        with ThreadPoolExecutor(max_workers=2) as executor:
            executor.submit(make_request)
            executor.submit(make_request)

        success_count = results.count(201)
        fail_count = results.count(422)

        self.assertEqual(success_count, 1, "Exactly one payout should succeed")
        self.assertEqual(fail_count, 1, "Exactly one payout should be rejected")


class IdempotencyTest(TestCase):
    """
    Same idempotency key sent twice must return same response, no duplicate payout.
    """
    def test_same_key_returns_same_response(self):
        merchant, bank = create_test_merchant(balance_paise=100_00)
        client = APIClient()
        key = str(uuid.uuid4())

        def make_request():
            return client.post(
                '/api/v1/payouts/',
                data={
                    'merchant_id': str(merchant.id),
                    'amount_paise': 50_00,
                    'bank_account_id': str(bank.id),
                },
                format='json',
                headers={'Idempotency-Key': key}
            )

        r1 = make_request()
        r2 = make_request()

        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.data['id'], r2.data['id'])  # Same payout, not two

        # Only one payout exists in DB
        from .models import Payout
        count = Payout.objects.filter(merchant=merchant).count()
        self.assertEqual(count, 1)