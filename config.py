"""
Конфигурация бота. Все настройки читаются из переменных окружения.
"""

import os
from dataclasses import dataclass


@dataclass
class BotConfig:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DB_PATH: str = os.getenv("DB_PATH", "game.db")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


config = BotConfig()
