import io
import json
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
from items.services.etl import ItemETLService


@pytest.fixture
def csv_data(tmp_path):
    csv_content = (
        "title,group,cost,last_update\n"
        "Phone,Electronics,100.5,2024-01-01T12:00:00Z\n"
        "Case,Accessories,10,2024-01-02T12:00:00Z\n"
    )
    file_path = tmp_path / "test.csv"
    file_path.write_text(csv_content, encoding="utf-8")
    return str(file_path)


@pytest.fixture
def json_data(tmp_path):
    json_content = [
        {"name": "Laptop", "category": "Electronics", "price": 1200.0, "updated_at": "2024-01-04T12:00:00Z"},
        {"name": "Mouse", "category": "Accessories", "price": 25.0, "updated_at": "2024-01-05T12:00:00Z"},
    ]
    file_path = tmp_path / "test.json"
    file_path.write_text(json.dumps(json_content, indent=2), encoding="utf-8")
    return str(file_path)


def test_load_local_csv(csv_data):
    service = ItemETLService(csv_data)
    df = service._load_to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert {"title", "group", "cost", "last_update"} <= set(df.columns)
    assert len(df) == 2


def test_load_local_json(json_data):
    service = ItemETLService(json_data)
    df = service._load_to_dataframe()
    assert isinstance(df, pd.DataFrame)
    assert {"name", "category", "price", "updated_at"} <= set(df.columns)
    assert len(df) == 2


def test_normalize_dataframe():
    # DataFrame с кривыми колонками
    df = pd.DataFrame({
        "title": ["Phone"],
        "group": ["Electronics"],
        "cost": [99.9],
        "last_update": ["2024-01-01T12:00:00Z"],
    })
    service = ItemETLService("dummy_source")
    normalized = service._normalize(df)

    # Проверяем, что колонки переименованы корректно
    assert list(normalized.columns) == ["name", "category", "price", "updated_at"]
    assert normalized.loc[0, "name"] == "Phone"
    assert normalized.loc[0, "category"] == "Electronics"
    assert float(normalized.loc[0, "price"]) == 99.9


@patch("items.services.etl.Item.objects")
def test_import_to_db_creates_and_updates(mock_item):
    # ВАЖНО: не реально создает записи — мы проверяем структуру результата
    # Мокаем ORM-объекты
    mock_item.objects.all.return_value = [
        MagicMock(name="Phone", category="Electronics", price=90.0, updated_at=pd.Timestamp("2024-01-01T00:00:00Z"))
    ]

    df = pd.DataFrame([
        {"name": "Phone", "category": "Electronics", "price": 100.0, "updated_at": pd.Timestamp("2024-01-02T00:00:00Z")},
        {"name": "Case", "category": "Accessories", "price": 10.0, "updated_at": pd.Timestamp("2024-01-01T00:00:00Z")},
    ])

    service = ItemETLService("dummy_source")
    result = service._import_to_db(df)

    # Проверяем, что возвращает корректную статистику
    assert set(result.keys()) == {"created", "updated", "total"}
    assert result["total"] == 2

