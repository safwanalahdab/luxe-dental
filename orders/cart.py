from decimal import Decimal

from catalog.models import Category, Product


class Cart:
    SESSION_KEY = "cart"

    def __init__(self, request):
        self.session = request.session
        self.data = self.session.get(self.SESSION_KEY, {})
        self._remove_missing_products()

    def _remove_missing_products(self):
        if not self.data:
            return
        existing_ids = {
            str(product_id)
            for product_id in Product.objects.filter(
                pk__in=self.data.keys()
            ).values_list("pk", flat=True)
        }
        missing_ids = set(self.data) - existing_ids
        if missing_ids:
            for product_id in missing_ids:
                self.data.pop(product_id)
            self._save()

    @staticmethod
    def validate_quantity(quantity):
        if isinstance(quantity, bool):
            raise ValueError("الكمية غير صالحة.")
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise ValueError("الكمية يجب أن تكون رقماً صحيحاً.") from None
        if quantity < 1:
            raise ValueError("الكمية يجب أن تكون 1 على الأقل.")
        return quantity

    @staticmethod
    def validate_product(product, quantity):
        if not product.is_available:
            raise ValueError("هذا المنتج غير متوفر.")
        if product.category.status != Category.Statuts.ACTIVE:
            raise ValueError("هذا القسم سيتوفر قريباً.")
        if product.stock_quantity == 0:
            raise ValueError("هذا المنتج نافد من المخزون.")
        if (
            product.stock_quantity is not None
            and quantity > product.stock_quantity
        ):
            raise ValueError("الكمية المطلوبة تتجاوز المخزون المتاح.")

    def _save(self):
        self.session[self.SESSION_KEY] = self.data
        self.session.modified = True

    def add(self, product, quantity=1):
        quantity = self.validate_quantity(quantity)
        product_id = str(product.pk)
        new_quantity = self.data.get(product_id, 0) + quantity
        self.validate_product(product, new_quantity)
        self.data[product_id] = new_quantity
        self._save()

    def update(self, product, quantity):
        quantity = self.validate_quantity(quantity)
        self.validate_product(product, quantity)
        self.data[str(product.pk)] = quantity
        self._save()

    def remove(self, product):
        if self.data.pop(str(product.pk), None) is not None:
            self._save()

    def clear(self):
        self.session.pop(self.SESSION_KEY, None)
        self.data = {}
        self.session.modified = True

    def __len__(self):
        return sum(self.data.values())

    def __iter__(self):
        products = Product.objects.select_related("category").filter(
            pk__in=self.data.keys()
        )
        for product in products:
            quantity = self.data[str(product.pk)]
            yield {
                "product": product,
                "quantity": quantity,
                "subtotal": product.price * quantity,
            }

    def get_total_price(self):
        return sum(
            (item["subtotal"] for item in self),
            Decimal("0.00"),
        )
