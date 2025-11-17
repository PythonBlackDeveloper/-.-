# paycharm/bots/admin_bot.py
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from paycharm.app.config import settings
from paycharm.app.database import SessionLocal
from paycharm.app.models import Order, StatusHistory
from paycharm.app.utils.enums import OrderStatus
from paycharm.app.integrations.google_sheets import update_order_in_google_sheet

logging.basicConfig(level=logging.INFO)

router = Router()


def _get_db():
    return SessionLocal()


@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_start(message: Message):
    text = (
        "Админ-бот заказов 📦\n\n"
        "/orders — последние заказы\n"
        "/order <id> — подробности заказа\n"
        "/set_status <id> <status> [YYYY-MM-DD] — сменить статус заказа\n\n"
        f"Доступные статусы: {[s.value for s in OrderStatus]}"
    )
    await message.answer(text)


@router.message(Command("orders"))
async def cmd_orders(message: Message):
    db = _get_db()
    try:
        orders = (
            db.query(Order)
            .order_by(Order.created_at.desc())
            .limit(10)
            .all()
        )
    finally:
        db.close()

    if not orders:
        await message.answer("Заказов пока нет.")
        return

    lines = ["Последние заказы:"]
    for o in orders:
        lines.append(
            f"#{o.id} | {o.created_at.strftime('%Y-%m-%d %H:%M')} | "
            f"{o.status} | {float(o.total_amount or 0)} руб."
        )

    await message.answer("\n".join(lines))


@router.message(Command("order"))
async def cmd_order(message: Message):
    parts = (message.text or "").strip().split()
    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer("Использование: /order <id>")
        return

    order_id = int(parts[1])

    db = _get_db()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
    finally:
        db.close()

    if not order:
        await message.answer(f"Заказ #{order_id} не найден.")
        return

    items_str = "; ".join([f"{i.name} x{i.quantity}" for i in order.items])

    text = (
        f"Заказ #{order.id}\n"
        f"Создан: {order.created_at}\n"
        f"Статус: {order.status}\n"
        f"Товары: {items_str}\n"
        f"Сумма: {float(order.total_amount or 0)} руб.\n"
        f"Адрес: {order.delivery_address or '-'}\n"
        f"Email: {order.contact_email or '-'}\n"
        f"Телефон: {order.contact_phone or '-'}\n"
        f"Ожидаемая доставка: {order.expected_delivery_date or '-'}\n"
        f"Фактическая доставка: {order.actual_delivery_date or '-'}\n"
    )

    await message.answer(text)


@router.message(Command("set_status"))
async def cmd_set_status(message: Message):
    """
    /set_status <order_id> <status> [YYYY-MM-DD]
    """
    parts = (message.text or "").strip().split()
    if len(parts) < 3:
        await message.answer("Использование: /set_status <order_id> <status> [YYYY-MM-DD]")
        return

    if not parts[1].isdigit():
        await message.answer("order_id должен быть числом.")
        return

    order_id = int(parts[1])
    new_status_str = parts[2]

    try:
        new_status = OrderStatus(new_status_str)
    except ValueError:
        await message.answer(f"Недопустимый статус. Доступные: {[s.value for s in OrderStatus]}")
        return

    expected_date = None
    if len(parts) >= 4:
        try:
            expected_date = datetime.strptime(parts[3], "%Y-%m-%d")
        except ValueError:
            await message.answer("Неверный формат даты. Используй YYYY-MM-DD.")
            return

    db = _get_db()
    try:
        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            await message.answer(f"Заказ #{order_id} не найден.")
            return

        old_status = order.status
        order.status = new_status.value

        if expected_date:
            order.expected_delivery_date = expected_date

        if new_status == OrderStatus.DELIVERED and not order.actual_delivery_date:
            order.actual_delivery_date = datetime.utcnow()

        history = StatusHistory(
            order_id=order.id,
            old_status=old_status,
            new_status=new_status.value,
            comment=f"Изменено через админ-бота @{message.from_user.username}",
        )
        db.add(history)

        db.commit()

        # обновляем строку в Google Sheets
        update_order_in_google_sheet(order.id)

    finally:
        db.close()

    await message.answer(
        f"Статус заказа #{order_id} изменён с {old_status} на {new_status.value}."
    )
    # Тут можно добавить уведомление пользователю, если в Order будет telegram_chat_id.


async def main():
    bot = Bot(token=settings.TELEGRAM_ADMIN_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
