import random
import logging
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

logger = logging.getLogger(__name__)

# Simulated bank response times in seconds
BANK_PROCESSING_DELAY = 2


@shared_task(bind=True, max_retries=3, default_retry_delay=5)
def process_payout(self, payout_id):
    """
    Processes a single payout through the bank settlement simulation.

    State machine enforced here:
    - pending -> processing (start)
    - processing -> completed (70% chance) + write debit ledger entry
    - processing -> failed (20% chance) + funds released (no debit entry)
    - processing -> stays processing (10% chance) = will be retried by beat

    CRITICAL: debit ledger entry and status transition happen atomically.
    A failed transition never leaves a partial debit.
    """
    from .models import Payout, LedgerEntry

    logger.info(f"[PAYOUT {payout_id}] Worker received task")

    try:
        # Step 1: Move to processing atomically
        with transaction.atomic():
            try:
                payout = Payout.objects.select_for_update(nowait=True).get(id=payout_id)
            except Payout.DoesNotExist:
                logger.error(f"[PAYOUT {payout_id}] Not found in DB")
                return
            except Exception:
                # Another worker has this row locked — skip
                logger.warning(f"[PAYOUT {payout_id}] Row locked by another worker, skipping")
                return

            if payout.status != 'pending':
                logger.info(f"[PAYOUT {payout_id}] Already {payout.status}, skipping")
                return

            # Enforce state machine
            payout.transition_to('processing')
            payout.attempt_count += 1
            payout.processing_started_at = timezone.now()
            payout.save(update_fields=['status', 'attempt_count', 'processing_started_at', 'updated_at'])

        logger.info(f"[PAYOUT {payout_id}] Moved to processing, attempt #{payout.attempt_count}")

        # Step 2: Simulate bank API call — OUTSIDE transaction so we don't hold lock during I/O
        # In production this would be: response = bank_api.initiate_transfer(...)
        outcome = random.random()
        logger.info(f"[PAYOUT {payout_id}] Bank outcome roll: {outcome:.3f}")

        # Step 3: Handle outcome atomically
        with transaction.atomic():
            # Re-fetch with lock — state may have changed (e.g. retry logic reset it)
            payout = Payout.objects.select_for_update().get(id=payout_id)

            if payout.status != 'processing':
                logger.warning(f"[PAYOUT {payout_id}] Status changed to {payout.status} during bank call, aborting")
                return

            if outcome < 0.70:
                # SUCCESS (70%)
                # Atomically: transition to completed + write debit entry
                # If either fails, both roll back — no orphaned debits ever
                payout.transition_to('completed')
                payout.save(update_fields=['status', 'updated_at'])

                LedgerEntry.objects.create(
                    merchant=payout.merchant,
                    amount=payout.amount_paise,
                    entry_type='debit',
                    description=f'Payout settled to {payout.bank_account.account_holder_name} ({payout.bank_account.account_number[-4:]})',
                    reference_id=str(payout.id),
                )
                logger.info(f"[PAYOUT {payout_id}] COMPLETED — ₹{payout.amount_paise // 100:,} debited")

            elif outcome < 0.90:
                # FAILURE (20%)
                # Atomically: transition to failed
                # No debit entry = funds automatically released back to available balance
                # Balance = credits - debits, and since no debit was written, funds are free
                payout.transition_to('failed')
                payout.failure_reason = _get_failure_reason()
                payout.save(update_fields=['status', 'failure_reason', 'updated_at'])
                logger.info(f"[PAYOUT {payout_id}] FAILED — {payout.failure_reason} — funds returned")

            else:
                # HUNG (10%) — stays in processing
                # retry_stuck_payouts beat task will pick this up after 30s
                logger.warning(f"[PAYOUT {payout_id}] HUNG in processing — will be retried by beat scheduler")

    except Exception as exc:
        logger.error(f"[PAYOUT {payout_id}] Unexpected error: {exc}", exc_info=True)
        # Exponential backoff: 2^attempt seconds (2, 4, 8)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


def _get_failure_reason():
    """Realistic bank failure reasons for simulation."""
    reasons = [
        'Bank rejected: account frozen',
        'Bank rejected: invalid IFSC code',
        'Bank rejected: beneficiary account closed',
        'Bank timeout: no response within SLA',
        'Bank rejected: daily limit exceeded',
        'NEFT/IMPS network unavailable',
        'Bank rejected: account details mismatch',
    ]
    return random.choice(reasons)


@shared_task
def retry_stuck_payouts():
    """
    Runs every 30 seconds via Celery Beat.

    Finds payouts that have been in 'processing' state for more than 30 seconds.
    These are the 10% that hung in the bank simulation.

    Strategy:
    - If attempts < 3: reset to pending with exponential backoff (2, 4, 8 seconds)
    - If attempts >= 3: mark failed, funds return automatically (no debit entry exists)
    """
    from .models import Payout

    cutoff = timezone.now() - timedelta(seconds=30)

    stuck = Payout.objects.filter(
        status='processing',
        processing_started_at__lt=cutoff,
    ).select_for_update(skip_locked=True)  # skip_locked avoids deadlocks with concurrent workers

    count = 0
    with transaction.atomic():
        for payout in stuck:
            if payout.attempt_count >= 3:
                # Max retries exhausted — fail it
                # Funds return automatically: no debit entry was ever written
                payout.transition_to('failed')
                payout.failure_reason = f'Max retries ({payout.attempt_count}) exceeded — bank unresponsive'
                payout.save(update_fields=['status', 'failure_reason', 'updated_at'])
                logger.warning(f"[PAYOUT {payout.id}] Max retries exceeded, marked failed")
            else:
                # Reset to pending for retry
                payout.status = 'pending'
                payout.processing_started_at = None
                payout.save(update_fields=['status', 'processing_started_at', 'updated_at'])

                # Exponential backoff: 2^attempts seconds
                backoff = 2 ** payout.attempt_count
                process_payout.apply_async(args=[str(payout.id)], countdown=backoff)
                logger.info(f"[PAYOUT {payout.id}] Retrying in {backoff}s (attempt {payout.attempt_count + 1}/3)")
            count += 1

    if count > 0:
        logger.info(f"[BEAT] Processed {count} stuck payouts")