import sqlite3

DB_PATH = "instance/database.db"

def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        query TEXT,
        response TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()

def save_chat(user_id, query, response):
    """Save chat message to database"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (user_id, query, response) VALUES (?, ?, ?)",
        (user_id, query, response)
    )
    conn.commit()
    conn.close()

def get_chat_history(user_id):
    """Retrieve chat history for a user"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT query, response, timestamp FROM chat_history WHERE user_id = ? ORDER BY timestamp ASC",
        (user_id,)
    )
    results = cursor.fetchall()
    conn.close()
    return results