import logging
from contextlib import contextmanager
from datetime import datetime

from pyrogram import Client, filters
from pyrogram.types import Message

from paycharm.app.config import settings
from paycharm.app.database import SessionLocal
from paycharm.app.services.order_service import (
    list_recent_orders,
    get_order_by_id,
    set_order_status,
    get_sales_metrics,
    get_delivery_metrics,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def is_admin(message: Message) -> bool:
    """
    Простейшая проверка, что пишет именно админ.
    В settings.ADMIN_TELEGRAM_ID можно хранить id админа (int).
    Если не хочешь ограничивать — верни просто True.
    """
    admin_id = getattr(settings, "ADMIN_TELEGRAM_ID", None)
    if admin_id is None:
        # если не задали — не ограничиваем
        return True
    return message.from_user and message.from_user.id == admin_id


def require_admin(func):
    """Декоратор, проверяющий, что команду вызывает админ."""

    async def wrapper(client: Client, message: Message):
        if not is_admin(message):
            await message.reply("⛔ У вас нет прав для использования этого бота.")
            return
        return await func(client, message)

    return wrapper


def format_order_short(order) -> str:
    created_at = getattr(order, "created_at", None)
    created_str = created_at.strftime("%Y-%m-%d %H:%M") if isinstance(created_at, datetime) else "—"
    status = getattr(order, "status", "unknown")
    total = getattr(order, "total_price", "?")
    currency = getattr(order, "currency", "₽")
    return f"#{order.id} | {created_str} | {status} | {total} {currency}"


def format_order_full(order) -> str:
    lines = [f"🧾 Заказ #{order.id}"]
    created_at = getattr(order, "created_at", None)
    created_str = created_at.strftime("%Y-%m-%d %H:%M") if isinstance(created_at, datetime) else "—"
    status = getattr(order, "status", "unknown")
    total = getattr(order, "total_price", "?")
    currency = getattr(order, "currency", "₽")

    lines.append(f"Дата создания: {created_str}")
    lines.append(f"Статус: {status}")
    lines.append(f"Сумма: {total} {currency}")

    addr = getattr(order, "delivery_address", None)
    if addr:
        lines.append(f"Адрес: {addr}")

    email = getattr(order, "contact_email", None)
    phone = getattr(order, "contact_phone", None)
    if email or phone:
        lines.append("Контакты:")
        if email:
            lines.append(f"  • Email: {email}")
        if phone:
            lines.append(f"  • Телефон: {phone}")

    if getattr(order, "items", None):
        lines.append("")
        lines.append("Товары:")
        for item in order.items:
            name = getattr(item, "name", "Товар")
            qty = getattr(item, "quantity", 1)
            price = getattr(item, "total_price", None)
            if price is not None:
                lines.append(f"  • {name} — {qty} шт, {price} {currency}")
            else:
                lines.append(f"  • {name} — {qty} шт")

    # Даты доставки
    expected = getattr(order, "expected_delivery_date", None)
    actual = getattr(order, "actual_delivery_date", None)
    if expected or actual:
        lines.append("")
        if expected:
            if isinstance(expected, datetime):
                expected_str = expected.strftime("%Y-%m-%d")
            else:
                expected_str = str(expected)
            lines.append(f"Ожидаемая дата доставки: {expected_str}")
        if actual:
            if isinstance(actual, datetime):
                actual_str = actual.strftime("%Y-%m-%d")
            else:
                actual_str = str(actual)
            lines.append(f"Фактическая дата доставки: {actual_str}")

    return "\n".join(lines)


# ==========================
#  Kurigram / Pyrogram Client
# ==========================

admin_app = Client(
    "admin_bot",
    api_id=settings.TG_API_ID,
    api_hash=settings.TG_API_HASH,
    bot_token=settings.TELEGRAM_ADMIN_BOT_TOKEN,
)


@admin_app.on_message(filters.command("start"))
@require_admin
async def cmd_start(client: Client, message: Message):
    text = (
        "👋 Привет, админ!\n\n"
        "Доступные команды:\n"
        "/orders — последние заказы\n"
        "/order <id> — детали заказа\n"
        "/set_status <id> <status> [YYYY-MM-DD] — сменить статус (и, опционально, дату доставки)\n"
        "/stats — метрики продаж и доставки\n"
    )
    await message.reply(text)


@admin_app.on_message(filters.command("orders"))
@require_admin
async def cmd_orders(client: Client, message: Message):
    args = message.command  # ['/orders', '10'] например
    limit = 10
    if len(args) > 1:
        try:
            limit = int(args[1])
        except ValueError:
            pass

    with db_session() as db:
        orders = list_recent_orders(db, limit=limit)

    if not orders:
        await message.reply("Пока нет заказов.")
        return

    lines = ["📋 Последние заказы:"]
    for order in orders:
        lines.append(format_order_short(order))

    await message.reply("\n".join(lines))


@admin_app.on_message(filters.command("order"))
@require_admin
async def cmd_order(client: Client, message: Message):
    args = message.command  # ['/order', '123']
    if len(args) < 2:
        await message.reply("Использование: /order <id>")
        return

    try:
        order_id = int(args[1])
    except ValueError:
        await message.reply("ID заказа должен быть числом.")
        return

    with db_session() as db:
        order = get_order_by_id(db, order_id)

    if not order:
        await message.reply(f"Заказ #{order_id} не найден.")
        return

    await message.reply(format_order_full(order))


@admin_app.on_message(filters.command("set_status"))
@require_admin
async def cmd_set_status(client: Client, message: Message):
    """
    /set_status <id> <status> [YYYY-MM-DD]

    Примеры:
      /set_status 123 shipped 2025-11-20
      /set_status 123 delivered
    """
    args = message.command
    if len(args) < 3:
        await message.reply("Использование: /set_status <id> <status> [YYYY-MM-DD]")
        return

    try:
        order_id = int(args[1])
    except ValueError:
        await message.reply("ID заказа должен быть числом.")
        return

    new_status = args[2]
    expected_date = None

    if len(args) >= 4:
        try:
            expected_date = datetime.strptime(args[3], "%Y-%m-%d").date()
        except ValueError:
            await message.reply("Дата должна быть в формате YYYY-MM-DD (например, 2025-11-18).")
            return

    with db_session() as db:
        try:
            order = set_order_status(
                db=db,
                order_id=order_id,
                new_status=new_status,
                expected_delivery_date=expected_date,
            )
        except Exception as e:
            logger.exception("Ошибка при смене статуса заказа: %s", e)
            await message.reply("Не удалось обновить статус заказа.")
            return

    # Здесь предполагается, что set_order_status:
    #   - обновляет БД
    #   - обновляет Google Sheets
    #   - шлёт уведомление пользователю (по telegram_user_id / chat_id)
    # Если нет — можно реализовать это внутри order_service.py

    await message.reply(f"✅ Статус заказа #{order.id} обновлён на '{order.status}'.")


@admin_app.on_message(filters.command("stats"))
@require_admin
async def cmd_stats(client: Client, message: Message):
    """
    /stats [days]
    По умолчанию — за 30 дней.
    """
    args = message.command
    days = 30
    if len(args) >= 2:
        try:
            days = int(args[1])
        except ValueError:
            pass

    with db_session() as db:
        sales = get_sales_metrics(db, days=days)
        delivery = get_delivery_metrics(db, days=days)

    # Ожидаемый формат sales / delivery:
    # sales = {
    #   "total_revenue": ...,
    #   "total_orders": ...,
    #   "by_day": [{"date": date, "orders": int, "revenue": Decimal}, ...]
    # }
    # delivery = {
    #   "avg_delay_days": ...,
    #   "on_time": int,
    #   "late": int,
    #   "by_day": [...]
    # }

    lines = [f"📊 Статистика за последние {days} дней:"]

    if sales:
        lines.append("")
        lines.append("💵 Продажи:")
        total_rev = sales.get("total_revenue", 0)
        total_orders = sales.get("total_orders", 0)
        lines.append(f"  • Заказов: {total_orders}")
        lines.append(f"  • Общая выручка: {total_rev}")

        by_day = sales.get("by_day") or []
        if by_day:
            lines.append("  • По дням:")
            for row in by_day:
                d = row.get("date")
                orders_count = row.get("orders")
                revenue = row.get("revenue")
                d_str = d.strftime("%Y-%m-%d") if hasattr(d, "strftime") else str(d)
                lines.append(f"    - {d_str}: {orders_count} заказов, {revenue} ₽")

    if delivery:
        lines.append("")
        lines.append("🚚 Доставка:")
        avg_delay = delivery.get("avg_delay_days")
        on_time = delivery.get("on_time")
        late = delivery.get("late")

        if avg_delay is not None:
            lines.append(f"  • Среднее отклонение по доставке: {avg_delay:.2f} дн.")
        if on_time is not None and late is not None:
            lines.append(f"  • В срок: {on_time}, с задержкой: {late}")

    await message.reply("\n".join(lines))


if __name__ == "__main__":
    logger.info("Запуск admin_bot (kurigram/pyrogram)…")
    admin_app.run()
