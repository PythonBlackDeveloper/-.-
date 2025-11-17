# app/config.py
from pydantic_settings import BaseSettings
from pydantic import AnyUrl


class Settings(BaseSettings):
    # DB
    DATABASE_URL: AnyUrl

    # LLM
    OPENAI_API_KEY: str

    # Telegram
    TELEGRAM_USER_BOT_TOKEN: str
    TELEGRAM_ADMIN_BOT_TOKEN: str

    # Google Sheets
    GOOGLE_SHEETS_CREDENTIALS_PATH: str
    GOOGLE_SHEETS_SPREADSHEET_ID: str

    # Email
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    ORDER_NOTIFICATION_EMAIL: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
