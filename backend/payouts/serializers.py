from rest_framework import serializers
from .models import Merchant, Payout, LedgerEntry, BankAccount


class BankAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankAccount
        fields = ['id', 'account_number', 'ifsc_code', 'account_holder_name']


class MerchantSerializer(serializers.ModelSerializer):
    bank_accounts = BankAccountSerializer(many=True, read_only=True)

    class Meta:
        model = Merchant
        fields = ['id', 'name', 'email', 'created_at', 'bank_accounts']


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ['id', 'amount', 'entry_type', 'description', 'reference_id', 'created_at']


class PayoutSerializer(serializers.ModelSerializer):
    bank_account = BankAccountSerializer(read_only=True)

    class Meta:
        model = Payout
        fields = [
            'id', 'merchant', 'bank_account', 'amount_paise',
            'status', 'idempotency_key', 'attempt_count',
            'failure_reason', 'created_at', 'updated_at'
        ]