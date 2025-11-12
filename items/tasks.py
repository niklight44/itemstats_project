from celery import shared_task
from django.core.management import call_command

@shared_task(name='items.tasks.import_items_task')
def import_items_task(source: str | None = None):
    # source can be a URL or a local file path; the management command handles it
    call_command('import_items', '--source', source or '')
