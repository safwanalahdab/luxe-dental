from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = (
        "product",
        "product_name",
        "unit_price",
        "quantity",
        "subtotal",
    )


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "full_name",
        "phone",
        "status",
        "total_amount",
        "created_at",
    )

    list_filter = (
        "status",
        "created_at",
    )

    search_fields = (
        "full_name",
        "phone",
        "city",
    )

    readonly_fields = (
        "total_amount",
        "created_at",
        "updated_at",
    )

    inlines = [
        OrderItemInline,
    ]
