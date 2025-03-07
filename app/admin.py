from django.contrib import admin
from django_celery_beat.models import PeriodicTask, IntervalSchedule
from .models import *


admin.site.register(UserProfile)
admin.site.register(Stock)
admin.site.register(StockPriceHistory)
admin.site.register(Order)
admin.site.register(Transaction)
admin.site.register(DepositTransaction)
admin.site.register(UserStockHolding)
