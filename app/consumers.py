import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils.timezone import now
from asgiref.sync import sync_to_async
from .models import StockPriceHistory, Stock
from decimal import Decimal

class StockPriceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_group_name = "stock_updates"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        print(" WebSocket Connected! Starting stock updates...")
        asyncio.create_task(self.send_stock_updates())

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        print(" WebSocket Disconnected!")

    async def send_stock_updates(self):
        """ Continuously fetch and send stock price updates every 5 seconds """
        while True:
            print("Fetching stock prices...")

            stocks = await sync_to_async(list)(Stock.objects.all())

            stock_prices = []
            for stock in stocks:
                latest_price = await sync_to_async(
                    lambda: StockPriceHistory.objects.filter(stock=stock).order_by('-date').first()
                )()

                if latest_price:
                    stock_prices.append({
                        "symbol": stock.symbol,
                        "price": float(latest_price.price),  # ✅ Convert Decimal to float
                        "timestamp": latest_price.date.strftime('%Y-%m-%d %H:%M:%S'),
                    })

            if stock_prices:
                print(f"Sending {len(stock_prices)} stock prices...")

                # Send data to all WebSocket clients
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "send_stock_price",
                        "stock_data": stock_prices
                    }
                )
            else:
                print("No stock prices found.")

            await asyncio.sleep(5)  # Fetch every 5 seconds

    async def send_stock_price(self, event):
        """ Send stock price data to the WebSocket client """
        await self.send(text_data=json.dumps(event["stock_data"]))  # ✅ Now JSON serializable
