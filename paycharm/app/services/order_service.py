# app/services/order_service.py
from typing import Dict, Any
from sqlalchemy.orm import Session

from paycharm.app.models import Order, OrderItem, StatusHistory
from paycharm.app.utils.enums import OrderStatus
from paycharm.app.services.validation import (
    is_valid_email,
    is_valid_phone,
    check_items_availability,
    calculate_total,
)
from paycharm.app.services.ai_parser import parse_order_text


def create_order_from_text(db: Session, message_text: str) -> Dict[str, Any]:
    """
    Главная функция: принимает текст сообщения пользователя,
    парсит через AI, валидирует, создаёт заказ в БД и возвращает инфу.
    """

    parsed = parse_order_text(message_text)

    items = parsed.get("items") or []
    delivery_address = parsed.get("delivery_address") or ""
    contact_email = parsed.get("contact_email") or ""
    contact_phone = parsed.get("contact_phone") or ""

    email_ok = is_valid_email(contact_email)
    phone_ok = is_valid_phone(contact_phone)

    all_in_stock, items_with_prices = check_items_availability(items)
    total = calculate_total(items_with_prices)

    status = OrderStatus.PENDING
    if not email_ok or not phone_ok:
        status = OrderStatus.INVALID_CONTACT
    if not all_in_stock:
        status = OrderStatus.OUT_OF_STOCK

    order = Order(
        status=status.value,
        delivery_address=delivery_address,
        contact_email=contact_email,
        contact_phone=contact_phone,
        total_amount=total,
        source_message=message_text,
    )
    db.add(order)
    db.flush()  # получим order.id до commit

    for item in items_with_prices:
        line_amount = item["unit_price"] * item["quantity"]
        order_item = OrderItem(
            order_id=order.id,
            name=item["name"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            line_amount=line_amount,
        )
        db.add(order_item)

    # История статусов
    history = StatusHistory(
        order_id=order.id,
        old_status=None,
        new_status=status.value,
        comment="Order created from user message",
    )
    db.add(history)

    db.commit()
    db.refresh(order)

    return {
        "order_id": order.id,
        "status": order.status,
        "total": float(order.total_amount),
        "email_ok": email_ok,
        "phone_ok": phone_ok,
        "all_in_stock": all_in_stock,
    }
