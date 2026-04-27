import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Beat schedule: every 30s check for stuck payouts
from celery.schedules import timedelta
app.conf.beat_schedule = {
    'retry-stuck-payouts': {
        'task': 'payouts.tasks.retry_stuck_payouts',
        'schedule': timedelta(seconds=30),
    },
}