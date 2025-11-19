# paycharm/app/services/metrics_service.py

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, date
from decimal import Decimal
from typing import Dict, Any, List, Optional

from sqlalchemy.orm import Session

from paycharm.app.models import Order


def _to_decimal(value) -> Decimal:
    """
    Аккуратно приводим любые деньги/суммы к Decimal.
    """
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def get_sales_metrics(db: Session, days: int = 30) -> Dict[str, Any]:
    """
    Метрики продаж за последние N дней.

    Возвращает словарь формата:
    {
        "total_revenue": Decimal,
        "total_orders": int,
        "by_day": [
            {"date": date, "orders": int, "revenue": Decimal},
            ...
        ],
    }
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
        total_amount = _to_decimal(getattr(order, "total_amount", 0))
        created_at: datetime = getattr(order, "created_at", now)
        day = created_at.date()

        total_revenue += total_amount
        by_day_map[day]["orders"] += 1
        by_day_map[day]["revenue"] += total_amount

    by_day_list: List[Dict[str, Any]] = []
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
    Метрики по доставке за последние N дней.

    Возвращает словарь формата:
    {
        "avg_delay_days": float | None,
        "on_time": int,
        "late": int,
    }

    delay = actual_delivery_date - expected_delivery_date (в днях).
    on_time — delay <= 0
    late    — delay > 0
    """
    now = datetime.utcnow()
    date_from = now - timedelta(days=days)

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
            continue

        # Приводим к date
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

    avg_delay: Optional[float] = None
    if delays:
        avg_delay = sum(delays) / len(delays)

    return {
        "avg_delay_days": avg_delay,
        "on_time": on_time,
        "late": late,
    }
