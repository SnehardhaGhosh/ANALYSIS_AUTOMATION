import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")

    # Database
    DATABASE = "instance/database.db"

    # Upload folders
    UPLOAD_FOLDER = "uploads"
    CLEANED_FOLDER = "cleaned_data"
    LOGS_FOLDER = "logs"

    # API KEYS
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    HF_API_KEY = os.getenv("HF_API_KEY")

    # AI Settings
    DEFAULT_MODEL = "groq"   # options: groq, gemini, hf

    # File limits
    MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB