import sqlite3
import json
from director import GameDirector

DB_PATH = "game.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS directors (
            chat_id INTEGER PRIMARY KEY,
            data TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def save_director(chat_id: int, director: GameDirector):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    data_json = json.dumps(director.to_dict())
    cursor.execute('''
        INSERT OR REPLACE INTO directors (chat_id, data) VALUES (?, ?)
    ''', (chat_id, data_json))
    conn.commit()
    conn.close()

def get_director(chat_id: int) -> GameDirector:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT data FROM directors WHERE chat_id = ?', (chat_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        data = json.loads(row)
        return GameDirector.from_dict(data)
    return GameDirector()
