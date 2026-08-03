import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from .models import Order

logger = logging.getLogger(__name__)


def build_order_notification_email(order):
    subject = f"طلب جديد رقم #{order.id} - Luxe Dental House"
    created_at = timezone.localtime(order.created_at).strftime("%Y-%m-%d %H:%M")
    lines = [
        "تم استلام طلب جديد في متجر Luxe Dental House.",
        "",
        f"رقم الطلب: #{order.id}",
        f"تاريخ الطلب: {created_at}",
        f"حالة الطلب: {order.get_status_display()}",
        "",
        "بيانات العميل:",
        f"الاسم الكامل: {order.full_name}",
        f"رقم الهاتف: {order.phone}",
        f"المدينة: {order.city}",
        f"العنوان: {order.address or ''}",
        "",
        "تفاصيل الطلب:",
        "",
    ]
    for item in order.items.all():
        lines.extend(
            [
                f"المنتج: {item.product_name}",
                f"الكمية: {item.quantity}",
                f"سعر الوحدة: ${item.unit_price}",
                f"المجموع: ${item.subtotal}",
                "",
            ]
        )
    lines.append(f"الإجمالي النهائي: ${order.total_amount}")
    if order.notes:
        lines.extend(["", "ملاحظات العميل:", order.notes])
    lines.extend(
        ["", "يمكن مراجعة الطلب وتغيير حالته من لوحة إدارة Django."]
    )
    return subject, "\n".join(lines)


def send_order_notification_email(order_id):
    required_settings = (
        settings.EMAIL_HOST_USER,
        settings.EMAIL_HOST_PASSWORD,
        settings.ORDER_NOTIFICATION_EMAIL,
    )
    if not all(required_settings):
        logger.warning(
            "Order notification email skipped because email settings are incomplete "
            "for order %s.",
            order_id,
        )
        return False

    try:
        order = Order.objects.prefetch_related("items").get(pk=order_id)
        subject, body = build_order_notification_email(order)
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ORDER_NOTIFICATION_EMAIL],
            fail_silently=False,
        )
    except Exception:
        logger.exception(
            "Failed to send order notification email for order %s.", order_id
        )
        return False
    return True
