# paycharm/app/services/ai_parser.py

from __future__ import annotations

import json
from typing import Dict, Any

import google.generativeai as genai

from paycharm.app.config import settings


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
Никаких комментариев, текста до или после JSON. Только чистый JSON.
"""


# Проверяем наличие ключа
if not settings.AI_KEY:
    raise RuntimeError(
        "AI_KEY не задан в .env. Укажи AI_KEY=... (ключ Gemini) и перезапусти."
    )

# Настройка Gemini SDK
genai.configure(api_key=settings.AI_KEY)

# ЖЁСТКО фиксируем модель, чтобы .env не ломал нам жизнь
MODEL_NAME = "gemini-pro"


def parse_order_text(text: str) -> Dict[str, Any]:
    """
    Отправляет текст заказа в модель Gemini и возвращает распарсенный JSON.
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)
    except Exception as e:
        raise RuntimeError(f"Ошибка инициализации модели Gemini '{MODEL_NAME}': {e}")

    prompt = f"{SYSTEM_PROMPT}\n\nТекст пользователя:\n{text}"

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
            },
        )
    except Exception as e:
        # Здесь будет, например, ошибка 404 модели, лимиты и т.д.
        raise RuntimeError(f"Ошибка запроса к модели Gemini: {e}")

    raw = (response.text or "").strip()

    # Пытаемся распарсить JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError(f"Не удалось распарсить JSON из ответа модели: {raw}")

    # Минимальная страховка по ключам
    data.setdefault("items", [])
    data.setdefault("delivery_address", "")
    data.setdefault("contact_email", "")
    data.setdefault("contact_phone", "")
    data.setdefault("status", "pending")

    return data
