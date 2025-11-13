from celery import shared_task
from items.services.etl import ItemETLService


@shared_task(name="items.tasks.import_items_task")
def import_items_task(source: str | None = None):
    service = ItemETLService(source or "items/sample_data/sample.csv")
    result = service.run()
    return result
