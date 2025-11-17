# app/utils/enums.py
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    INVALID_CONTACT = "invalid_contact"
    OUT_OF_STOCK = "out_of_stock"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
