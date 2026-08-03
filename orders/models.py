from django.core.validators import MinValueValidator
from django.db import models

from catalog.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "جديد"
        PROCESSING = "processing", "قيد المعالجة"
        COMPLETED = "completed", "مكتمل"
        CANCELLED = "cancelled", "ملغي"

    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    city = models.CharField(max_length=20)
    address = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order{self.pk} - {self.full_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        related_name="order_items",
    )

    product_name = models.CharField(max_length=200)

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    def __str__(self):
        return f"{self.product_name} × {self.quantity}"

    @property
    def subtotal(self):
        if self.quantity is None or self.unit_price is None:
            return 0
        return self.quantity * self.unit_price
