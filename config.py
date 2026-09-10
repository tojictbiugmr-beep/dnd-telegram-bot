"""
Конфигурация из переменных окружения (.env).
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    DB_PATH: str = os.getenv("DB_PATH", "dnd_bot.db")


config = Config()
