import sqlite3
import random
from datetime import datetime, timedelta

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
        password TEXT,
        is_verified INTEGER DEFAULT 0
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

    # OTP table: stores the active OTP code for each email
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS otp_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL,
        otp TEXT NOT NULL,
        expires_at DATETIME NOT NULL,
        used INTEGER DEFAULT 0
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

def generate_otp():
    """Generate a 6-digit OTP code"""
    return str(random.randint(100000, 999999))

def save_otp(email, otp):
    """Store an OTP for a given email, valid for 10 minutes"""
    conn = get_connection()
    cursor = conn.cursor()
    expires_at = (datetime.now() + timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S')
    # Invalidate any existing OTPs for this email
    cursor.execute("UPDATE otp_codes SET used=1 WHERE email=?", (email,))
    cursor.execute(
        "INSERT INTO otp_codes (email, otp, expires_at, used) VALUES (?, ?, ?, 0)",
        (email, otp, expires_at)
    )
    conn.commit()
    conn.close()

def verify_otp(email, otp_input):
    """Verify the OTP for an email. Returns True if valid, False otherwise."""
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(
        "SELECT id FROM otp_codes WHERE email=? AND otp=? AND used=0 AND expires_at > ?",
        (email, otp_input, now)
    )
    row = cursor.fetchone()
    if row:
        cursor.execute("UPDATE otp_codes SET used=1 WHERE id=?", (row[0],))
        conn.commit()
    conn.close()
    return row is not None