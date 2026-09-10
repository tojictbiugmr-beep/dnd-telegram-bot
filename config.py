"""
Конфигурация бота.
"""

import os
from dataclasses import dataclass


@dataclass
class BotConfig:
    BOT_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    DB_PATH: str = os.getenv("DB_PATH", "game.db")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = "groq/compound-mini"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"


config = BotConfig()
