from django.contrib import admin

from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "status")
    list_filter = ("status",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "price",
        "stock_quantity",
        "is_available",
        "updated_at",
    )
    list_filter = (
        "category",
        "product_type",
        "is_available",
    )
    search_fields = (
        "name",
        "brand",
        "description",
    )
    prepopulated_fields = {"slug": ("name",)}
