from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.RESTRICT, related_name='profile', unique=True)
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # Store balance with decimal precision
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.RESTRICT, related_name='created_profile')
    created_date_time = models.DateTimeField(null=True, blank=True)
    updated_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.RESTRICT, related_name='updated_profile')
    updated_date_time = models.DateTimeField(null=True, blank=True)


class DepositTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('DEPOSIT', 'Deposit'),
        ('WITHDRAWAL', 'Withdrawal')
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} - ₹{self.amount}" 

class Stock(models.Model):
    symbol = models.CharField(max_length=10, unique=True,null=True,blank=True)  # e.g., AAPL, TSLA
    name = models.CharField(max_length=100,null=True,blank=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2, null=True,blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.symbol

class StockPriceHistory(models.Model):
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="price_history")
    date = models.DateTimeField(auto_now_add=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['-date']

class Order(models.Model):
    ORDER_TYPE_CHOICES = [
        ('BUY', 'BUY'),
        ('SELL', 'SELL'),
    ]
    MARKET_OR_LIMIT_CHOICES = [
        ('LIMIT', 'LIMIT'),
        ('MARKET', 'MARKET'),
    ]
    STATUS_CHOICES = [
        ('PENDING', 'PENDING'),
        ('COMPLETED', 'COMPLETED'),
        ('CANCELLED', 'CANCELLED'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, related_name="orders")
    order_type = models.CharField(max_length=4, choices=ORDER_TYPE_CHOICES,null=True,blank=True)
    market_or_limit = models.CharField(max_length=6, choices=MARKET_OR_LIMIT_CHOICES,null=True,blank=True)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Limit or market price
    executed_quantity = models.IntegerField(default=0)  # Track partially filled orders
    executed_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Track execution price
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    expiry = models.DateTimeField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} {self.order_type} {self.quantity} {self.stock.symbol} @ {self.price}"

class Transaction(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="transactions")
    executed_price = models.DecimalField(max_digits=10, decimal_places=2)
    executed_quantity = models.IntegerField(default=0)  # Keep track of how much was executed
    executed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Transaction: {self.order.stock.symbol} - {self.executed_quantity} shares @ {self.executed_price}"


class UserStockHolding(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)  # Total stocks the user holds

    class Meta:
        unique_together = ('user', 'stock')  # One entry per user-stock combination

    def __str__(self):
        return f"{self.user.username} holds {self.quantity} shares of {self.stock.symbol}"
