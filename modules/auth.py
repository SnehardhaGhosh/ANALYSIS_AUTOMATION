from werkzeug.security import generate_password_hash, check_password_hash
from modules.db import get_connection


def create_user(username, email, password):
    conn = get_connection()
    cursor = conn.cursor()

    hashed_password = generate_password_hash(password)

    cursor.execute(
        "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
        (username, email, hashed_password)
    )

    conn.commit()
    conn.close()


def verify_user(email, password):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cursor.fetchone()

    conn.close()

    if user and check_password_hash(user[3], password):
        return user
    return None