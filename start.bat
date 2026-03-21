@echo off
REM Production startup script for AI Data Analyst (Windows)

setlocal enabledelayedexpansion

REM Create necessary directories
if not exist logs mkdir logs
if not exist uploads mkdir uploads
if not exist cleaned_data mkdir cleaned_data
if not exist instance mkdir instance

REM Set Flask environment
set FLASK_ENV=production
set FLASK_PORT=5000

echo Starting AI Data Analyst...
echo Environment: %FLASK_ENV%
echo Port: %FLASK_PORT%

REM Check if .env file exists
if exist .env (
    echo Loading environment variables from .env
)

REM Install dependencies if needed
pip install -r requirements.txt --quiet

REM Run development server for testing
REM python app.py

REM For production with Gunicorn:
gunicorn --bind 0.0.0.0:%FLASK_PORT% --workers 4 --access-logfile logs/access.log --error-logfile logs/error.log wsgi:app

endlocal