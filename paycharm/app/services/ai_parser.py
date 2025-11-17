# app/services/ai_parser.py
import json
from typing import Dict, Any
import openai
from paycharm.app.config import settings

openai.api_key = settings.OPENAI_API_KEY


SYSTEM_PROMPT = """
Ты — система обработки заказов. Пользователь пишет текстом, что хочет купить.
Твоя задача — выделить товары, адрес доставки, email и телефон.
Верни строго JSON без пояснений.

Формат:
{
  "items": [
    {"name": "iPhone 15", "quantity": 2},
    {"name": "AirPods Pro", "quantity": 1}
  ],
  "delivery_address": "ул. Ленина 15, кв 44",
  "contact_email": "ivanov@mail.ru",
  "contact_phone": "+79161234567",
  "status": "pending"
}

Если каких-то данных нет — ставь null или пустую строку.
"""


def parse_order_text(text: str) -> Dict[str, Any]:
    # Тут использую generic GPT, ты подставишь нужную модель
    completion = openai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.1,
    )
    raw = completion.choices[0].message.content.strip()

    # Пытаемся распарсить JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # На проде стоило бы логировать и кидать ошибку/перепарсивать
        raise ValueError(f"Не удалось распарсить JSON из ответа модели: {raw}")

    return data
