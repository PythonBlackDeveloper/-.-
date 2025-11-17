# paycharm/bots/user_bot.py
import asyncio
import logging

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from paycharm.app.config import settings
from paycharm.app.database import SessionLocal
from paycharm.app.services.order_service import create_order_from_text
from paycharm.app.integrations.google_sheets import write_order_to_google_sheet
from paycharm.app.integrations.email_service import send_new_order_notification

logging.basicConfig(level=logging.INFO)

router = Router()


@router.message(CommandStart())
@router.message(Command("help"))
async def cmd_start(message: Message):
    text = (
        "Привет! 👋\n\n"
        "Напиши мне, что хочешь заказать, в свободной форме. Например:\n"
        "\"Хочу заказать: iPhone 15 - 2 шт, AirPods Pro - 1 шт. "
        "Доставка на ул. Ленина 15, кв 44. Email: ivanov@mail.ru, телефон +79161234567\""
    )
    await message.answer(text)


@router.message(F.text)
async def handle_order_message(message: Message):
    user_text = (message.text or "").strip()
    if not user_text:
        await message.answer("Сообщение пустое. Напиши, пожалуйста, что хочешь заказать 😊")
        return

    db = SessionLocal()
    try:
        # ⚠ Это синхронный код внутри async-хендлера.
        # Для учебного проекта можно так, но под нагрузкой стоит выносить в asyncio.to_thread(...)
        result = create_order_from_text(db, user_text)
        order_id = result["order_id"]
        status = result["status"]
        total = result["total"]

        # запись в Google Sheets
        write_order_to_google_sheet(order_id)

        # email менеджеру
        send_new_order_notification(order_id)

    except Exception:
        logging.exception("Ошибка при обработке заказа")
        await message.answer("Произошла ошибка при обработке заказа. Попробуй ещё раз или свяжись с менеджером.")
        return
    finally:
        db.close()

    lines = [
        f"Ваш заказ №{order_id} принят в систему ✅",
        f"Статус: {status}",
        f"Итоговая сумма: {total} руб.",
    ]

    if not result["email_ok"]:
        lines.append("⚠ Email указан некорректно — менеджер может уточнить его дополнительно.")
    if not result["phone_ok"]:
        lines.append("⚠ Телефон указан некорректно — менеджер может связаться с вами через другой канал.")
    if not result["all_in_stock"]:
        lines.append("⚠ Некоторых товаров может не быть в наличии — менеджер свяжется с вами для уточнения.")

    await message.answer("\n".join(lines))


async def main():
    bot = Bot(token=settings.TELEGRAM_USER_BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
