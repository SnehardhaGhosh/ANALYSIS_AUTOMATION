# AI Data Analyst - Production Setup Guide

## Quick Start (Development)

```bash
# 1. Create virtual environment
python -m venv venv
venv\Scripts\activate  # On Windows

# 2. Install dependencies
pip install -r requirements.txt

# 3. Create .env file
copy .env.example .env
# Edit .env with your API keys

# 4. Create necessary folders
mkdir logs uploads cleaned_data instance

# 5. Run the application
python app.py
```

The app will be available at `http://localhost:5000`

## Production Setup

### Option 1: Docker (Recommended)

```bash
# 1. Build the image
docker build -t ai-data-analyst .

# 2. Run with docker-compose
docker-compose up -d

# 3. Access the app
# http://localhost:5000
```

### Option 2: Gunicorn + Nginx

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file with production settings
export SECRET_KEY=$(openssl rand -hex 32)
# Add your API keys to .env

# 3. Create necessary directories
mkdir -p logs uploads cleaned_data instance

# 4. Run with Gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:app

# 5. Configure Nginx as reverse proxy (optional)
# See nginx-config.example for sample configuration
```

### Option 3: Heroku

```bash
# 1. Create Procfile (included)
# 2. Set environment variables:
heroku config:set SECRET_KEY=your-secret-key
heroku config:set GROQ_API_KEY=your-groq-key
# ... other API keys

# 3. Deploy
git push heroku main
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
# Flask Configuration
FLASK_ENV=production          # Set to 'development' for debugging
FLASK_PORT=5000             # Port to run on

# Security (CHANGE IN PRODUCTION!)
SECRET_KEY=your-secret-key-here

# API Keys (get from respective providers)
GROQ_API_KEY=your-groq-key
GEMINI_API_KEY=your-gemini-key
HF_API_KEY=your-huggingface-key
```

## Database Setup

The application uses SQLite by default. For production, consider:

```bash
# Automatic initialization on first run
python -c "from modules.db import init_db; init_db()"
```

## File Structure for Production

```
ai-data-analyst/
├── logs/              # Application and server logs
├── uploads/           # Uploaded data files
├── cleaned_data/      # Processed data files
├── instance/          # Database and instance files
└── ...
```

## Security Checklist

- [ ] Change SECRET_KEY in .env to a random value
- [ ] Set FLASK_ENV=production
- [ ] Use HTTPS/SSL in production
- [ ] Limit file upload sizes (configured: 16MB)
- [ ] Keep API keys secure and never commit to git
- [ ] Use environment variables for all sensitive data
- [ ] Set up proper firewall rules
- [ ] Enable logging and monitoring
- [ ] Regular database backups
- [ ] Update dependencies regularly

## Monitoring & Logging

### View Logs

```bash
# Application logs
tail -f logs/app.log

# Access logs (with Gunicorn)
tail -f logs/access.log

# Error logs
tail -f logs/error.log
```

### Health Check

```bash
curl http://localhost:5000/
```

## Performance Tips

1. **Caching**: Implement Redis for session caching
2. **Database**: Use PostgreSQL instead of SQLite for production
3. **Workers**: Adjust Gunicorn workers based on CPU cores
4. **CDN**: Serve static files via CDN
5. **Database Pooling**: Configure connection pooling for better concurrency

## Troubleshooting

### App won't start

```bash
# Check Python version (3.7+)
python --version

# Verify all dependencies
pip list | grep -E "flask|pandas|gunicorn"

# Check logs
cat logs/app.log
```

### Import errors

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt

# Verify environment
python -c "import flask; import pandas; print('OK')"
```

### Permission errors

```bash
# Ensure proper folder permissions
chmod -R 755 logs uploads cleaned_data instance

# On Windows:
# Use "Run as Administrator" or adjust folder properties
```

## Backup Strategy

Recommended backup locations:
- Database: `instance/database.db`
- Uploaded files: `uploads/`
- Cleaned data: `cleaned_data/`
- Logs: `logs/`

```bash
# Simple backup script
tar -czf backup-$(date +%Y%m%d).tar.gz \
    instance/ uploads/ cleaned_data/ logs/
```

## Scaling Considerations

For high-traffic deployments:

1. **Database**: Migrate to PostgreSQL with read replicas
2. **Session Store**: Use Redis instead of default sessions
3. **Task Queue**: Implement Celery for async processing
4. **Load Balancer**: Use HAProxy or AWS ELB
5. **Storage**: Use S3 or similar for file uploads
6. **Monitoring**: Set up CloudWatch or Datadog

## Support & Updates

- Check `logs/app.log` for detailed error messages
- Review `README.md` for general documentation
- Update dependencies: `pip install --upgrade -r requirements.txt`
- Report issues with full logs and error messages

## Production Deployment Checklist

```
Pre-deployment:
- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Database backed up
- [ ] Static files optimized
- [ ] Error handling in place
- [ ] Logging configured
- [ ] Security headers set
- [ ] SSL certificates ready

Post-deployment:
- [ ] Health checks passing
- [ ] Logs being written
- [ ] Database connected
- [ ] API keys working
- [ ] File uploads working
- [ ] Chat functionality responsive
- [ ] Error pages displaying correctly
```