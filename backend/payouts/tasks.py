import random
import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_payout(self, payout_id):
    from .models import Payout, LedgerEntry

    try:
        with transaction.atomic():
            # Lock this specific payout row
            payout = Payout.objects.select_for_update().get(id=payout_id)

            # Only process if still pending
            if payout.status != 'pending':
                logger.info(f"Payout {payout_id} already {payout.status}, skipping")
                return

            # Move to processing
            payout.transition_to('processing')
            payout.attempt_count += 1
            payout.processing_started_at = timezone.now()
            payout.save()

        # Simulate bank API call OUTSIDE the transaction
        # so we don't hold the lock during I/O
        outcome = random.random()

        with transaction.atomic():
            payout = Payout.objects.select_for_update().get(id=payout_id)

            if payout.status != 'processing':
                return  # Something else changed it

            if outcome < 0.70:
                # SUCCESS
                payout.transition_to('completed')
                payout.save()

                # Write debit ledger entry — funds are now gone
                LedgerEntry.objects.create(
                    merchant=payout.merchant,
                    amount=payout.amount_paise,
                    entry_type='debit',
                    description=f'Payout to bank account',
                    reference_id=str(payout.id),
                )
                logger.info(f"Payout {payout_id} completed")

            elif outcome < 0.90:
                # FAILURE — return funds (no debit entry needed, held is released)
                payout.transition_to('failed')
                payout.failure_reason = 'Bank rejected the transfer'
                payout.save()
                logger.info(f"Payout {payout_id} failed, funds returned")

            else:
                # STUCK in processing — will be picked up by retry_stuck_payouts
                logger.info(f"Payout {payout_id} hung in processing")

    except Exception as exc:
        logger.error(f"Error processing payout {payout_id}: {exc}")
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@shared_task
def retry_stuck_payouts():
    """
    Runs every 30s via Celery Beat.
    Finds payouts stuck in processing > 30s and retries them.
    Max 3 attempts then mark failed.
    """
    from .models import Payout, LedgerEntry

    cutoff = timezone.now() - timedelta(seconds=30)
    stuck_payouts = Payout.objects.filter(
        status='processing',
        processing_started_at__lt=cutoff,
    )

    for payout in stuck_payouts:
        with transaction.atomic():
            # Re-fetch with lock
            p = Payout.objects.select_for_update().get(id=payout.id)

            if p.status != 'processing':
                continue

            if p.attempt_count >= 3:
                # Max retries hit — fail it and return funds
                p.transition_to('failed')
                p.failure_reason = 'Max retries exceeded — bank timeout'
                p.save()
                logger.info(f"Payout {p.id} failed after max retries")
            else:
                # Reset to pending for retry with exponential backoff
                p.status = 'pending'
                p.processing_started_at = None
                p.save()

                countdown = 2 ** p.attempt_count  # 2, 4, 8 seconds
                process_payout.apply_async(args=[str(p.id)], countdown=countdown)
                logger.info(f"Retrying payout {p.id}, attempt {p.attempt_count + 1}")