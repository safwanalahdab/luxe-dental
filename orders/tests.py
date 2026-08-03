from decimal import Decimal
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.core import mail
from django.contrib import admin
from django.contrib.messages import get_messages
from django.test import TestCase, override_settings
from django.urls import reverse

from catalog.models import Category, Product

from .cart import Cart
from .models import Order, OrderItem
from .admin import OrderAdmin, OrderItemInline


class CartTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.active = Category.objects.create(name="Dental", slug="dental-cart")
        cls.coming = Category.objects.create(
            name="Medical",
            slug="medical-cart",
            status=Category.Statuts.COMING_SOON,
        )
        cls.product = Product.objects.create(
            category=cls.active,
            name="Material",
            slug="material",
            description="Test",
            price=Decimal("12.50"),
            stock_quantity=5,
        )
        cls.unavailable = Product.objects.create(
            category=cls.active,
            name="Unavailable",
            slug="unavailable",
            description="Test",
            price=10,
            is_available=False,
        )
        cls.coming_product = Product.objects.create(
            category=cls.coming,
            name="Coming",
            slug="coming",
            description="Test",
            price=10,
        )
        cls.out_of_stock = Product.objects.create(
            category=cls.active,
            name="Out",
            slug="out",
            description="Test",
            price=10,
            stock_quantity=0,
        )

    def add_url(self, product=None):
        return reverse("orders:cart_add", args=[(product or self.product).pk])

    def session_cart(self):
        return self.client.session.get("cart", {})

    def test_available_product_can_be_added(self):
        self.client.post(self.add_url(), {"quantity": 2})
        self.assertEqual(self.session_cart(), {str(self.product.pk): 2})

    def test_add_from_product_list_redirects_to_same_page_with_query(self):
        next_url = "/products/?type=devices&q=material"
        response = self.client.post(
            self.add_url(), {"quantity": 1, "next": next_url}
        )
        self.assertRedirects(response, next_url, fetch_redirect_response=False)
        self.assertEqual(self.session_cart(), {str(self.product.pk): 1})

    def test_add_from_product_detail_redirects_to_same_page(self):
        next_url = reverse("catalog:product_detail", args=[self.product.slug])
        response = self.client.post(
            self.add_url(), {"quantity": 1, "next": next_url}
        )
        self.assertRedirects(response, next_url)

    def test_success_message_names_product_and_cart_count_updates(self):
        next_url = reverse("catalog:product_list")
        response = self.client.post(
            self.add_url(),
            {"quantity": 2, "next": next_url},
            follow=True,
        )
        self.assertContains(response, f"تمت إضافة {self.product.name} إلى السلة.")
        self.assertContains(response, '<span class="cart-count">2</span>', html=True)
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn(f"تمت إضافة {self.product.name} إلى السلة.", messages)

    def test_external_or_missing_next_uses_internal_fallback(self):
        for next_url in ("https://malicious.example.com", None):
            data = {"quantity": 1}
            if next_url is not None:
                data["next"] = next_url
            response = self.client.post(self.add_url(), data)
            self.assertRedirects(response, reverse("catalog:product_list"))

    def test_validation_error_returns_to_safe_next_without_adding(self):
        next_url = "/products/?type=devices"
        response = self.client.post(
            self.add_url(), {"quantity": 6, "next": next_url}
        )
        self.assertRedirects(response, next_url, fetch_redirect_response=False)
        self.assertEqual(self.session_cart(), {})
        messages = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn("الكمية المطلوبة تتجاوز المخزون المتاح.", messages)

    def test_adding_same_product_twice_increments_quantity(self):
        self.client.post(self.add_url(), {"quantity": 1})
        self.client.post(self.add_url(), {"quantity": 2})
        self.assertEqual(self.session_cart()[str(self.product.pk)], 3)

    def test_unavailable_product_cannot_be_added(self):
        self.client.post(self.add_url(self.unavailable), {"quantity": 1})
        self.assertEqual(self.session_cart(), {})

    def test_coming_soon_product_cannot_be_added(self):
        self.client.post(self.add_url(self.coming_product), {"quantity": 1})
        self.assertEqual(self.session_cart(), {})

    def test_zero_stock_product_cannot_be_added(self):
        self.client.post(self.add_url(self.out_of_stock), {"quantity": 1})
        self.assertEqual(self.session_cart(), {})

    def test_stock_cannot_be_exceeded_on_add(self):
        self.client.post(self.add_url(), {"quantity": 6})
        self.assertEqual(self.session_cart(), {})

    def test_invalid_quantities_are_rejected(self):
        for quantity in (0, -1, "invalid"):
            self.client.post(self.add_url(), {"quantity": quantity})
            self.assertEqual(self.session_cart(), {})

    def test_update_quantity_works_and_checks_stock(self):
        self.client.post(self.add_url(), {"quantity": 1})
        url = reverse("orders:cart_update", args=[self.product.pk])
        self.client.post(url, {"quantity": 4})
        self.assertEqual(self.session_cart()[str(self.product.pk)], 4)
        self.client.post(url, {"quantity": 6})
        self.assertEqual(self.session_cart()[str(self.product.pk)], 4)

    def test_remove_works(self):
        self.client.post(self.add_url(), {"quantity": 1})
        self.client.post(reverse("orders:cart_remove", args=[self.product.pk]))
        self.assertEqual(self.session_cart(), {})

    def test_total_and_count_use_database_price(self):
        self.client.post(self.add_url(), {"quantity": 3, "price": "0.01"})
        request = type("Request", (), {"session": self.client.session})()
        cart = Cart(request)
        self.assertEqual(len(cart), 3)
        self.assertEqual(cart.get_total_price(), Decimal("37.50"))

    def test_mutation_endpoints_reject_get_without_changing_cart(self):
        self.client.post(self.add_url(), {"quantity": 1})
        original = self.session_cart().copy()
        urls = [
            self.add_url(),
            reverse("orders:cart_update", args=[self.product.pk]),
            reverse("orders:cart_remove", args=[self.product.pk]),
        ]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 405)
            self.assertEqual(self.session_cart(), original)

    def test_cart_page_returns_200_for_empty_and_populated_cart(self):
        url = reverse("orders:cart_detail")
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.post(self.add_url(), {"quantity": 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Material")


class OrderAdminTests(TestCase):
    def test_historical_order_values_are_read_only(self):
        order_admin = OrderAdmin(Order, admin.site)
        self.assertIn("total_amount", order_admin.get_readonly_fields(None))
        self.assertFalse(OrderItemInline.can_delete)
        self.assertEqual(
            set(OrderItemInline.readonly_fields),
            {"product", "product_name", "unit_price", "quantity", "subtotal"},
        )


class CheckoutTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.active = Category.objects.create(name="Active", slug="checkout-active")
        cls.coming = Category.objects.create(
            name="Soon",
            slug="checkout-soon",
            status=Category.Statuts.COMING_SOON,
        )
        cls.product = Product.objects.create(
            category=cls.active,
            name="Checkout Product",
            slug="checkout-product",
            description="Test",
            price=Decimal("15.75"),
            stock_quantity=5,
        )
        cls.second_product = Product.objects.create(
            category=cls.active,
            name="Second Product",
            slug="second-product",
            description="Test",
            price=Decimal("8.00"),
            stock_quantity=None,
        )

    def form_data(self, **extra):
        data = {
            "full_name": "Test Customer",
            "phone": "+963 999 111 222",
            "city": "Damascus",
            "address": "Main Street 12",
            "notes": "Call first",
        }
        data.update(extra)
        return data

    def set_cart(self, values=None):
        session = self.client.session
        session["cart"] = values or {str(self.product.pk): 2}
        session.save()

    def test_get_checkout_with_valid_cart_returns_200(self):
        self.set_cart()
        response = self.client.get(reverse("orders:checkout"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Checkout Product")

    def test_empty_cart_cannot_create_order(self):
        response = self.client.post(reverse("orders:checkout"), self.form_data())
        self.assertRedirects(response, reverse("orders:cart_detail"))
        self.assertEqual(Order.objects.count(), 0)

    def test_valid_post_creates_order_and_correct_items(self):
        self.set_cart(
            {str(self.product.pk): 2, str(self.second_product.pk): 3}
        )
        response = self.client.post(reverse("orders:checkout"), self.form_data())
        self.assertRedirects(response, reverse("orders:order_success"))
        self.assertEqual(Order.objects.count(), 1)
        order = Order.objects.get()
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.total_amount, Decimal("55.50"))
        first = order.items.get(product=self.product)
        self.assertEqual(first.unit_price, self.product.price)
        self.assertEqual(first.product_name, self.product.name)
        self.assertEqual(first.quantity, 2)

    def test_client_cannot_forge_totals_or_item_snapshot(self):
        self.set_cart()
        data = self.form_data(
            total_amount="0.01",
            unit_price="0.01",
            product_name="Forged",
        )
        self.client.post(reverse("orders:checkout"), data)
        order = Order.objects.get()
        item = order.items.get()
        self.assertEqual(order.total_amount, Decimal("31.50"))
        self.assertEqual(item.unit_price, Decimal("15.75"))
        self.assertEqual(item.product_name, "Checkout Product")

    def test_unavailable_product_blocks_checkout_and_preserves_cart(self):
        self.set_cart()
        self.product.is_available = False
        self.product.save(update_fields=["is_available"])
        self.client.post(reverse("orders:checkout"), self.form_data())
        self.assertEqual(Order.objects.count(), 0)
        self.assertIn(str(self.product.pk), self.client.session["cart"])

    def test_coming_soon_product_blocks_checkout(self):
        self.set_cart()
        self.product.category = self.coming
        self.product.save(update_fields=["category"])
        self.client.post(reverse("orders:checkout"), self.form_data())
        self.assertEqual(Order.objects.count(), 0)

    def test_zero_stock_blocks_checkout(self):
        self.set_cart()
        self.product.stock_quantity = 0
        self.product.save(update_fields=["stock_quantity"])
        self.client.post(reverse("orders:checkout"), self.form_data())
        self.assertEqual(Order.objects.count(), 0)

    def test_quantity_above_stock_blocks_checkout(self):
        self.set_cart({str(self.product.pk): 6})
        self.client.post(reverse("orders:checkout"), self.form_data())
        self.assertEqual(Order.objects.count(), 0)

    def test_cart_is_cleared_only_after_success(self):
        self.set_cart()
        self.client.post(reverse("orders:checkout"), self.form_data())
        self.assertNotIn("cart", self.client.session)

    @patch("orders.views.OrderItem.objects.bulk_create", side_effect=RuntimeError)
    def test_transaction_failure_rolls_back_and_preserves_cart(self, _bulk_create):
        self.set_cart()
        with self.assertRaises(RuntimeError):
            self.client.post(reverse("orders:checkout"), self.form_data())
        self.assertEqual(Order.objects.count(), 0)
        self.assertIn(str(self.product.pk), self.client.session["cart"])

    def test_invalid_form_preserves_entered_data_and_cart(self):
        self.set_cart()
        response = self.client.post(
            reverse("orders:checkout"), self.form_data(phone="bad")
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["form"]["phone"].value(), "bad")
        self.assertIn(str(self.product.pk), self.client.session["cart"])
        self.assertEqual(Order.objects.count(), 0)

    def test_success_page_is_limited_to_creating_session(self):
        self.set_cart()
        self.client.post(reverse("orders:checkout"), self.form_data())
        order = Order.objects.get()
        response = self.client.get(reverse("orders:order_success"))
        self.assertContains(response, f"#{order.pk}")

        other_client = self.client_class()
        other_response = other_client.get(reverse("orders:order_success"))
        self.assertRedirects(other_response, reverse("orders:cart_detail"))

    def test_success_page_whatsapp_link_uses_saved_order_data(self):
        self.set_cart(
            {str(self.product.pk): 2, str(self.second_product.pk): 3}
        )
        self.client.post(reverse("orders:checkout"), self.form_data())
        order = Order.objects.get()

        self.assertNotIn("cart", self.client.session)
        response = self.client.get(reverse("orders:order_success"))
        whatsapp_url = response.context["whatsapp_url"]
        parsed = urlparse(whatsapp_url)
        message = parse_qs(parsed.query)["text"][0]

        self.assertEqual(parsed.netloc, "wa.me")
        self.assertEqual(parsed.path, "/963962092655")
        self.assertContains(response, "إرسال تفاصيل الطلب عبر WhatsApp")
        self.assertContains(response, 'target="_blank"')
        self.assertContains(response, 'rel="noopener noreferrer"')
        self.assertIn(f"#{order.pk}", message)
        self.assertIn(order.full_name, message)
        self.assertIn("Checkout Product", message)
        self.assertIn("الكمية: 2", message)
        self.assertIn("سعر الوحدة: $15.75", message)
        self.assertIn("Second Product", message)
        self.assertIn("الإجمالي: $55.50", message)
        self.assertIn("ملاحظات:\nCall first", message)

    def test_whatsapp_message_omits_empty_notes(self):
        self.set_cart()
        self.client.post(reverse("orders:checkout"), self.form_data(notes=""))
        response = self.client.get(reverse("orders:order_success"))
        message = parse_qs(
            urlparse(response.context["whatsapp_url"]).query
        )["text"][0]

        self.assertNotIn("ملاحظات:", message)

    def test_session_cannot_build_whatsapp_url_for_another_order(self):
        other_order = Order.objects.create(
            full_name="Other Customer",
            phone="+963000000000",
            city="Aleppo",
            address="Other address",
            total_amount=Decimal("999.00"),
        )
        self.set_cart()
        self.client.post(reverse("orders:checkout"), self.form_data())

        response = self.client.get(
            reverse("orders:order_success"), {"order_id": other_order.pk}
        )
        message = parse_qs(
            urlparse(response.context["whatsapp_url"]).query
        )["text"][0]

        self.assertNotIn("Other Customer", message)
        self.assertNotIn("$999.00", message)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST_USER="amermashaan6@gmail.com",
        EMAIL_HOST_PASSWORD="test-app-password",
        DEFAULT_FROM_EMAIL="amermashaan6@gmail.com",
        ORDER_NOTIFICATION_EMAIL="amermashaan6@gmail.com",
    )
    def test_successful_checkout_sends_one_complete_email_from_saved_order(self):
        self.set_cart(
            {str(self.product.pk): 2, str(self.second_product.pk): 3}
        )
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("orders:checkout"), self.form_data()
            )

        self.assertRedirects(response, reverse("orders:order_success"))
        order = Order.objects.get()
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertEqual(email.to, ["amermashaan6@gmail.com"])
        self.assertIn(f"#{order.pk}", email.subject)
        for value in (
            "Test Customer",
            "+963 999 111 222",
            "Damascus",
            "Main Street 12",
            "Checkout Product",
            "الكمية: 2",
            "سعر الوحدة: $15.75",
            "المجموع: $31.50",
            "Second Product",
            "الكمية: 3",
            "سعر الوحدة: $8.00",
            "المجموع: $24.00",
            "الإجمالي النهائي: $55.50",
            "ملاحظات العميل:\nCall first",
        ):
            self.assertIn(value, email.body)
        self.assertNotIn("cart", self.client.session)

        self.client.get(reverse("orders:order_success"))
        self.client.get(reverse("orders:order_success"))
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST_USER="amermashaan6@gmail.com",
        EMAIL_HOST_PASSWORD="test-app-password",
        DEFAULT_FROM_EMAIL="amermashaan6@gmail.com",
        ORDER_NOTIFICATION_EMAIL="amermashaan6@gmail.com",
    )
    def test_email_omits_empty_notes(self):
        self.set_cart()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(
                reverse("orders:checkout"), self.form_data(notes="")
            )
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn("ملاحظات العميل:", mail.outbox[0].body)

    @override_settings(
        EMAIL_HOST_USER="amermashaan6@gmail.com",
        EMAIL_HOST_PASSWORD="test-app-password",
        DEFAULT_FROM_EMAIL="amermashaan6@gmail.com",
        ORDER_NOTIFICATION_EMAIL="amermashaan6@gmail.com",
    )
    @patch("orders.emails.send_mail", side_effect=OSError("SMTP unavailable"))
    def test_email_failure_keeps_order_items_and_success_redirect(self, _send_mail):
        self.set_cart()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse("orders:checkout"), self.form_data()
            )

        self.assertRedirects(response, reverse("orders:order_success"))
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(Order.objects.get().items.count(), 1)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        EMAIL_HOST_USER="amermashaan6@gmail.com",
        EMAIL_HOST_PASSWORD="test-app-password",
        ORDER_NOTIFICATION_EMAIL="amermashaan6@gmail.com",
    )
    def test_unsuccessful_checkouts_do_not_send_email(self):
        response = self.client.post(
            reverse("orders:checkout"), self.form_data()
        )
        self.assertRedirects(response, reverse("orders:cart_detail"))

        self.set_cart()
        self.client.post(
            reverse("orders:checkout"), self.form_data(phone="bad")
        )

        self.product.is_available = False
        self.product.save(update_fields=["is_available"])
        self.set_cart()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("orders:checkout"), self.form_data())

        self.product.is_available = True
        self.product.category = self.coming
        self.product.save(update_fields=["is_available", "category"])
        self.set_cart()
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("orders:checkout"), self.form_data())

        self.product.category = self.active
        self.product.stock_quantity = 1
        self.product.save(update_fields=["category", "stock_quantity"])
        self.set_cart({str(self.product.pk): 2})
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("orders:checkout"), self.form_data())

        self.assertEqual(len(mail.outbox), 0)
