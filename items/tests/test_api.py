import json
import pandas as pd
import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient
from items.models import Item

@pytest.mark.django_db
def test_parsing_and_normalization(tmp_path, django_db_blocker):
    # Create a messy CSV
    csv_content = "title,group,cost,last_update\nPhone,Electronics,100.5,2024-01-01T12:00:00Z\nCase,Accessories,10,2024-01-02T12:00:00Z\n"
    p = tmp_path / "mess.csv"
    p.write_text(csv_content, encoding="utf-8")

    # Use management command
    from django.core.management import call_command
    call_command("import_items", "--source", str(p))

    assert Item.objects.count() == 2
    phone = Item.objects.get(name="Phone")
    assert phone.category == "Electronics"
    assert float(phone.price) == 100.5


@pytest.mark.django_db
def test_avg_price_calculation(client: APIClient):
    Item.objects.create(name="A", category="Cat1", price=10, updated_at=timezone.now())
    Item.objects.create(name="B", category="Cat1", price=20, updated_at=timezone.now())
    Item.objects.create(name="C", category="Cat2", price=30, updated_at=timezone.now())

    url = "/api/stats/avg-price-by-category/"
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert data["Cat1"] == 15.0
    assert data["Cat2"] == 30.0


@pytest.mark.django_db
def test_items_filtering_pagination(client: APIClient, settings):
    settings.REST_FRAMEWORK['PAGE_SIZE'] = 2
    for i in range(5):
        Item.objects.create(name=f"Item{i}", category="Cat", price=i, updated_at=timezone.now())
    for i in range(3):
        Item.objects.create(name=f"Gadget{i}", category="Gadgets", price=100+i, updated_at=timezone.now())

    url = "/api/items/?category=Cat&price_min=2&price_max=4"
    resp = client.get(url)
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 3  # items 2,3,4
    assert len(data["results"]) == 2  # page size
