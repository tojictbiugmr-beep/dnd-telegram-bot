"""
База данных SQLite: хранит персонажей и режиссёров.
Чистый JSON-контейнер, никакой бизнес-логики.
"""

import json
import sqlite3
import logging
from typing import Optional

log = logging.getLogger("dnd-bot.db")


class Database:
    def __init__(self, db_path: str = "game.db"):
        self.path = db_path
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    user_id INTEGER PRIMARY KEY,
                    data    TEXT NOT NULL
                )
            """)
            c.execute("""
                CREATE TABLE IF NOT EXISTS directors (
                    chat_id INTEGER PRIMARY KEY,
                    data    TEXT NOT NULL
                )
            """)
            c.commit()

    # ─── Персонажи ────────────────────────────────────────

    def get_character(self, user_id: int):
        with self._conn() as c:
            row = c.execute(
                "SELECT data FROM characters WHERE user_id = ?", (user_id,)
            ).fetchone()
            if row:
                from engine import Character
                return Character.from_dict(json.loads(row["data"]))
        return None

    def save_character(self, user_id: int, char) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO characters (user_id, data) VALUES (?, ?)",
                (user_id, json.dumps(char.to_dict())),
            )
            c.commit()

    def delete_character(self, user_id: int) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM characters WHERE user_id = ?", (user_id,))
            c.commit()

    # ─── Режиссёр ─────────────────────────────────────────

    def get_director(self, chat_id: int):
        from director import GameDirector
        with self._conn() as c:
            row = c.execute(
                "SELECT data FROM directors WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            if row:
                try:
                    return GameDirector.from_dict(json.loads(row["data"]))
                except Exception as e:
                    log.error(f"Не удалось прочитать director {chat_id}: {e}")
                    return GameDirector()
        return GameDirector()

    def save_director(self, chat_id: int, director) -> None:
        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO directors (chat_id, data) VALUES (?, ?)",
                (chat_id, json.dumps(director.to_dict())),
            )
            c.commit()

    def delete_director(self, chat_id: int) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM directors WHERE chat_id = ?", (chat_id,))
            c.commit()
