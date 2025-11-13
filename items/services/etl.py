import pandas as pd
import json
import io
import requests
from urllib.parse import urlparse
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from items.models import Item


class ItemETLService:
    """
    Сервис отвечает за:
      - загрузку данных из CSV/JSON (локально или по URL),
      - нормализацию структуры,
      - идемпотентный импорт в базу.
    """

    def __init__(self, source: str):
        self.source = source

    def run(self) -> dict:
        df = self._load_to_dataframe()
        df = self._normalize(df)
        return self._import_to_db(df)

    def _load_to_dataframe(self) -> pd.DataFrame:
        parsed = urlparse(self.source)
        is_url = parsed.scheme in ("http", "https")

        if is_url:
            resp = requests.get(self.source, timeout=30)
            resp.raise_for_status()
            if self.source.endswith(".csv"):
                return pd.read_csv(io.StringIO(resp.text))
            data = resp.json()
            return pd.DataFrame(data if isinstance(data, list) else data.get("items", data))

        if self.source.endswith(".csv"):
            return pd.read_csv(self.source)
        if self.source.endswith(".json"):
            with open(self.source, "r", encoding="utf-8") as f:
                data = json.load(f)
            return pd.DataFrame(data if isinstance(data, list) else data.get("items", data))
        raise ValueError(f"Unsupported file type: {self.source}")

    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        rename_map = {}
        for cand in df.columns:
            cl = cand.lower()
            if cl in ("title", "product", "item", "item_name"):
                rename_map[cand] = "name"
            elif cl in ("cat", "group", "type"):
                rename_map[cand] = "category"
            elif cl in ("cost", "amount", "value"):
                rename_map[cand] = "price"
            elif cl in ("updated", "updatedat", "last_update", "last_updated"):
                rename_map[cand] = "updated_at"

        df = df.rename(columns=rename_map)
        for col in ["name", "category", "price", "updated_at"]:
            if col not in df.columns:
                df[col] = None

        df["name"] = df["name"].astype(str)
        df["category"] = df["category"].astype(str)
        df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)
        df["updated_at"] = df["updated_at"].apply(self._parse_dt).fillna(pd.Timestamp.utcnow())
        return df[["name", "category", "price", "updated_at"]]

    @staticmethod
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

    def _import_to_db(self, df: pd.DataFrame) -> dict:
        created, updated = 0, 0
        for row in df.to_dict(orient="records"):
            obj, is_created = Item.objects.get_or_create(
                name=row["name"],
                category=row["category"],
                defaults={"price": row["price"], "updated_at": row["updated_at"]},
            )
            if is_created:
                created += 1
            elif row["updated_at"] > obj.updated_at:
                obj.price = row["price"]
                obj.updated_at = row["updated_at"]
                obj.save(update_fields=["price", "updated_at"])
                updated += 1
        return {"created": created, "updated": updated, "total": len(df)}
