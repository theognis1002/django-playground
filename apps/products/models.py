from django.db import models


class Customer(models.Model):
    first_name = models.CharField(max_length=50, null=False)
    last_name = models.CharField(max_length=50, null=False)
    address = models.CharField(max_length=500, null=False)
    city = models.CharField(max_length=50, null=False)
    postcode = models.CharField(max_length=50, null=False)
    email = models.CharField(max_length=50, null=False, unique=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class Product(models.Model):
    name = models.CharField(max_length=50, null=False, unique=True)
    price = models.IntegerField(null=False)

    def __str__(self):
        return f"{self.name}"


class Order(models.Model):
    order_date = models.DateField(null=False)
    shipped_date = models.DateField(null=True)
    delivered_date = models.DateField(null=True)
    coupon_code = models.CharField(max_length=50, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=False)
    products = models.ManyToManyField(Product, through="LineItem")

    def __str__(self):
        return f"Order#: {self.pk}"


class LineItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=False)
    quantity = models.IntegerField(null=False)

    def __str__(self):
        return f"Line Item #:{self.pk}"
