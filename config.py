"""
Конфигурация из переменных окружения.
Локально: читает .env через python-dotenv.
На Bothost: переменные задаются в панели хостинга.
"""

import os

# Локально загружаем .env (на Bothost файла нет — тихо пропускается)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    # Bothost автоматически подставляет BOT_TOKEN
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")

    # GROQ_API_KEY добавляется вручную в панели Bothost
    GRGROQ_MODEL: str = os.getenv("GROQ_MODEL", "compound-mini")

    # SQLite: на Bothost контейнер пересоздаётся при деплое,
    # поэтому БД лучше класть в /tmp (сохраняется между рестартами,
    # но не между деплоями). Для персистентности — использовать
    # PostgreSQL/Redis из тарифа Pro.
    DB_PATH: str = os.getenv("DB_PATH", "/tmp/dnd_bot.db")


config = Config()
