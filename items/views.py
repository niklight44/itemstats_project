from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import Item
from .serializers import ItemSerializer
import pandas as pd
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class ItemFilter(filters.FilterSet):
    category = filters.CharFilter(field_name='category', lookup_expr='iexact')
    price_min = filters.NumberFilter(field_name='price', lookup_expr='gte')
    price_max = filters.NumberFilter(field_name='price', lookup_expr='lte')

    class Meta:
        model = Item
        fields = ['category', 'price_min', 'price_max']


class ItemListView(generics.ListAPIView):
    queryset = Item.objects.all().order_by('id')
    serializer_class = ItemSerializer
    filterset_class = ItemFilter

    @swagger_auto_schema(
        operation_description="Получить список товаров с фильтрацией по категории и цене",
        responses={200: ItemSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class AvgPriceByCategoryView(APIView):
    @swagger_auto_schema(
        operation_description="Средняя цена товаров по категориям",
        responses={200: openapi.Response(
            description="Словарь с категориями и средними ценами",
            examples={"application/json": {"electronics": 150.5, "books": 82.3}}
        )}
    )
    def get(self, request):
        key = "stats:avg_price_by_category"
        data = cache.get(key)
        if data is not None:
            return Response(data)

        qs = Item.objects.values('category', 'price')
        if not qs.exists():
            cache.set(key, {}, settings.STATS_CACHE_TTL)
            return Response({})

        df = pd.DataFrame(list(qs))
        # In case of Decimal -> convert to float for JSON serialization
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        grouped = df.groupby('category', dropna=False)['price'].mean().round(2)
        data = {k if k is not None else "": float(v) for k, v in grouped.to_dict().items()}
        cache.set(key, data, settings.STATS_CACHE_TTL)
        return Response(data)
