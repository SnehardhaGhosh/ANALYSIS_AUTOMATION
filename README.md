# AI Data Analyst

> **PRODUCTION READY** - Fully configured for development and production deployment

A modern, production-ready Flask web application that allows users to upload data files (CSV, Excel, JSON) and interact with an AI-powered data analysis system. The application provides a sequential workflow from login to data analysis with a beautiful, responsive UI.

## Quick Start

```bash
# Development (Windows)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py

# Production with Docker
docker-compose up -d

# Production with Gunicorn
gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:app
```

See [PRODUCTION.md](PRODUCTION.md) for detailed production setup instructions.

A modern, production-ready Flask web application that allows users to upload data files (CSV, Excel, JSON) and interact with an AI-powered data analysis system. The application provides a sequential workflow from login to data analysis with a beautiful, responsive UI.

## Features

### 🔐 User Authentication
- Secure user registration and login
- Session-based authentication
- Password hashing with Werkzeug

### 📊 Data Processing
- Support for multiple file formats: CSV, Excel (.xlsx/.xls), JSON
- Automatic data cleaning and validation
- Data preview and quality reports
- User-specific dataset management

### 🤖 AI-Powered Analysis
- Integration with Groq, Hugging Face, and Gemini AI models
- Rule-based query processing for fast responses
- AI interpretation for complex questions
- Support for various data analysis operations:
  - Aggregations (sum, average, count)
  - Statistical analysis
  - Correlation analysis
  - Data summaries

### 🎨 Modern UI/UX
- Responsive Bootstrap-based design
- Gradient backgrounds and modern styling
- Step-by-step workflow guidance
- Real-time chat interface
- Mobile-friendly design

### 🛡️ Production Features
- Comprehensive error handling and logging
- File type validation and security checks
- Session management
- SQLite database with proper schema
- Environment variable configuration

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd ai-data-analyst
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the root directory:
   ```env
   SECRET_KEY=your-secret-key-here
   GROQ_API_KEY=your-groq-api-key
   GEMINI_API_KEY=your-gemini-api-key
   HF_API_KEY=your-huggingface-api-key
   ```

5. **Initialize the database:**
   ```bash
   python -c "from modules.db import init_db; init_db()"
   ```

## Usage

1. **Start the application:**
   ```bash
   python app.py
   ```

2. **Open your browser and navigate to:**
   ```
   http://localhost:5000
   ```

3. **Follow the sequential workflow:**
   - Register/Login
   - Upload your data file (CSV, Excel, or JSON)
   - Preview and validate your data
   - Chat with AI for data analysis

## API Endpoints

### Authentication
- `POST /login` - User login
- `POST /register` - User registration
- `GET /logout` - User logout

### Data Management
- `POST /upload` - Upload data file
- `GET /preview` - Preview processed data
- `POST /ask` - Query data with AI

### File Support
- **CSV**: Standard comma-separated values
- **Excel**: .xlsx and .xls formats
- **JSON**: Standard JSON format

## Project Structure

```
ai-data-analyst/
├── app.py                 # Main Flask application
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── README.md            # This file
├── modules/              # Core application modules
│   ├── ai_engine.py     # AI model integrations
│   ├── analysis.py      # Data analysis functions
│   ├── auth.py          # Authentication logic
│   ├── data_cleaning.py # Data preprocessing
│   ├── data_validation.py# Data quality checks
│   ├── db.py            # Database operations
│   ├── file_handler.py  # File upload/processing
│   ├── models.py        # Data models
│   ├── prompt_builder.py# AI prompt generation
│   ├── query_executor.py# Query processing
│   └── utils.py         # Utility functions
├── api/                  # API blueprints
│   ├── auth_routes.py   # Authentication endpoints
│   ├── data_routes.py   # Data management endpoints
│   └── ai_routes.py     # AI interaction endpoints
├── templates/            # Jinja2 templates
│   ├── base.html        # Base layout
│   ├── login.html       # Login page
│   ├── register.html    # Registration page
│   ├── dashboard.html   # Main dashboard
│   ├── upload.html      # File upload page
│   ├── preview.html     # Data preview page
│   └── chat.html        # AI chat interface
├── static/               # Static assets
│   ├── css/
│   │   └── style.css    # Custom styles
│   └── js/
│       └── main.js      # Client-side JavaScript
├── uploads/              # Uploaded files
├── cleaned_data/         # Processed data files
├── logs/                 # Application logs
├── instance/             # Instance-specific data
│   └── database.db      # SQLite database
└── tests/                # Test files
```

## Configuration

### Environment Variables
- `SECRET_KEY`: Flask secret key for sessions
- `GROQ_API_KEY`: API key for Groq AI
- `GEMINI_API_KEY`: API key for Google Gemini
- `HF_API_KEY`: API key for Hugging Face

### AI Models
The application supports multiple AI models:
- **Groq** (Default): Fast inference with Llama models
- **Hugging Face**: Router API for various models
- **Gemini**: Google's generative AI

## Security Features

- Password hashing with Werkzeug
- Session-based authentication
- File type validation
- Input sanitization
- Error handling without information leakage
- Secure file storage

## Development

### Running Tests
```bash
python -m pytest tests/
```

### Code Formatting
```bash
# Install development dependencies
pip install black flake8

# Format code
black .

# Check style
flake8 .
```

### Database Migrations
The application uses SQLite with manual schema management. Database changes should be handled carefully in production.

## Deployment

### Local Development
```bash
export FLASK_ENV=development
python app.py
```

### Production
For production deployment, consider:
- Using a WSGI server like Gunicorn
- Setting up a reverse proxy (nginx)
- Using a production database (PostgreSQL)
- Enabling HTTPS
- Setting up monitoring and logging

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Check the logs in the `logs/` directory
- Review the code documentation
- Open an issue on GitHub

## Changelog

### Version 1.0.0
- Initial release with core functionality
- Support for CSV, Excel, and JSON files
- AI-powered data analysis
- Modern responsive UI
- Production-ready features
