#!/bin/bash
# Production startup script for AI Data Analyst

set -e

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

# Set Flask environment
export FLASK_ENV=${FLASK_ENV:-production}
export FLASK_PORT=${FLASK_PORT:-5000}

echo "Starting AI Data Analyst..."
echo "Environment: $FLASK_ENV"
echo "Port: $FLASK_PORT"

# Create necessary directories
mkdir -p logs uploads cleaned_data instance

# Start the application with Gunicorn for production
# For development, use: python app.py
gunicorn \
    --bind 0.0.0.0:${FLASK_PORT} \
    --workers 4 \
    --worker-class sync \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info \
    wsgi:app