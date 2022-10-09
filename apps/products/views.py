from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, F, Sum
from django.shortcuts import render

from .models import Customer, LineItem, Order, Product


def index(request):
    orders = Order.objects.select_related("customer").all()

    for order in orders:
        print(order.customer.full_name)

    return render(request, "products/index.html", {"orders": orders})


@login_required
def atomic_test(request):
    with transaction.atomic():
        orders = Order.objects.select_related("customer").get(pk=1)
        orders.coupon_code = "DISCOUNT2021"
        orders.save()
        try:
            # pass
            failed_query = Order.objects.select_related("customer").get(pk=999999)
        except Order.DoesNotExist:
            print("Failed")
            transaction.set_rollback(True)

    return render(request, "products/index.html", {"orders": [orders]})


@login_required
def test_view(request):
    return render(request, "products/index.html", {"orders": []})
