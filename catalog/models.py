from django.core.validators import MinValueValidator
from django.db import models

# Create your models here.


class Category(models.Model):
    class Statuts(models.TextChoices):
        ACTIVE = "active", "متاح"
        COMING_SOON = "coming_soon", "سيتوفر لاحقاً"

    name = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=100, choices=Statuts.choices, default=Statuts.ACTIVE
    )
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):
    class ProductType(models.TextChoices):
        METALS = "metals", "معدنيات"
        DEVICES = "devices", "أجهزة"
        MATERIALS = "materials", "مواد"

    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True, allow_unicode=True)
    brand = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField()
    price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    image = models.ImageField(
        null=True,
        blank=True,
        upload_to="products/",
    )
    product_type = models.CharField(
        max_length=20,
        choices=ProductType.choices,
        blank=True,
    )
    stock_quantity = models.PositiveIntegerField(
        blank=True,
        null=True,
    )

    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name     

