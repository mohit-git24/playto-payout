from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction, IntegrityError
from django.utils import timezone
from datetime import timedelta
import uuid

from .models import Merchant, Payout, LedgerEntry, BankAccount
from .serializers import PayoutSerializer, MerchantSerializer, LedgerEntrySerializer, BankAccountSerializer
from .tasks import process_payout


class MerchantDetailView(APIView):
    def get(self, request, merchant_id):
        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({'error': 'Merchant not found'}, status=404)

        balance = merchant.get_available_balance()
        entries = merchant.ledger_entries.all()[:20]
        payouts = merchant.payouts.all()[:20]

        return Response({
            'merchant': MerchantSerializer(merchant).data,
            'balance': balance,
            'ledger_entries': LedgerEntrySerializer(entries, many=True).data,
            'payouts': PayoutSerializer(payouts, many=True).data,
        })


class MerchantListView(APIView):
    def get(self, request):
        merchants = Merchant.objects.all()
        data = []
        for m in merchants:
            balance = m.get_available_balance()
            data.append({**MerchantSerializer(m).data, **balance})
        return Response(data)


class PayoutCreateView(APIView):
    def post(self, request):
        # 1. Validate idempotency key
        idempotency_key = request.headers.get('Idempotency-Key', '').strip()
        if not idempotency_key:
            return Response(
                {'error': 'Idempotency-Key header is required', 'code': 'MISSING_IDEMPOTENCY_KEY'},
                status=400
            )
        try:
            uuid.UUID(idempotency_key)
        except ValueError:
            return Response(
                {'error': 'Idempotency-Key must be a valid UUID v4', 'code': 'INVALID_IDEMPOTENCY_KEY'},
                status=400
            )

        # 2. Validate request body
        merchant_id = request.data.get('merchant_id')
        amount_paise = request.data.get('amount_paise')
        bank_account_id = request.data.get('bank_account_id')

        if not all([merchant_id, amount_paise, bank_account_id]):
            return Response(
                {'error': 'merchant_id, amount_paise, bank_account_id are all required', 'code': 'MISSING_FIELDS'},
                status=400
            )

        try:
            amount_paise = int(amount_paise)
        except (TypeError, ValueError):
            return Response({'error': 'amount_paise must be an integer', 'code': 'INVALID_AMOUNT'}, status=400)

        if amount_paise <= 0:
            return Response({'error': 'amount_paise must be positive', 'code': 'INVALID_AMOUNT'}, status=400)

        # Minimum payout: 100 paise = ₹1
        if amount_paise < 100:
            return Response({'error': 'Minimum payout is ₹1 (100 paise)', 'code': 'BELOW_MINIMUM'}, status=400)

        # 3. Fetch merchant
        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({'error': 'Merchant not found', 'code': 'MERCHANT_NOT_FOUND'}, status=404)

        # 4. Check idempotency BEFORE acquiring lock
        # This fast-path avoids unnecessary DB locking for duplicate requests
        existing = Payout.objects.filter(
            merchant=merchant,
            idempotency_key=idempotency_key
        ).first()

        if existing:
            age = timezone.now() - existing.created_at
            if age <= timedelta(hours=24):
                # Within 24h window — return exact same response
                return Response(PayoutSerializer(existing).data, status=200)
            # Key expired — fall through to create new payout

        # 5. Validate bank account belongs to this merchant
        try:
            bank_account = BankAccount.objects.get(id=bank_account_id, merchant=merchant, is_active=True)
        except BankAccount.DoesNotExist:
            return Response(
                {'error': 'Bank account not found or does not belong to this merchant', 'code': 'INVALID_BANK_ACCOUNT'},
                status=404
            )

        # 6. CRITICAL SECTION — atomic + row-level lock
        # SELECT FOR UPDATE on merchant row serializes all concurrent payout requests
        # for this merchant. The second request blocks here until the first commits.
        # This eliminates the check-then-deduct race condition entirely.
        try:
            with transaction.atomic():
                # Lock the merchant row for the duration of this transaction
                merchant_locked = Merchant.objects.select_for_update().get(id=merchant_id)

                # Re-check idempotency inside the lock
                # Handles the race where two identical requests both pass the fast-path check
                existing_inside = Payout.objects.filter(
                    merchant=merchant_locked,
                    idempotency_key=idempotency_key
                ).first()
                if existing_inside:
                    return Response(PayoutSerializer(existing_inside).data, status=200)

                # Compute balance inside the lock using DB aggregation
                # Never fetch rows and sum in Python — always aggregate in DB
                balance_data = merchant_locked.get_available_balance()
                available = balance_data['available_paise']

                if available < amount_paise:
                    return Response(
                        {
                            'error': 'Insufficient balance',
                            'code': 'INSUFFICIENT_BALANCE',
                            'available_paise': available,
                            'requested_paise': amount_paise,
                            'shortfall_paise': amount_paise - available,
                        },
                        status=422
                    )

                # Create payout — funds are now "held" by virtue of being a pending payout
                # No separate debit entry yet — debit only happens on completion
                payout = Payout.objects.create(
                    merchant=merchant_locked,
                    bank_account=bank_account,
                    amount_paise=amount_paise,
                    idempotency_key=idempotency_key,
                    status='pending',
                )

        except IntegrityError:
            # Database unique constraint caught a race condition at INSERT level
            # Two requests with same key slipped through both idempotency checks
            # Fetch and return the winner's payout
            existing = Payout.objects.filter(
                merchant=merchant,
                idempotency_key=idempotency_key
            ).first()
            if existing:
                return Response(PayoutSerializer(existing).data, status=200)
            return Response({'error': 'Concurrent request conflict', 'code': 'CONFLICT'}, status=409)

        # 7. Dispatch to Celery AFTER transaction commits
        # If we dispatched inside the transaction, the worker might run before
        # the transaction commits and find no payout to process
        process_payout.apply_async(args=[str(payout.id)], countdown=1)

        return Response(PayoutSerializer(payout).data, status=201)


class PayoutDetailView(APIView):
    def get(self, request, payout_id):
        try:
            payout = Payout.objects.get(id=payout_id)
        except Payout.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        return Response(PayoutSerializer(payout).data)