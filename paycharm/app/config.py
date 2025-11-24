# paycharm/app/config.py

from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Читаем .env и игнорируем лишние переменные,
    # чтобы не падать, если в .env что-то ещё лежит
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # === БАЗА ДАННЫХ (обязательно) ===
    DATABASE_URL: str

    # === ИИ (Gemini / gmini) ===
    # Ключ для Google Gemini (gmini)
    AI_KEY: Optional[str] = None

    # Можно вынести имя модели в конфиг, чтобы не хардкодить в ai_parser
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # === Telegram (боты / kurigram) ===
    TELEGRAM_USER_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ADMIN_BOT_TOKEN: Optional[str] = None

    TG_API_ID: Optional[int] = None       # для pyrogram/kurigram клиента
    TG_API_HASH: Optional[str] = None
    ADMIN_TELEGRAM_ID: Optional[int] = None

    # === Google Sheets ===
    GOOGLE_SHEETS_CREDENTIALS_PATH: Optional[str] = None
    GOOGLE_SHEETS_SPREADSHEET_ID: Optional[str] = None

    # === Email (SMTP) ===
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    ORDER_NOTIFICATION_EMAIL: Optional[str] = None


settings = Settings()

