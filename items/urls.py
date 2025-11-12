from django.urls import path
from .views import ItemListView, AvgPriceByCategoryView

urlpatterns = [
    path('items/', ItemListView.as_view(), name='items-list'),
    path('stats/avg-price-by-category/', AvgPriceByCategoryView.as_view(), name='stats-avg-price-by-category'),
]
