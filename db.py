"""
Хранение персонажей и состояния игры в SQLite.
"""

import sqlite3
import json


class Database:
    def __init__(self, db_path: str = "dnd_bot.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS characters (
                    user_id    INTEGER PRIMARY KEY,
                    char_data  TEXT NOT NULL,
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS game_state (
                    chat_id    INTEGER PRIMARY KEY,
                    state_data TEXT NOT NULL,
                    updated_at TEXT DEFAULT (datetime('now'))
                )
            """)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def save_character(self, user_id: int, char) -> None:
        data = char.to_dict()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO characters (user_id, char_data, updated_at)
                   VALUES (?, ?, datetime('now'))
                   ON CONFLICT(user_id) DO UPDATE SET
                     char_data = excluded.char_data,
                     updated_at = datetime('now')""",
                (user_id, json.dumps(data)),
            )

    def get_character(self, user_id: int):
        """Возвращает Character или None."""
        from engine import Character
        with self._conn() as conn:
            row = conn.execute(
                "SELECT char_data FROM characters WHERE user_id = ?", (user_id,)
            ).fetchone()
        if row is None:
            return None
        return Character.from_dict(json.loads(row[0]))

    def delete_character(self, user_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM characters WHERE user_id = ?", (user_id,))

    def save_game_state(self, chat_id: int, state: dict) -> None:
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO game_state (chat_id, state_data, updated_at)
                   VALUES (?, ?, datetime('now'))
                   ON CONFLICT(chat_id) DO UPDATE SET
                     state_data = excluded.state_data,
                     updated_at = datetime('now')""",
                (chat_id, json.dumps(state)),
            )

    def get_game_state(self, chat_id: int) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT state_data FROM game_state WHERE chat_id = ?", (chat_id,)
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def delete_game_state(self, chat_id: int) -> None:
        with self._conn() as conn:
            conn.execute("DELETE FROM game_state WHERE chat_id = ?", (chat_id,))

    def list_all_characters(self) -> list:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT user_id, char_data, updated_at FROM characters ORDER BY updated_at DESC"
            ).fetchall()
        return [(r[0], json.loads(r[1]), r[2]) for in rows]
