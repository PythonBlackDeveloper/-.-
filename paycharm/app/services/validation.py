# app/services/validation.py
import re
from typing import List, Dict, Tuple
from paycharm.app.utils.product_catalog import PRODUCTS

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+7\d{10}$")  # простой вариант РФ


def is_valid_email(email: str | None) -> bool:
    if not email:
        return False
    return bool(EMAIL_RE.match(email))


def is_valid_phone(phone: str | None) -> bool:
    if not phone:
        return False
    return bool(PHONE_RE.match(phone))


def check_items_availability(items: List[Dict]) -> Tuple[bool, List[Dict]]:
    """
    items: [{name: str, quantity: int}]
    return: (all_available, [ {name, quantity, available, unit_price} ])
    """
    result = []
    all_available = True
    for item in items:
        name = item["name"]
        quantity = item["quantity"]
        product = PRODUCTS.get(name)
        available = bool(product and product.get("in_stock"))
        if not available:
            all_available = False
        unit_price = product["price"] if product else 0
        result.append(
            {
                "name": name,
                "quantity": quantity,
                "available": available,
                "unit_price": unit_price,
            }
        )
    return all_available, result


def calculate_total(items_with_prices: List[Dict]) -> float:
    total = 0.0
    for item in items_with_prices:
        total += item["unit_price"] * item["quantity"]
    return total
