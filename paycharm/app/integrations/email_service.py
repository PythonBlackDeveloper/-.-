# paycharm/app/integrations/email_service.py
from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage
from typing import List, Tuple, Optional

from paycharm.app.config import settings
from paycharm.app.database import SessionLocal
from paycharm.app.models import Order, OrderItem


def _get_order_with_items(order_id: int) -> Tuple[Optional[Order], List[OrderItem]]:
    """
    Вытаскиваем заказ и его позиции по ID из БД.
    """
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return None, []
        items = list(order.items)
        return order, items
    finally:
        db.close()


def _items_to_text(items: List[OrderItem]) -> str:
    """
    Человекочитаемый список товаров для письма.
    """
    lines = []
    for item in items:
        unit_price = float(item.unit_price or 0)
        line_amount = float(item.line_amount or 0)
        lines.append(
            f"- {item.name}: {item.quantity} шт x {unit_price} = {line_amount}"
        )
    return "\n".join(lines)


def send_order_notification_email(order: Order) -> None:
    """
    Основная функция: отправляет письмо админу/менеджеру
    о создании нового заказа, когда у нас уже есть объект Order.
    ЭТО ТА ФУНКЦИЯ, КОТОРУЮ ИМПОРТИРУЕТ manager_listener.
    """
    items: List[OrderItem] = list(getattr(order, "items", []))

    total = float(order.total_amount or 0)

    subject = f"Новый заказ #{order.id}"
    body = f"""
Новый заказ #{order.id}

Статус: {order.status}
Сумма: {total} руб.

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


def send_new_order_notification(order_id: int) -> None:
    """
    Старая функция-обёртка для обратной совместимости:
    принимает order_id, достаёт заказ из БД и вызывает send_order_notification_email.
    """
    order, _ = _get_order_with_items(order_id)
    if not order:
        return

    send_order_notification_email(order)
