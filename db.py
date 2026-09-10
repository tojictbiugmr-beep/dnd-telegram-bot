"""
Хранение персонажей и состояния игры (GameDirector) в SQLite.
Единое соединение для потокобезопасности в asyncio.
"""

import sqlite3
import json


class Database:
    def __init__(self, db_path: str = "dnd_bot.db"):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS characters (
                user_id    INTEGER PRIMARY KEY,
                char_data  TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS game_state (
                chat_id    INTEGER PRIMARY KEY,
                state_data TEXT NOT NULL,
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        self._conn.commit()

    # ─── Персонажи ────────────────────────────────────────

    def save_character(self, user_id: int, char) -> None:
        self._conn.execute(
            """INSERT INTO characters (user_id, char_data, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(user_id) DO UPDATE SET
                 char_data = excluded.char_data,
                 updated_at = datetime('now')""",
            (user_id, json.dumps(char.to_dict())),
        )
        self._conn.commit()

    def get_character(self, user_id: int):
        from engine import Character
        row = self._conn.execute(
            "SELECT char_data FROM characters WHERE user_id = ?", (user_id,)
        ).fetchone()
        if row is None:
            return None
        return Character.from_dict(json.loads(row[0]))

    def delete_character(self, user_id: int) -> None:
        self._conn.execute("DELETE FROM characters WHERE user_id = ?", (user_id,))
        self._conn.commit()

    def list_all_characters(self) -> list:
        rows = self._conn.execute(
            "SELECT user_id, char_data, updated_at FROM characters ORDER BY updated_at DESC"
        ).fetchall()
        return [(r[0], json.loads(r[1]), r[2]) for r in rows]

    # ─── GameDirector ─────────────────────────────────────

    def save_director(self, chat_id: int, director) -> None:
        from director import GameDirector
        self._conn.execute(
            """INSERT INTO game_state (chat_id, state_data, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(chat_id) DO UPDATE SET
                 state_data = excluded.state_data,
                 updated_at = datetime('now')""",
            (chat_id, json.dumps(director.to_dict())),
        )
        self._conn.commit()

    def get_director(self, chat_id: int):
        """Возвращает GameDirector для чата или новый пустый."""
        from director import GameDirector
        row = self._conn.execute(
            "SELECT state_data FROM game_state WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        if row is None:
            return GameDirector()
        return GameDirector.from_dict(json.loads(row[0]))

    def delete_director(self, chat_id: int) -> None:
        self._conn.execute("DELETE FROM game_state WHERE chat_id = ?", (chat_id,))
        self._conn.commit()

    # ─── Произвольное состояние ──────────────────────────

    def save_game_state(self, chat_id: int, state: dict) -> None:
        self._conn.execute(
            """INSERT INTO game_state (chat_id, state_data, updated_at)
               VALUES (?, ?, datetime('now'))
               ON CONFLICT(chat_id) DO UPDATE SET
                 state_data = excluded.state_data,
                 updated_at = datetime('now')""",
            (chat_id, json.dumps(state)),
        )
        self._conn.commit()

    def get_game_state(self, chat_id: int) -> dict | None:
        row = self._conn.execute(
            "SELECT state_data FROM game_state WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    def delete_game_state(self, chat_id: int) -> None:
        self._conn.execute("DELETE FROM game_state WHERE chat_id = ?", (chat_id,))
        self._conn.commit()

    def close(self) -> None:
        s
        elf._conn.close()
