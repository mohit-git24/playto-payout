import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from payouts.models import Merchant, BankAccount, LedgerEntry

merchants_data = [
    {
        'name': 'Aryan Design Studio',
        'email': 'aryan@aryandesign.in',
        'bank': {'account_number': '50100123456789', 'ifsc': 'HDFC0001234', 'holder': 'Aryan Kapoor'},
        'credits': [
            (250_000_00, 'Payment from Acme Corp USA - Invoice #INV-001'),
            (180_000_00, 'Payment from TechStart Berlin - Invoice #INV-002'),
            (95_000_00,  'Payment from Maple Agency Canada - Invoice #INV-003'),
        ]
    },
    {
        'name': 'Priya Freelance Dev',
        'email': 'priya@priyatech.io',
        'bank': {'account_number': '60200987654321', 'ifsc': 'ICIC0005678', 'holder': 'Priya Sharma'},
        'credits': [
            (320_000_00, 'Contract payment - SaaS Company Singapore'),
            (150_000_00, 'Milestone 2 - UK Fintech Client'),
        ]
    },
    {
        'name': 'Nexus Marketing Agency',
        'email': 'accounts@nexusmarketing.co',
        'bank': {'account_number': '70300456123789', 'ifsc': 'SBIN0002345', 'holder': 'Nexus Marketing Pvt Ltd'},
        'credits': [
            (500_000_00, 'Campaign payment - US E-commerce Client'),
            (200_000_00, 'Retainer fee - Dubai Luxury Brand'),
            (75_000_00,  'Content project - Australian Startup'),
        ]
    },
]

print("Seeding database...")

for data in merchants_data:
    merchant, _ = Merchant.objects.get_or_create(
        email=data['email'],
        defaults={'name': data['name']}
    )
    BankAccount.objects.get_or_create(
        merchant=merchant,
        account_number=data['bank']['account_number'],
        defaults={
            'ifsc_code': data['bank']['ifsc'],
            'account_holder_name': data['bank']['holder'],
        }
    )
    for amount, desc in data['credits']:
        LedgerEntry.objects.get_or_create(
            merchant=merchant,
            description=desc,
            defaults={'amount': amount, 'entry_type': 'credit'}
        )
    bal = merchant.get_available_balance()
    print(f"  {merchant.name}: ₹{bal['available_paise']//100:,} available")

print("Done.")