# paycharm/app/integrations/email_service.py
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import List

from paycharm.app.config import settings
from paycharm.app.database import SessionLocal
from paycharm.app.models import Order, OrderItem


def _get_order_with_items(order_id: int) -> tuple[Order | None, List[OrderItem]]:
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return None, []
        items = order.items
        # detach if нужно, но для простоты просто возвращаем
        return order, items
    finally:
        db.close()


def _items_to_text(items: List[OrderItem]) -> str:
    lines = []
    for item in items:
        lines.append(
            f"- {item.name}: {item.quantity} шт x {float(item.unit_price)} = {float(item.line_amount)}"
        )
    return "\n".join(lines)


def send_new_order_notification(order_id: int) -> None:
    """
    Отправляем письмо админу/менеджеру о новом заказе.
    """
    order, items = _get_order_with_items(order_id)
    if not order:
        return

    subject = f"Новый заказ #{order.id}"
    body = f"""
Новый заказ #{order.id}

Статус: {order.status}
Сумма: {float(order.total_amount or 0)} руб.

Товары:
{_items_to_text(items)}

Адрес доставки: {order.delivery_address or '-'}
Email: {order.contact_email or '-'}
Телефон: {order.contact_phone or '-'}

Создан: {order.created_at}
    """.strip()

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USER
    msg["To"] = settings.ORDER_NOTIFICATION_EMAIL
    msg.set_content(body)

    context = ssl.create_default_context()
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls(context=context)
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
