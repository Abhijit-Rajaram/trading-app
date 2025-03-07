from celery import shared_task
import requests
from decimal import Decimal
from django.utils.timezone import now
from .models import *
import time
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
import json
from django.db import transaction
from datetime import datetime, timedelta

API_URL = "https://script.google.com/macros/s/AKfycbyE3x3exGpNQaIADJ8L8Vu6X9OyoHiU3uhGTgTKuKVsNT-X-C68JyiWsmkAj7ffqTT1/exec"
API_KEY = "your_api_key"



@shared_task
def print_hi():
    print("Hi from Celery!")
    return "Printed Hi"


@shared_task
def update_stock_prices():
    # headers = {"Authorization": f"Bearer {API_KEY}"}
    response = requests.get(API_URL)
    print('Task Running', response.status_code)

    
    
    if response.status_code == 200:
        print('status code is 200')
        stock_data = response.json()

        # Get the channel layer for WebSocket communication
        channel_layer = get_channel_layer()

        print()
        
        for stock_info in stock_data[:5]: # Took First five companies only
            symbol = stock_info.get("Code_act")
            name = stock_info.get("Company_Name")
            ltp = stock_info.get("LTP")

            current_time = datetime.now() + timedelta(hours=5, minutes=30)

            print('current_time : ',current_time)
            if symbol and ltp:
                try:
                    stock, _ = Stock.objects.get_or_create(symbol=symbol,name=name)

                    # Store price in StockPriceHistory
                    StockPriceHistory.objects.create(
                        stock=stock,
                        price=Decimal(ltp),
                        date=current_time
                    )

                    async_to_sync(channel_layer.group_send)(
                        "stock_updates",
                        {"type": "send_stock_price", "stock_data": {"symbol": symbol, "price": ltp}},
                    )

                    print(f"Saved LTP for {symbol}: {ltp}")

                except Stock.DoesNotExist:
                    print(f"Stock {symbol} not found in database.")
    else:
        print("Failed to fetch stock data")


@shared_task
def process_limit_orders():
    limit_orders = Order.objects.filter(market_or_limit="LIMIT", status="PENDING")
    print('limit_orders : ',limit_orders)

    for order in limit_orders:
        latest_price = StockPriceHistory.objects.filter(stock=order.stock).order_by('-date').first()

        if latest_price:
            user_profile = order.user.profile  # Get user's profile

            with transaction.atomic():
                if order.order_type == "BUY":
                    total_cost = order.price * order.quantity

                    # Ensure user still has sufficient balance
                    if latest_price.price <= order.price and user_profile.balance < total_cost:
                        print(f"Limit Order Failed (Insufficient Balance): {order.stock.symbol}")
                        continue

                    # Deduct balance
                    user_profile.balance -= total_cost
                    user_profile.save()

                    # Add stock to user's holdings
                    holding, created = UserStockHolding.objects.get_or_create(user=order.user, stock=order.stock)
                    holding.quantity += order.quantity
                    holding.save()

                elif order.order_type == "SELL":
                    # Ensure user has enough stock to sell
                    holding = UserStockHolding.objects.filter(user=order.user, stock=order.stock).first()
                    if not holding or holding.quantity < order.quantity:
                        print(f"Limit Sell Order Failed (Not Enough Stocks): {order.stock.symbol}")
                        continue
                    if latest_price.price >= order.price:
                    # Reduce stock holdings and credit balance
                        holding.quantity -= order.quantity
                        holding.save()
                        user_profile.balance += latest_price.price * order.quantity
                        user_profile.save()
                    else:
                        continue

                # Mark order as executed
                order.status = "COMPLETED"
                order.executed_at = now()
                order.executed_price = latest_price.price
                order.save()

                current_time = datetime.now() + timedelta(hours=5, minutes=30)
                
                Transaction.objects.create(
                    order=order,
                    executed_price=latest_price.price,
                    executed_at=current_time
                )

                print(f"Limit Order Executed: {order.stock.symbol} at ₹{latest_price.price}")

    # **Cancel unexecuted limit orders at the end of the day**
    
    expired_orders = Order.objects.filter(order_type="LIMIT", status="PENDING", expiry__lte=now())

    for order in expired_orders:
        if order.order_type == "BUY":
            # Refund the reserved balance for expired buy orders
            user_profile = order.user.profile
            user_profile.balance += order.price * order.quantity
            user_profile.save()

        order.status = "CANCELLED"
        order.save()

    print("Expired limit orders have been cancelled.")

