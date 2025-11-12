import os
import io
import json
import logging
from urllib.parse import urlparse
import requests
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from items.models import Item

logger = logging.getLogger(__name__)

SAMPLE_CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'sample_data', 'sample.csv')
SAMPLE_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'sample_data', 'sample.json')

class Command(BaseCommand):
    help = 'Import items from CSV or JSON (HTTP/HTTPS or local). Idempotent by (name, category) and updated_at.'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=str, default='', help='URL (csv/json) or local file path. If empty, tries env SOURCE_URL_* or samples.')

    def handle(self, *args, **options):
        source = options.get('source') or os.getenv('SOURCE_URL_CSV') or os.getenv('SOURCE_URL_JSON')
        if not source:
            # fallback to sample data
            source = SAMPLE_CSV_PATH

        self.stdout.write(self.style.NOTICE(f"Import starting from: {source}"))
        try:
            df = self._load_to_dataframe(source)
        except Exception as e:
            raise CommandError(f"Failed to load source: {e}")

        # Normalize columns to required schema
        df = self._normalize(df)

        # Compute avg by category via pandas (for logs / verification)
        avg_by_cat = df.groupby('category')['price'].mean().round(2).to_dict()
        logger.info("Pandas avg price by category (preview): %s", avg_by_cat)
        self.stdout.write(self.style.SUCCESS(f"Pandas avg price by category: {avg_by_cat}"))

        # Upsert items idempotently
        created, updated = 0, 0
        for row in df.to_dict(orient='records'):
            name = row['name']
            category = row['category']
            price = row['price']
            updated_at = row['updated_at']
            obj, is_created = Item.objects.get_or_create(name=name, category=category, defaults={'price': price, 'updated_at': updated_at})
            if is_created:
                created += 1
            else:
                # Update only if incoming is newer
                if updated_at and (obj.updated_at is None or updated_at > obj.updated_at):
                    obj.price = price
                    obj.updated_at = updated_at
                    obj.save(update_fields=['price', 'updated_at'])
                    updated += 1

        self.stdout.write(self.style.SUCCESS(f"Import finished. created={created}, updated={updated} (total {len(df)})"))

    def _load_to_dataframe(self, source: str) -> pd.DataFrame:
        parsed = urlparse(source)
        is_url = parsed.scheme in ('http', 'https')
        if is_url:
            resp = requests.get(source, timeout=30)
            resp.raise_for_status()
            if source.endswith('.csv'):
                return pd.read_csv(io.StringIO(resp.text))
            else:
                data = resp.json()
                return pd.DataFrame(data if isinstance(data, list) else data.get('items', data))
        # local file
        if source.endswith('.csv'):
            return pd.read_csv(source)
        if source.endswith('.json'):
            with open(source, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return pd.DataFrame(data if isinstance(data, list) else data.get('items', data))
        # default to csv
        return pd.read_csv(source)

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        # Rename similar columns if present
        cols = {c.lower().strip(): c for c in df.columns}
        rename_map = {}
        for needed in ['name', 'category', 'price', 'updated_at']:
            if needed not in cols:
                # try to infer simple variants
                for cand in df.columns:
                    cl = cand.lower()
                    if needed == 'updated_at' and cl in ('updated', 'updatedat', 'last_update', 'last_updated'):
                        rename_map[cand] = 'updated_at'
                    if needed == 'price' and cl in ('cost', 'amount', 'value'):
                        rename_map[cand] = 'price'
                    if needed == 'category' and cl in ('cat', 'group', 'type'):
                        rename_map[cand] = 'category'
                    if needed == 'name' and cl in ('title', 'product', 'item', 'item_name'):
                        rename_map[cand] = 'name'
        df = df.rename(columns=rename_map)

        # Ensure required columns exist
        for col in ['name', 'category', 'price', 'updated_at']:
            if col not in df.columns:
                df[col] = None

        # Coerce types
        df['name'] = df['name'].astype(str)
        df['category'] = df['category'].astype(str)
        df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0.0)
        # Parse datetimes
        def _parse_dt(x):
            if pd.isna(x):
                return None
            if isinstance(x, str):
                dt = parse_datetime(x)
                if dt is None:
                    try:
                        return pd.to_datetime(x, utc=True)
                    except Exception:
                        return None
                return dt
            try:
                return pd.to_datetime(x, utc=True)
            except Exception:
                return None

        df['updated_at'] = df['updated_at'].apply(_parse_dt)
        # Fill missing updated_at with now to ensure idempotency works predictably
        now = pd.Timestamp.utcnow()
        df['updated_at'] = df['updated_at'].fillna(now)
        return df[['name', 'category', 'price', 'updated_at']]
