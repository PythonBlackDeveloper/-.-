# paycharm/app/config.py

from __future__ import annotations

from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # говорим, что надо читать .env и игнорировать любые лишние переменные
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # <- ВАЖНО: не ругаться на tg_api_id и прочее
    )

    # === Обязательная штука ===
    DATABASE_URL: str

    # === Остальное — опционально ===
    OPENAI_API_KEY: Optional[str] = None

    TELEGRAM_USER_BOT_TOKEN: Optional[str] = None
    TELEGRAM_ADMIN_BOT_TOKEN: Optional[str] = None

    GOOGLE_SHEETS_CREDENTIALS_PATH: Optional[str] = None
    GOOGLE_SHEETS_SPREADSHEET_ID: Optional[str] = None

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    ORDER_NOTIFICATION_EMAIL: Optional[str] = None

    TG_API_ID: Optional[int] = None
    TG_API_HASH: Optional[str] = None
    ADMIN_TELEGRAM_ID: Optional[int] = None


settings = Settings()
