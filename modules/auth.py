import smtplib
import os
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from werkzeug.security import generate_password_hash, check_password_hash
from modules.db import get_connection, generate_otp, save_otp

logger = logging.getLogger(__name__)

MAIL_EMAIL = os.getenv("MAIL_EMAIL", "")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "")


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


def send_otp_email(to_email, otp, username="User"):
    """
    Sends a beautiful HTML OTP email via Gmail SMTP.
    Requires MAIL_EMAIL and MAIL_PASSWORD to be set in .env
    """
    if not MAIL_EMAIL or not MAIL_PASSWORD or MAIL_EMAIL == "your_gmail@gmail.com":
        logger.warning("Email OTP not configured. Logging OTP to console for development.")
        logger.info(f"[DEV MODE] OTP for {to_email}: {otp}")
        return True  # Return True so the flow continues in dev mode

    try:
        subject = "Your AI Data Analyst Verification Code"
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <body style="margin:0;padding:0;font-family:'Inter',sans-serif;background:#f0f4ff;">
          <div style="max-width:560px;margin:40px auto;background:white;border-radius:20px;overflow:hidden;box-shadow:0 10px 40px rgba(0,0,0,0.08);">
            <div style="background:linear-gradient(135deg,#3b82f6,#8b5cf6);padding:40px 40px 30px;text-align:center;">
              <h1 style="color:white;margin:0;font-size:24px;letter-spacing:-1px;">&#128274; Verification Code</h1>
              <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px;">AI Data Analyst Platform</p>
            </div>
            <div style="padding:40px;">
              <p style="color:#374151;font-size:16px;margin:0 0 8px;">Hi <strong>{username}</strong>,</p>
              <p style="color:#6b7280;font-size:14px;margin:0 0 30px;">Use the verification code below to complete your login. This code expires in <strong>10 minutes</strong>.</p>
              <div style="background:#f0f4ff;border:2px dashed #c7d2fe;border-radius:16px;padding:28px;text-align:center;margin-bottom:30px;">
                <p style="margin:0 0 6px;color:#6b7280;font-size:12px;text-transform:uppercase;letter-spacing:2px;font-weight:600;">Your OTP Code</p>
                <div style="font-size:48px;font-weight:800;letter-spacing:16px;color:#3b82f6;font-family:monospace;">{otp}</div>
              </div>
              <p style="color:#9ca3af;font-size:12px;text-align:center;margin:0;">If you did not request this code, you can safely ignore this email.</p>
            </div>
            <div style="background:#f9fafb;padding:20px;text-align:center;border-top:1px solid #e5e7eb;">
              <p style="color:#9ca3af;font-size:12px;margin:0;">&#169; 2025 AI Data Analyst &bull; Automated Intelligence Platform</p>
            </div>
          </div>
        </body>
        </html>
        """

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"AI Data Analyst <{MAIL_EMAIL}>"
        msg['To'] = to_email
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(MAIL_EMAIL, MAIL_PASSWORD)
            server.sendmail(MAIL_EMAIL, to_email, msg.as_string())

        logger.info(f"OTP email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send OTP email to {to_email}: {e}")
        return False


def generate_and_send_otp(email, username="User"):
    """Generates an OTP, stores it in the DB, and emails it."""
    otp = generate_otp()
    save_otp(email, otp)
    success = send_otp_email(email, otp, username)
    return success