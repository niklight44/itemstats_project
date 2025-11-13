import os
import logging
from django.core.management.base import BaseCommand
from items.services.etl import ItemETLService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Импорт товаров из CSV/JSON источников"

    def add_arguments(self, parser):
        parser.add_argument("--source", type=str, default="", help="Путь или URL к CSV/JSON")

    def handle(self, *args, **options):
        source = (
            options.get("source")
            or os.getenv("SOURCE_URL_CSV")
            or os.getenv("SOURCE_URL_JSON")
            or "items/sample_data/sample.csv"
        )

        self.stdout.write(self.style.NOTICE(f"Importing from: {source}"))
        result = ItemETLService(source).run()
        msg = f"Import completed — created={result['created']}, updated={result['updated']}, total={result['total']}"
        logger.info(msg)
        self.stdout.write(self.style.SUCCESS(msg))
