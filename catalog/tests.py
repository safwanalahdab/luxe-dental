from django.contrib.staticfiles import finders
from django.test import TestCase
from django.urls import reverse

from .models import Category, Product


class CatalogViewsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.active = Category.objects.create(name="Dental", slug="dental")
        cls.coming = Category.objects.create(
            name="Medical", slug="medical", status=Category.Statuts.COMING_SOON
        )
        cls.product = Product.objects.create(
            category=cls.active,
            name="Test product",
            slug="منتج-تجريبي",
            description="Clinical material",
            price=10,
            product_type=Product.ProductType.MATERIALS,
        )
        Product.objects.create(
            category=cls.coming,
            name="Hidden product",
            slug="hidden-product",
            description="Not orderable",
            price=20,
        )

    def test_core_pages_render(self):
        for name in ("home", "product_list", "about", "contact"):
            self.assertEqual(self.client.get(reverse(f"catalog:{name}")).status_code, 200)

    def test_home_uses_single_final_medical_category_icon(self):
        response = self.client.get(reverse("catalog:home"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn('class="medical-category-icon"', html)
        self.assertEqual(html.count("medical-stethoscope.jpg"), 1)
        self.assertNotIn("medical-equipment-icon", html)
        self.assertNotIn("medical-art", html)

    def test_product_list_filters_database_products(self):
        response = self.client.get(
            reverse("catalog:product_list"), {"type": "materials", "q": "Clinical"}
        )
        self.assertContains(response, "Test product")
        self.assertNotContains(response, "Hidden product")

    def test_product_collections_include_shared_view_controls(self):
        for name in ("home", "product_list"):
            response = self.client.get(reverse(f"catalog:{name}"))
            self.assertContains(response, 'data-product-view="grid"')
            self.assertContains(response, 'data-product-view="list"')
            self.assertContains(response, "data-product-grid")

    def test_product_view_keeps_existing_add_to_cart_form(self):
        response = self.client.get(reverse("catalog:product_list"))
        self.assertContains(
            response,
            reverse("orders:cart_add", args=[self.product.pk]),
        )
        self.assertContains(response, 'name="next"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_invalid_type_is_treated_as_all(self):
        response = self.client.get(reverse("catalog:product_list"), {"type": "invalid"})
        self.assertEqual(response.context["selected_type"], "all")

    def test_product_without_image_uses_existing_static_fallback(self):
        response = self.client.get(
            reverse("catalog:product_detail", args=[self.product.slug])
        )
        fallback = "images/products/composite-kit.svg"
        self.assertIsNotNone(finders.find(fallback))
        self.assertContains(response, f"/static/{fallback}")

    def test_non_orderable_products_do_not_show_add_to_cart_form(self):
        unavailable = Product.objects.create(
            category=self.active,
            name="Unavailable product",
            slug="unavailable-product",
            description="Unavailable",
            price=10,
            is_available=False,
        )
        out_of_stock = Product.objects.create(
            category=self.active,
            name="Out of stock product",
            slug="out-of-stock-product",
            description="Out of stock",
            price=10,
            stock_quantity=0,
        )
        for product in (
            unavailable,
            out_of_stock,
            Product.objects.get(slug="hidden-product"),
        ):
            response = self.client.get(
                reverse("catalog:product_detail", args=[product.slug])
            )
            self.assertNotContains(
                response,
                reverse("orders:cart_add", args=[product.pk]),
            )

    def test_all_supported_product_type_filters_are_accepted(self):
        url = reverse("catalog:product_list")
        for product_type in ("all", "metals", "devices", "materials"):
            response = self.client.get(url, {"type": product_type})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["selected_type"], product_type)

    def test_detail_uses_slug_and_shows_nullable_stock(self):
        response = self.client.get(
            reverse("catalog:product_detail", args=[self.product.slug])
        )
        self.assertContains(response, "غير محددة")
