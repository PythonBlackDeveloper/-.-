# paycharm/app/services/order_service.py

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple

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


# ==========================
#  Создание заказа из текста
# ==========================

def create_order_from_text(
    db: Session,
    raw_text: str,
    telegram_user_id: Optional[int] = None,
    telegram_chat_id: Optional[int] = None,
) -> Order:
    """
    Главная функция: принимает текст сообщения пользователя,
    парсит через AI, валидирует, создаёт заказ в БД и возвращает объект Order.

    raw_text — исходный текст сообщения (из Telegram).
    telegram_user_id / telegram_chat_id — опциональные идентификаторы,
    можно использовать для отправки уведомлений при смене статуса.
    """

    parsed: Dict[str, Any] = parse_order_text(raw_text)

    items = parsed.get("items") or []
    delivery_address = parsed.get("delivery_address") or ""
    contact_email = parsed.get("contact_email") or ""
    contact_phone = parsed.get("contact_phone") or ""

    # Валидация контактов
    email_ok = is_valid_email(contact_email)
    phone_ok = is_valid_phone(contact_phone)

    # Проверка наличия и цен
    all_in_stock, items_with_prices = check_items_availability(items)
    total = calculate_total(items_with_prices)  # Decimal или float

    # Определяем статус
    status = OrderStatus.PENDING
    if not email_ok or not phone_ok:
        status = OrderStatus.INVALID_CONTACT
    if not all_in_stock:
        status = OrderStatus.OUT_OF_STOCK

    # Сбор kwargs для Order (поддерживаем опциональные поля)
    order_kwargs: Dict[str, Any] = dict(
        status=status.value,
        delivery_address=delivery_address,
        contact_email=contact_email,
        contact_phone=contact_phone,
        total_amount=total,
        source_message=raw_text,
    )

    # Если в модели Order есть поля telegram_user_id / telegram_chat_id — заполним
    if telegram_user_id is not None and hasattr(Order, "telegram_user_id"):
        order_kwargs["telegram_user_id"] = telegram_user_id
    if telegram_chat_id is not None and hasattr(Order, "telegram_chat_id"):
        order_kwargs["telegram_chat_id"] = telegram_chat_id

    order = Order(**order_kwargs)
    db.add(order)
    db.flush()  # получим order.id до commit

    # Позиции заказа
    for item in items_with_prices:
        unit_price = item["unit_price"]
        quantity = item["quantity"]
        line_amount = unit_price * quantity

        order_item = OrderItem(
            order_id=order.id,
            name=item["name"],
            quantity=quantity,
            unit_price=unit_price,
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
    return order


# ==========================
#  Вспомогательные функции для админки
# ==========================

def list_recent_orders(db: Session, limit: int = 10) -> List[Order]:
    """
    Вернуть последние N заказов по дате создания (убывание).
    """
    return (
        db.query(Order)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .all()
    )


def get_order_by_id(db: Session, order_id: int) -> Optional[Order]:
    """
    Найти заказ по ID.
    """
    return db.query(Order).filter(Order.id == order_id).first()


def set_order_status(
    db: Session,
    order_id: int,
    new_status: str,
    expected_delivery_date: Optional[date] = None,
) -> Order:
    """
    Сменить статус заказа, дополнительно можно указать ожидаемую дату доставки.

    Логика:
      - находим заказ
      - пишем запись в StatusHistory
      - при статусе DELIVERED ставим actual_delivery_date (если не стоит)
      - сохраняем и возвращаем обновлённый заказ
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise ValueError(f"Order with id={order_id} not found")

    # Если используем enum — проверим, что такой статус существует
    try:
        os = OrderStatus(new_status)
        status_value = os.value
    except ValueError:
        # Если значение не из enum — всё равно сохраняем строку,
        # но можно выбросить ошибку, если хочешь строгий контроль.
        status_value = new_status

    old_status = order.status
    order.status = status_value

    if expected_delivery_date is not None:
        # предполагаем, что поле в модели: expected_delivery_date (Date/DateTime)
        order.expected_delivery_date = expected_delivery_date

    # Если заказ доставлен — пометим фактическую дату доставки
    try:
        delivered_status = OrderStatus.DELIVERED.value
    except Exception:
        delivered_status = "delivered"

    if status_value == delivered_status and getattr(order, "actual_delivery_date", None) is None:
        order.actual_delivery_date = datetime.utcnow()

    # История статусов
    history = StatusHistory(
        order_id=order.id,
        old_status=old_status,
        new_status=status_value,
        comment="Status changed via admin bot",
    )
    db.add(history)

    db.commit()
    db.refresh(order)
    return order


# ==========================
#  Метрики продажи и доставки
# ==========================

def get_sales_metrics(db: Session, days: int = 30) -> Dict[str, Any]:
    """
    Метрики продаж за последние N дней:
      - total_revenue
      - total_orders
      - by_day: список {date, orders, revenue}
    """
    now = datetime.utcnow()
    date_from = now - timedelta(days=days)

    orders: List[Order] = (
        db.query(Order)
        .filter(Order.created_at >= date_from)
        .all()
    )

    total_revenue = Decimal("0")
    total_orders = len(orders)

    by_day_map: Dict[date, Dict[str, Any]] = defaultdict(lambda: {"orders": 0, "revenue": Decimal("0")})

    for order in orders:
        total_amount = getattr(order, "total_amount", None) or Decimal("0")
        if not isinstance(total_amount, Decimal):
            total_amount = Decimal(str(total_amount))

        created_at: datetime = getattr(order, "created_at", now)
        day = created_at.date()

        total_revenue += total_amount
        by_day_map[day]["orders"] += 1
        by_day_map[day]["revenue"] += total_amount

    by_day_list = []
    for d, data in sorted(by_day_map.items(), key=lambda x: x[0]):
        by_day_list.append(
            {
                "date": d,
                "orders": data["orders"],
                "revenue": data["revenue"],
            }
        )

    return {
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "by_day": by_day_list,
    }


def get_delivery_metrics(db: Session, days: int = 30) -> Dict[str, Any]:
    """
    Метрики по доставке:
      - avg_delay_days: среднее отклонение (фактическая - ожидаемая) в днях
      - on_time: сколько заказов доставлено вовремя или раньше
      - late: сколько заказов доставлено позже
      - by_day: можно добавить детализированную статистику по датам (опционально)
    """
    now = datetime.utcnow()
    date_from = now - timedelta(days=days)

    # Берём заказы, у которых есть хотя бы ожидаемая или фактическая дата доставки
    orders: List[Order] = (
        db.query(Order)
        .filter(Order.created_at >= date_from)
        .all()
    )

    delays: List[int] = []
    on_time = 0
    late = 0

    for order in orders:
        expected = getattr(order, "expected_delivery_date", None)
        actual = getattr(order, "actual_delivery_date", None)

        if not expected or not actual:
            # если нет пары дат — пропускаем
            continue

        # нормализуем к date
        if isinstance(expected, datetime):
            expected_date = expected.date()
        else:
            expected_date = expected

        if isinstance(actual, datetime):
            actual_date = actual.date()
        else:
            actual_date = actual

        delay_days = (actual_date - expected_date).days
        delays.append(delay_days)
        if delay_days <= 0:
            on_time += 1
        else:
            late += 1

    avg_delay = None
    if delays:
        avg_delay = sum(delays) / len(delays)

    return {
        "avg_delay_days": avg_delay,
        "on_time": on_time,
        "late": late,
        # сюда можно добавить "by_day", если понадобится детальнее
    }
