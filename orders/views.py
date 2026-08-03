from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from urllib.parse import quote

from catalog.models import Product

from .cart import Cart
from .emails import send_order_notification_email
from .forms import CheckoutForm
from .models import Order, OrderItem

WHATSAPP_STORE_NUMBER = "963962092655"


def redirect_to_safe_next(request, fallback="catalog:product_list"):
    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect(fallback)


def build_whatsapp_url(order):
    lines = [
        "مرحباً Luxe Dental House،",
        "",
        f"أرغب بتأكيد طلبي رقم #{order.id}",
        "",
        f"الاسم: {order.full_name}",
        f"الهاتف: {order.phone}",
        f"المدينة: {order.city}",
        f"العنوان: {order.address or ''}",
        "",
        "تفاصيل الطلب:",
        "",
    ]
    for item in order.items.all():
        lines.extend(
            [
                item.product_name,
                f"الكمية: {item.quantity}",
                f"سعر الوحدة: ${item.unit_price}",
                f"المجموع: ${item.subtotal}",
                "",
            ]
        )
    lines.append(f"الإجمالي: ${order.total_amount}")
    if order.notes:
        lines.extend(["", "ملاحظات:", order.notes])

    return (
        f"https://wa.me/{WHATSAPP_STORE_NUMBER}"
        f"?text={quote(chr(10).join(lines), safe='')}"
    )


def cart_detail(request):
    cart = Cart(request)
    return render(
        request,
        "orders/cart.html",
        {"cart": cart, "cart_items": list(cart), "cart_total": cart.get_total_price()},
    )


@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product.objects.select_related("category"), pk=product_id)
    try:
        Cart(request).add(product, request.POST.get("quantity", 1))
    except ValueError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, f"تمت إضافة {product.name} إلى السلة.")
    return redirect_to_safe_next(request)


@require_POST
def cart_update(request, product_id):
    product = get_object_or_404(Product.objects.select_related("category"), pk=product_id)
    try:
        Cart(request).update(product, request.POST.get("quantity"))
    except ValueError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "تم تحديث الكمية.")
    return redirect("orders:cart_detail")


@require_POST
def cart_remove(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    Cart(request).remove(product)
    messages.success(request, "تم حذف المنتج من السلة.")
    return redirect("orders:cart_detail")


def checkout(request):
    cart = Cart(request)
    if not cart.data:
        messages.error(request, "السلة فارغة. أضف منتجاً قبل إتمام الطلب.")
        return redirect("orders:cart_detail")

    form = CheckoutForm(request.POST or None)
    cart_items = list(cart)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                products = {
                    str(product.pk): product
                    for product in Product.objects.select_for_update()
                    .select_related("category")
                    .filter(pk__in=cart.data.keys())
                }
                if len(products) != len(cart.data):
                    raise ValueError("أحد منتجات السلة لم يعد موجوداً.")

                checked_items = []
                total = 0
                for product_id, raw_quantity in cart.data.items():
                    product = products[product_id]
                    quantity = Cart.validate_quantity(raw_quantity)
                    Cart.validate_product(product, quantity)
                    subtotal = product.price * quantity
                    total += subtotal
                    checked_items.append((product, quantity))

                order = form.save(commit=False)
                order.total_amount = total
                order.save()
                OrderItem.objects.bulk_create(
                    [
                        OrderItem(
                            order=order,
                            product=product,
                            product_name=product.name,
                            unit_price=product.price,
                            quantity=quantity,
                        )
                        for product, quantity in checked_items
                    ]
                )
                transaction.on_commit(
                    lambda order_id=order.pk: send_order_notification_email(order_id)
                )
        except ValueError as error:
            messages.error(request, str(error))
            return redirect("orders:cart_detail")

        cart.clear()
        request.session["last_order_id"] = order.pk
        return redirect("orders:order_success")

    return render(
        request,
        "orders/checkout.html",
        {"form": form, "cart_items": cart_items, "cart_total": cart.get_total_price()},
    )


def order_success(request):
    order_id = request.session.get("last_order_id")
    if not order_id:
        messages.error(request, "لا يوجد طلب حديث لعرضه.")
        return redirect("orders:cart_detail")
    order = Order.objects.prefetch_related("items").filter(pk=order_id).first()
    if order is None:
        request.session.pop("last_order_id", None)
        return redirect("catalog:product_list")
    return render(
        request,
        "orders/order_success.html",
        {"order": order, "whatsapp_url": build_whatsapp_url(order)},
    )
