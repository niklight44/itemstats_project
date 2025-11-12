import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'itemstats.settings')

app = Celery('itemstats')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

from celery.schedules import crontab

def _schedule_from_env():
    try:
        minutes = int(os.getenv('IMPORT_INTERVAL_MINUTES', '5'))
        return {'every_n_minutes': {'task': 'items.tasks.import_items_task', 'schedule': minutes * 60}}
    except Exception:
        return {}

app.conf.beat_schedule = _schedule_from_env()
