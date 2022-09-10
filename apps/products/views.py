from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, F, Sum
from django.shortcuts import render

from .models import Customer, LineItem, Order, Product


def index(request):
    """
    line_items = LineItem.objects.select_related("product").annotate(
        sub_total=F("product__price") * F("quantity")
    )
    for line_item in line_items:
        print(line_item.quantity, line_item.product.price, line_item.sub_total)
    """
    """
    result = LineItem.objects.aggregate(total=Avg(F('product__price') * F('quantity')))
    print(result['total'])
    """

    """
    orders = Order.objects.filter(order_date=F('shipped_date'))
    for order in orders:
        print(order.order_date, order.shipped_date)
    """

    """
    orders = Order.objects.annotate(
        processing_time=F("shipped_date") - F("order_date")
    ).filter(processing_time__lt=timedelta(days=3))
    for order in orders:
        print(order.order_date, order.shipped_date)
    """

    orders = Order.objects.select_related("customer").all()

    for order in orders:
        print(order.customer.full_name)

    return render(request, "products/index.html", {"orders": orders})


@login_required
def atomic_test(request):
    with transaction.atomic():
        orders = Order.objects.select_related("customer").get(pk=1)
        print(orders.coupon_code)
        orders.coupon_code = "DISCOUNT2021"
        orders.save()
        print(orders.coupon_code)
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
