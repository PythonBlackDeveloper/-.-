# paycharm/app/integrations/google_sheets.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, List

import gspread
from google.oauth2.service_account import Credentials

from paycharm.app.config import settings
from paycharm.app.database import SessionLocal
from paycharm.app.models import Order, OrderItem


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_sheet():
    creds = Credentials.from_service_account_file(
        settings.GOOGLE_SHEETS_CREDENTIALS_PATH,
        scopes=SCOPES,
    )
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(settings.GOOGLE_SHEETS_SPREADSHEET_ID)
    # Для простоты — первый лист
    sheet = spreadsheet.sheet1
    return sheet


HEADER = [
    "Order ID",
    "Created At",
    "Status",
    "Items",
    "Total Amount",
    "Delivery Address",
    "Email",
    "Phone",
    "Expected Delivery",
    "Actual Delivery",
]


def _ensure_header(sheet):
    existing = sheet.row_values(1)
    if existing != HEADER:
        sheet.delete_rows(1)
        sheet.insert_row(HEADER, 1)


def _format_datetime(dt: Optional[datetime]) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _items_to_string(items: List[OrderItem]) -> str:
    parts = [f"{item.name} x{item.quantity}" for item in items]
    return "; ".join(parts)


def write_order_to_google_sheet(order_id: int) -> None:
    """Добавляем строку с заказом в конец таблицы."""
    db = SessionLocal()
    try:
        order: Order | None = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return

        items: List[OrderItem] = order.items

        sheet = _get_sheet()
        _ensure_header(sheet)

        row = [
            str(order.id),
            _format_datetime(order.created_at),
            order.status,
            _items_to_string(items),
            float(order.total_amount or 0),
            order.delivery_address or "",
            order.contact_email or "",
            order.contact_phone or "",
            _format_datetime(order.expected_delivery_date),
            _format_datetime(order.actual_delivery_date),
        ]

        sheet.append_row(row)
    finally:
        db.close()


def update_order_in_google_sheet(order_id: int) -> None:
    """
    Находит строку по Order ID и обновляет её (статус, суммы, даты).
    Если строка не найдена — ничего не делаем.
    """
    db = SessionLocal()
    try:
        order: Order | None = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            return

        items: List[OrderItem] = order.items

        sheet = _get_sheet()
        _ensure_header(sheet)

        # Ищем строку, где в первом столбце наш order_id
        records = sheet.get_all_values()
        # records[0] — заголовок
        row_index = None
        for i, row in enumerate(records[1:], start=2):  # начинаем с 2-й строки
            if row and row[0] == str(order.id):
                row_index = i
                break

        if row_index is None:
            # если нет — просто добавим новую строку
            write_order_to_google_sheet(order_id)
            return

        new_row = [
            str(order.id),
            _format_datetime(order.created_at),
            order.status,
            _items_to_string(items),
            float(order.total_amount or 0),
            order.delivery_address or "",
            order.contact_email or "",
            order.contact_phone or "",
            _format_datetime(order.expected_delivery_date),
            _format_datetime(order.actual_delivery_date),
        ]

        sheet.update(f"A{row_index}:J{row_index}", [new_row])
    finally:
        db.close()
