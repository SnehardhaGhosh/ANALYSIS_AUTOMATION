from flask import redirect, request, jsonify,session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from api import auth_bp

DB_PATH = "instance/database.db"


def get_db():
    return sqlite3.connect(DB_PATH)


@auth_bp.route('/register', methods=['POST'])
def register():
    username = request.form.get("username")
    email = request.form.get("email")
    password = generate_password_hash(request.form.get("password"))
    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, password)
        )
        conn.commit()
        return jsonify({"message": "User registered successfully"})
    except:
        return jsonify({"error": "Email already exists"}), 400
    finally:
        conn.close()


@auth_bp.route('/login', methods=['POST'])
def login():
    email = request.form.get("email")
    password = request.form.get("password")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cursor.fetchone()
    conn.close()

    if user and check_password_hash(user[3], password):
        session['user_id'] = user[0]   # 🔥 ADD THIS
        return redirect('/dashboard')
    else:
        return "Invalid credentials"


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = request.form.get("email")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email=?", (email,))
    user = cursor.fetchone()

    if user:
        return jsonify({"message": "Password reset link (mock)"})
    else:
        return jsonify({"error": "Email not found"}), 404