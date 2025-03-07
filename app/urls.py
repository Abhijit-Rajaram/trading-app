from django.urls import path
from .views import *

urlpatterns = [
    path('deposit/', deposit, name='deposit'),
    path("withdraw/", withdraw, name="withdraw"),
    path("stock_price_data/", stock_price_data, name="stock_price_data"),
    path("dashboard/", dashboard, name="dashboard"),
    path("stock-price/<str:symbol>/", stock_price_data, name="stock_price_data"),
    path("place-order/", place_order, name="place_order"),
    path("orders/", order_list, name="order_list"),
    path("portfolio/", portfolio_view, name="portfolio"),
]
