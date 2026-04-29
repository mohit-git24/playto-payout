from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import uuid

from .models import Merchant, BankAccount, LedgerEntry, Payout


def setup_merchant(name="Test", balance_paise=100_00):
    merchant = Merchant.objects.create(name=name, email=f"{uuid.uuid4()}@test.com")
    bank = BankAccount.objects.create(
        merchant=merchant,
        account_number="1234567890",
        ifsc_code="HDFC0001234",
        account_holder_name=name,
    )
    LedgerEntry.objects.create(
        merchant=merchant, amount=balance_paise,
        entry_type='credit', description='Test credit'
    )
    return merchant, bank


class ConcurrencyTest(TransactionTestCase):
    """
    Uses TransactionTestCase (not TestCase) because select_for_update
    requires real transactions, not savepoints.
    TestCase wraps everything in one transaction which breaks FOR UPDATE.
    """

    def test_two_concurrent_60rs_against_100rs_balance(self):
        """
        The canonical race condition test.
        Balance: ₹100. Two simultaneous requests for ₹60 each.
        Expected: exactly one 201, exactly one 422. Total held never exceeds balance.
        """
        merchant, bank = setup_merchant(balance_paise=100_00)
        results = []
        lock = threading.Lock()

        def request():
            client = APIClient()
            resp = client.post('/api/v1/payouts/', {
                'merchant_id': str(merchant.id),
                'amount_paise': 60_00,
                'bank_account_id': str(bank.id),
            }, format='json', headers={'Idempotency-Key': str(uuid.uuid4())})
            with lock:
                results.append(resp.status_code)

        with ThreadPoolExecutor(max_workers=2) as ex:
            futures = [ex.submit(request), ex.submit(request)]
            for f in as_completed(futures):
                f.result()

        self.assertEqual(results.count(201), 1, f"Expected 1 success, got {results.count(201)}. Results: {results}")
        self.assertEqual(results.count(422), 1, f"Expected 1 rejection, got {results.count(422)}. Results: {results}")

        # Invariant check: held must not exceed balance
        bal = merchant.get_available_balance()
        self.assertGreaterEqual(bal['available_paise'], 0, "Available balance went negative!")


class IdempotencyTest(TestCase):

    def test_same_key_same_response_no_duplicate(self):
        """
        Same idempotency key sent twice returns same payout ID.
        DB must have exactly 1 payout, not 2.
        """
        merchant, bank = setup_merchant(balance_paise=100_00)
        client = APIClient()
        key = str(uuid.uuid4())
        payload = {
            'merchant_id': str(merchant.id),
            'amount_paise': 50_00,
            'bank_account_id': str(bank.id),
        }

        r1 = client.post('/api/v1/payouts/', payload, format='json', headers={'Idempotency-Key': key})
        r2 = client.post('/api/v1/payouts/', payload, format='json', headers={'Idempotency-Key': key})

        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.data['id'], r2.data['id'], "Duplicate payout created!")
        self.assertEqual(Payout.objects.filter(merchant=merchant).count(), 1)

    def test_different_keys_create_different_payouts(self):
        merchant, bank = setup_merchant(balance_paise=200_00)
        client = APIClient()
        payload = {
            'merchant_id': str(merchant.id),
            'amount_paise': 50_00,
            'bank_account_id': str(bank.id),
        }

        r1 = client.post('/api/v1/payouts/', payload, format='json', headers={'Idempotency-Key': str(uuid.uuid4())})
        r2 = client.post('/api/v1/payouts/', payload, format='json', headers={'Idempotency-Key': str(uuid.uuid4())})

        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 201)
        self.assertNotEqual(r1.data['id'], r2.data['id'])
        self.assertEqual(Payout.objects.filter(merchant=merchant).count(), 2)


class StateMachineTest(TestCase):

    def test_illegal_transitions_raise(self):
        merchant, bank = setup_merchant()
        payout = Payout.objects.create(
            merchant=merchant, bank_account=bank,
            amount_paise=10_00, idempotency_key=str(uuid.uuid4()),
            status='completed'
        )
        with self.assertRaises(ValueError):
            payout.transition_to('pending')
        with self.assertRaises(ValueError):
            payout.transition_to('failed')

        payout.status = 'failed'
        with self.assertRaises(ValueError):
            payout.transition_to('completed')

    def test_legal_transitions_work(self):
        merchant, bank = setup_merchant()
        payout = Payout.objects.create(
            merchant=merchant, bank_account=bank,
            amount_paise=10_00, idempotency_key=str(uuid.uuid4()),
        )
        payout.transition_to('processing')
        self.assertEqual(payout.status, 'processing')
        payout.transition_to('completed')
        self.assertEqual(payout.status, 'completed')


class BalanceIntegrityTest(TestCase):

    def test_balance_never_goes_negative(self):
        """The core ledger invariant: credits - debits = balance always."""
        merchant, bank = setup_merchant(balance_paise=100_00)
        bal = merchant.get_available_balance()
        self.assertEqual(bal['balance_paise'], 100_00)
        self.assertEqual(bal['available_paise'], 100_00)
        self.assertEqual(bal['held_paise'], 0)

    def test_held_reduces_available(self):
        merchant, bank = setup_merchant(balance_paise=100_00)
        Payout.objects.create(
            merchant=merchant, bank_account=bank,
            amount_paise=40_00, idempotency_key=str(uuid.uuid4()),
            status='pending'
        )
        bal = merchant.get_available_balance()
        self.assertEqual(bal['balance_paise'], 100_00)
        self.assertEqual(bal['held_paise'], 40_00)
        self.assertEqual(bal['available_paise'], 60_00)