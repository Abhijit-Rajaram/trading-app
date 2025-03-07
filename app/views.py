from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponseRedirect
from .models import *
from django.db import transaction
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from django.utils.timezone import now
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from .models import *
from datetime import datetime, timedelta

def register_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Validate input
        if not username or not email or not password or not confirm_password:
            messages.error(request, "All fields are required!")
            return render(request, 'auth/register.html')

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return render(request, 'auth/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken!")
            return render(request, 'auth/register.html')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered!")
            return render(request, 'auth/register.html')

         # Create user and profile atomically
        try:
            with transaction.atomic():
                user = User.objects.create_user(username=username, email=email, password=password)
                UserProfile.objects.create(user=user, balance=0)  # Initialize balance

            messages.success(request, "Registration successful! You can now log in.")
            return redirect('login')

        except Exception as e:
            messages.error(request, f"Registration failed: {str(e)}")
            return render(request, 'auth/register.html')

    return render(request, 'auth/register.html')


def login_view(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')

        if not username or not password:
            messages.error(request, "Username and password are required!")
            return render(request, 'auth/login.html')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid credentials!")
            return render(request, 'auth/login.html')

    return render(request, 'auth/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('login')

@login_required(login_url="/")
def deposit(request):
    if request.method == "POST":
        amount = request.POST.get("amount")
        
        try:
            amount = Decimal(amount) 
            if amount <= 0:
                messages.error(request, "Invalid deposit amount.")
                return redirect("deposit")

            with transaction.atomic():
                profile, created = UserProfile.objects.get_or_create(user=request.user)
                profile.balance += amount  
                profile.save()

                # Log the deposit transaction
                DepositTransaction.objects.create(
                    user=request.user,
                    amount=amount,
                    transaction_type="DEPOSIT"
                )

            messages.success(request, f"Successfully deposited ₹{amount}!")
            return redirect("deposit")

        except:
            messages.error(request, "Invalid amount entered.")
            return redirect("deposit")

    return render(request, "funds/deposit.html")


@login_required(login_url="/")
def withdraw(request):
    if request.method == "POST":
        amount = request.POST.get("amount")
        
        try:
            amount = Decimal(amount)  # Convert to Decimal
            if amount <= 0:
                messages.error(request, "Invalid withdrawal amount.")
                return redirect("deposit")

            with transaction.atomic():
                profile = UserProfile.objects.get(user=request.user)

                if profile.balance < amount:
                    messages.error(request, "Insufficient balance.")
                    return redirect("deposit")

                profile.balance -= amount  
                profile.save()

                # Log the withdrawal transaction
                DepositTransaction.objects.create(
                    user=request.user,
                    amount=amount,
                    transaction_type="WITHDRAW"
                )

            messages.success(request, f"Successfully withdrew ₹{amount}!")
            return redirect("deposit")

        except:
            messages.error(request, "Invalid amount entered.")
            return redirect("deposit")

    return redirect("deposit")



def stock_price_data(request, symbol):
    prices = StockPriceHistory.objects.filter(stock__symbol=symbol).order_by("-date")[:50]
    print(prices)
    # prices = prices.order_by("date")
    data = [
    {
        "datetime": p.date.strftime("%Y-%m-%d %H:%M:%S"),  # Full datetime
        "date": p.date.strftime("%Y-%m-%d"),  # Only Date
        "time": p.date.strftime("%H:%M:%S"),  # Only Time
        "price": float(p.price),
    }
    for p in prices
]

    return JsonResponse(data, safe=False)

def dashboard(request):
    stocks = Stock.objects.all()
    return render(request, "chart/dashboard.html",{'stocks':stocks})

@login_required(login_url="/")
def place_order(request):
    if request.method == "POST":
        user = request.user
        stock_symbol = request.POST.get("symbol")
        order_type = request.POST.get("order_type")  # "market" or "limit"
        price = request.POST.get("price")  # Limit price (optional)
        quantity = request.POST.get("quantity")

        print('inside')

        try:
            stock = Stock.objects.get(symbol=stock_symbol)
            quantity = int(quantity)
            price = Decimal(price) if price else None
            user_profile = user.profile  

            with transaction.atomic():
                if order_type.upper() == "MARKET":
                    
                    latest_price = StockPriceHistory.objects.filter(stock=stock).order_by('-date').first()

                    if not latest_price:
                        return JsonResponse({"error": "Market price not available"}, status=400)

                    executed_price = latest_price.price
                    total_cost = executed_price * quantity

                    print('Total Cost : ', total_cost , request.POST.get("trade_type"))

                    if request.POST.get("trade_type").upper() == "BUY":
                        
                        if user_profile.balance < total_cost:
                            return JsonResponse({"error": "Insufficient balance"}, status=400)
                        
                        
                        user_profile.balance -= total_cost
                        user_profile.save()
                        print('Deduct balance : ', user_profile.balance)

                        holding, created = UserStockHolding.objects.get_or_create(user=user, stock=stock)
                        holding.quantity += quantity
                        holding.save()
                        print('holding : ', holding)

                    elif request.POST.get("trade_type").upper() == "SELL":
                        holding = UserStockHolding.objects.filter(user=user, stock=stock).first()
                        if not holding or holding.quantity < quantity:
                            return JsonResponse({"error": "Not enough stocks to sell"}, status=400)

                        
                        holding.quantity -= quantity
                        holding.save()
                        user_profile.balance += total_cost
                        user_profile.save()

                    
                    order = Order.objects.create(
                        user=user, stock=stock, quantity=quantity, order_type=request.POST.get("trade_type").upper(),market_or_limit = order_type.upper(),
                        price=executed_price, status="COMPLETED",executed_price=executed_price,executed_quantity = quantity
                    )
                    current_time = datetime.now() + timedelta(hours=5, minutes=30)
                    
                    Transaction.objects.create(
                        order=order,
                        executed_price=executed_price,
                        executed_quantity=quantity,
                        executed_at=current_time
                    )

                    return JsonResponse({"message": f"Market order executed at ₹{executed_price}!"})

                elif order_type.upper() == "LIMIT":
                    # Reserve balance for limit buy orders
                    if request.POST.get("trade_type") == "BUY":
                        total_cost = price * quantity
                        if user_profile.balance < total_cost:
                            return JsonResponse({"error": "Insufficient balance"}, status=400)

                        user_profile.balance -= total_cost  
                        user_profile.save()
                    
                    
                    Order.objects.create(
                        user=user, stock=stock, quantity=quantity, order_type=request.POST.get("trade_type").upper(),market_or_limit = order_type.upper(),
                        price=price, status="PENDING", expiry=now().replace(hour=23, minute=59, second=59)
                    )

                    return JsonResponse({"message": f"Limit order placed at ₹{price}. Waiting for execution."})

                else:
                    return JsonResponse({"message": "Invalid order type"}, status=400)

        except Stock.DoesNotExist:
            return JsonResponse({"message": "Stock not found"}, status=404)
        except Exception as e:
            return JsonResponse({"message": str(e)}, status=500)

    return JsonResponse({"message": "Invalid request"}, status=400)

@login_required(login_url="/")
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, "chart/orders.html", {"orders": orders})

@login_required(login_url="/")
def portfolio_view(request):
    holdings = UserStockHolding.objects.filter(user=request.user)

    for holding in holdings:
        latest_price = (
            StockPriceHistory.objects.filter(stock=holding.stock)
            .order_by('-date')
            .values('price')
            .first()
        )
        print('latest_price : ',latest_price)
        latest_price = latest_price["price"] if latest_price else 0  
        holding.latest_price = latest_price  
        holding.total_value = holding.quantity * latest_price  

    return render(request, "chart/portfolio.html", {"holdings": holdings})

