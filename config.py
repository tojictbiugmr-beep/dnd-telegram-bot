"""
Конфигурация из переменных окружения.
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL = os.getenv("GROQ_MODEL", "compound-mini")
    DB_PATH = os.getenv("DB_PATH", "/tmp/dnd_bot.db")


config = Config()
