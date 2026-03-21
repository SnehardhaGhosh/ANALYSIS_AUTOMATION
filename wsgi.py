"""
WSGI entry point for production deployment.
Use with Gunicorn: gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
"""
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=".env")

from app import app

if __name__ == "__main__":
    app.run()