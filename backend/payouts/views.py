from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from .models import Merchant, Payout, LedgerEntry
from .serializers import PayoutSerializer, MerchantSerializer, LedgerEntrySerializer
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
        idempotency_key = request.headers.get('Idempotency-Key')
        if not idempotency_key:
            return Response(
                {'error': 'Idempotency-Key header required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        merchant_id = request.data.get('merchant_id')
        amount_paise = request.data.get('amount_paise')
        bank_account_id = request.data.get('bank_account_id')

        if not all([merchant_id, amount_paise, bank_account_id]):
            return Response({'error': 'merchant_id, amount_paise, bank_account_id required'}, status=400)

        if int(amount_paise) <= 0:
            return Response({'error': 'amount_paise must be positive'}, status=400)

        try:
            merchant = Merchant.objects.get(id=merchant_id)
        except Merchant.DoesNotExist:
            return Response({'error': 'Merchant not found'}, status=404)

        # Check idempotency key expiry (24 hours)
        existing = Payout.objects.filter(
            merchant=merchant,
            idempotency_key=idempotency_key
        ).first()

        if existing:
            # Key exists — return same response regardless of state
            # But check if key is expired (24h)
            if existing.created_at < timezone.now() - timedelta(hours=24):
                # Expired key — treat as new request
                pass
            else:
                return Response(PayoutSerializer(existing).data, status=status.HTTP_200_OK)

        # CRITICAL: wrap in atomic + SELECT FOR UPDATE to prevent overdraw
        try:
            with transaction.atomic():
                # Lock the merchant row — prevents concurrent transactions
                # from reading stale balance simultaneously
                merchant_locked = Merchant.objects.select_for_update().get(id=merchant_id)
                balance_data = merchant_locked.get_available_balance()

                if balance_data['available_paise'] < int(amount_paise):
                    return Response(
                        {
                            'error': 'Insufficient balance',
                            'available_paise': balance_data['available_paise'],
                            'requested_paise': int(amount_paise),
                        },
                        status=status.HTTP_422_UNPROCESSABLE_ENTITY
                    )

                payout = Payout.objects.create(
                    merchant=merchant_locked,
                    bank_account_id=bank_account_id,
                    amount_paise=int(amount_paise),
                    idempotency_key=idempotency_key,
                    status='pending',
                )

        except Exception as e:
            return Response({'error': str(e)}, status=500)

        # Dispatch to Celery worker AFTER transaction commits
        process_payout.apply_async(args=[str(payout.id)], countdown=2)

        return Response(PayoutSerializer(payout).data, status=status.HTTP_201_CREATED)


class PayoutDetailView(APIView):
    def get(self, request, payout_id):
        try:
            payout = Payout.objects.get(id=payout_id)
        except Payout.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)
        return Response(PayoutSerializer(payout).data)