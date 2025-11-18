import logging
from contextlib import contextmanager

from pyrogram import Client, filters
from pyrogram.types import Message

from paycharm.app.config import settings
from paycharm.app.database import SessionLocal
from paycharm.app.services.order_service import create_order_from_text
from paycharm.app.integrations.google_sheets import append_order_to_sheet
from paycharm.app.integrations.email_service import send_order_notification_email

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@contextmanager
def db_session():
    """Контекстный менеджер для сессии БД."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def format_order_summary(order) -> str:
    """
    Красивый текст для ответа пользователю.
    Предполагаем у order:
      - id
      - total_price
      - currency (опционально)
      - status
      - items (relationship), у items: name, quantity
    """
    lines = [f"✅ Ваш заказ №{order.id} принят!"]

    # Состав заказа
    if getattr(order, "items", None):
        lines.append("")
        lines.append("🧾 Состав заказа:")
        for item in order.items:
            # предполагаем поля name и quantity
            name = getattr(item, "name", "Товар")
            qty = getattr(item, "quantity", 1)
            lines.append(f"• {name} — {qty} шт")

    # Итоговая сумма
    total_price = getattr(order, "total_price", None)
    currency = getattr(order, "currency", "₽")

    if total_price is not None:
        lines.append("")
        lines.append(f"💰 Итоговая сумма: {total_price} {currency}")

    # Статус
    status = getattr(order, "status", "pending")
    lines.append("")
    lines.append(f"📦 Текущий статус: {status}")

    lines.append("")
    lines.append("Мы свяжемся с вами, когда заказ будет обработан 🙌")

    return "\n".join(lines)


# ==========================
#  Pyrogram / Kurigram Client
# ==========================

# Важно:
# kurigram ставится командой `pip install kurigram`,
# но импорт остаётся из `pyrogram`, как в официальных примерах.

app = Client(
    "manager_account",  # имя сессии (файл manager_account.session)
    api_id=settings.TG_API_ID,      # добавь в Settings
    api_hash=settings.TG_API_HASH,  # добавь в Settings
    # первый запуск попросит телефон / код в консоли
)


@app.on_message(filters.private & ~filters.me)
async def handle_new_message(client: Client, message: Message):
    """
    Ловим новые личные сообщения на аккаунт менеджера.

    Поток:
      1. Берём текст сообщения
      2. Парсим и создаём заказ через create_order_from_text
      3. Пишем заказ в Google Sheets
      4. Шлём уведомление на email
      5. Отвечаем пользователю суммой и статусом
    """
    if not (message.text or message.caption):
        await message.reply("Я вижу только медиа без текста, пришлите, пожалуйста, текст заказа 🙏")
        return

    raw_text = message.text or message.caption
    user_id = message.from_user.id
    chat_id = message.chat.id

    logger.info("Получено новое сообщение от %s: %s", user_id, raw_text)

    with db_session() as db:
        try:
            # ВАЖНО:
            # предполагаем, что create_order_from_text умеет принимать
            # telegram_user_id и telegram_chat_id (можно добавить эти поля в функцию)
            order = create_order_from_text(
                db=db,
                raw_text=raw_text,
                telegram_user_id=user_id,
                telegram_chat_id=chat_id,
            )

            # Пишем в Google Sheets
            try:
                append_order_to_sheet(order)
            except Exception as e:
                logger.exception("Ошибка при записи заказа в Google Sheets: %s", e)

            # Email уведомление админу/менеджеру
            try:
                send_order_notification_email(order)
            except Exception as e:
                logger.exception("Ошибка при отправке email уведомления: %s", e)

            # Ответ пользователю
            reply_text = format_order_summary(order)
            await message.reply(reply_text)

        except Exception as e:
            logger.exception("Ошибка при обработке заказа: %s", e)
            await message.reply(
                "❌ Не удалось обработать заказ. "
                "Проверьте, пожалуйста, корректность данных (товары, адрес, email, телефон) "
                "или попробуйте ещё раз."
            )


if __name__ == "__main__":
    logger.info("Запуск слушателя менеджера (kurigram/pyrogram)…")
    app.run()
