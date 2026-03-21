from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import os
import pandas as pd
import logging
from dotenv import load_dotenv

# Load environment variables first
load_dotenv(dotenv_path=".env")

# Config
from config import Config

# Ensure all required folders exist BEFORE logging setup
os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
os.makedirs(Config.CLEANED_FOLDER, exist_ok=True)
os.makedirs(Config.LOGS_FOLDER, exist_ok=True)
os.makedirs('instance', exist_ok=True)

# Setup logging after folders are created
logging.basicConfig(
    filename=os.path.join(Config.LOGS_FOLDER, 'app.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Modules
try:
    from modules.db import init_db, save_chat, get_chat_history
    from modules.auth import create_user, verify_user
    from modules.file_handler import save_file, load_file
    from modules.data_cleaning import clean_data, get_cleaning_report
    from modules.data_validation import validate_data, check_data_quality
    from modules.data_preprocessing import preprocess_data, get_preprocessing_report
    from modules.data_transformation import transform_data, get_transformation_report
    from modules.analysis import add_profit_column
    from modules.ai_engine import ask_gemini
    from modules.prompt_builder import build_prompt
    from modules.query_executor import execute_safe_query
except ImportError as e:
    logger.error(f"Failed to import modules: {str(e)}")
    raise

# API Blueprints
try:
    from api.auth_routes import auth_bp
    from api.data_routes import data_bp
    from api.ai_routes import ai_bp
except ImportError as e:
    logger.error(f"Failed to import API blueprints: {str(e)}")
    raise

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY

# Register APIs
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(data_bp, url_prefix='/api/data')
app.register_blueprint(ai_bp, url_prefix='/api/ai')

# Initialize DB
try:
    init_db()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database: {str(e)}")

# Store current dataset path (simple version)
# CURRENT_DATASET = None  # Removed global, using session instead


# ------------------- ROUTES -------------------

@app.route('/')
def home():
    return redirect('/login')


# 🔐 LOGIN
@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()

            if not email or not password:
                return render_template('login.html', error='Email and password are required')

            user = verify_user(email, password)

            if user:
                session['user_id'] = user[0]
                logger.info(f"User {email} logged in successfully")
                return redirect('/dashboard')
            else:
                logger.warning(f"Failed login attempt for email: {email}")
                return render_template('login.html', error='Invalid email or password')

        return render_template('login.html')
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return render_template('login.html', error='An error occurred during login')


# 📝 REGISTER
@app.route('/register', methods=['GET', 'POST'])
def register():
    try:
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '').strip()

            if not all([username, email, password]):
                return render_template('register.html', error='All fields are required')

            if len(password) < 6:
                return render_template('register.html', error='Password must be at least 6 characters')

            create_user(username, email, password)
            logger.info(f"New user registered: {email}")
            return redirect('/login?registered=1')

        return render_template('register.html')
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return render_template('register.html', error='Email already exists or registration failed')

@app.route('/forgot-password', methods=['GET'])
def forgot_password_page():
    return render_template('forgot_password.html')

# 🔑 LOGOUT
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# 📊 DASHBOARD
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    return render_template('dashboard.html')


# 📂 UPLOAD CSV
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        try:
            file = request.files['file']
            
            if not file or file.filename == '':
                logger.warning(f"User {session['user_id']} attempted upload without file")
                return redirect('/upload?error=no_file')
            
            # Check file extension
            allowed_extensions = ['.csv', '.xlsx', '.xls', '.json']
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in allowed_extensions:
                logger.warning(f"User {session['user_id']} attempted upload of unsupported file: {file_ext}")
                return redirect('/upload?error=unsupported')

            filepath = save_file(file)
            df = load_file(filepath)
            
            original_rows = len(df)
            logger.info(f"User {session['user_id']} uploaded file: {file.filename}, rows: {original_rows}")

            # Step 1: Validation (before cleaning)
            validation_report = validate_data(df)
            data_quality_score = check_data_quality(df)

            # Step 2: Cleaning
            df = clean_data(df)
            cleaning_report = get_cleaning_report(df)
            logger.info(f"Data cleaned for user {session['user_id']}: {cleaning_report}")

            # Step 3: Preprocessing
            df = preprocess_data(df)
            preprocessing_report = get_preprocessing_report(df)
            logger.info(f"Data preprocessed for user {session['user_id']}: {preprocessing_report}")

            # Step 4: Transformation
            df = transform_data(df)
            transformation_report = get_transformation_report(df)
            logger.info(f"Data transformed for user {session['user_id']}: {transformation_report}")

            # Step 5: Add analysis
            df = add_profit_column(df)

            # Save cleaned file
            cleaned_path = os.path.join(Config.CLEANED_FOLDER, f"cleaned_{session['user_id']}.csv")
            df.to_csv(cleaned_path, index=False)

            # Save processing reports to session
            original_columns = validation_report.get('dataset_info', {}).get('total_columns', len(df.columns))
            
            # Save reports as JSON files instead of session to avoid serialization issues
            import json
            reports_summary = {
                'original_rows': int(original_rows),
                'final_rows': int(len(df)),
                'original_columns': int(original_columns),
                'final_columns': int(len(df.columns)),
                'data_quality_score': float(data_quality_score) if isinstance(data_quality_score, (int, float)) else 0.0,
            }
            
            # Store in-memory for this session
            session['dataset'] = cleaned_path
            session['processing_reports'] = reports_summary
            session['last_upload_time'] = str(__import__('datetime').datetime.now())
            
            # Also save to session file for reference
            reports_file = os.path.join(Config.CLEANED_FOLDER, f"reports_{session['user_id']}.json")
            try:
                # Convert complex objects to simple dicts for JSON serialization
                json_safe_validation = {
                    'quality_warnings': validation_report.get('quality_warnings', []),
                    'quality_score': validation_report.get('quality_score', 0),
                    'dataset_info': validation_report.get('dataset_info', {})
                }
                with open(reports_file, 'w') as f:
                    json.dump({
                        'summary': reports_summary,
                        'validation': json_safe_validation,
                        'dataset_path': cleaned_path
                    }, f, indent=2, default=str)
            except Exception as file_err:
                logger.warning(f"Could not save reports file: {str(file_err)}")

            return redirect('/processing-summary')
        except Exception as e:
            logging.error(f"Error processing upload for user {session['user_id']}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return redirect('/upload?error=process')

    return render_template('upload.html')


# 👀 PREVIEW DATA
@app.route('/preview')
def preview():
    if 'user_id' not in session or 'dataset' not in session:
        return redirect('/login')

    try:
        df = pd.read_csv(session['dataset'])
        report = validate_data(df)
        return render_template(
            'preview.html',
            columns=df.columns,
            data=df.head(10).to_dict(orient='records'),
            report=report
        )
    except:
        return "Error loading dataset", 500


# 📋 PROCESSING SUMMARY - Shows all data processing steps
@app.route('/processing-summary')
def processing_summary():
    if 'user_id' not in session or 'dataset' not in session:
        return redirect('/login')
    
    try:
        # Get reports from session
        reports = session.get('processing_reports', {})
        
        # Load final dataset
        df = pd.read_csv(session['dataset'])
        
        return render_template(
            'processing_summary.html',
            reports=reports,
            columns=df.columns,
            data=df.head(10).to_dict(orient='records'),
            dataset_shape=df.shape
        )
    except Exception as e:
        logger.error(f"Error loading processing summary for user {session['user_id']}: {str(e)}")
        return "Error loading processing summary", 500


# 🤖 AI CHAT PAGE
@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect('/login')
    
    if 'dataset' not in session:
        return redirect('/upload')

    return render_template('chat.html')


# 🤖 AI QUERY API (CONNECTED TO FRONTEND)
@app.route('/ask', methods=['POST'])
def ask():
    if 'user_id' not in session or 'dataset' not in session:
        logger.warning("Unauthorized access to /ask endpoint")
        return jsonify({"error": "No dataset available"}), 403

    data = request.json
    query = data.get("query")

    if not query:
        return jsonify({"error": "No query provided"}), 400

    try:
        df = pd.read_csv(session['dataset'])
        logger.info(f"User {session['user_id']} queried: {query}")
    except Exception as e:
        logger.error(f"Error loading dataset for user {session['user_id']}: {str(e)}")
        return jsonify({"error": "Dataset error"}), 500

    try:
        # Step 1: Get rule-based result for accuracy
        rule_result = None
        try:
            rule_result = execute_safe_query(df, query)
        except Exception as e:
            logger.error(f"Rule-based query error for user {session['user_id']}: {str(e)}")

        # Step 2: Pass FULL dataset to AI for accurate calculations
        try:
            full_dataset_str = df.to_string()
            prompt = build_prompt(query, df.columns.tolist(), full_dataset_str, str(rule_result))
            ai_response = ask_gemini(prompt)
            logger.info(f"AI response generated for user {session['user_id']}")
            
            # Save chat to database
            save_chat(session['user_id'], query, ai_response)
            
        except Exception as e:
            logger.error(f"AI query error for user {session['user_id']}: {str(e)}")
            return jsonify({"error": str(e)}), 500

        return jsonify({
            "response": str(ai_response).strip()
        })
    except Exception as e:
        logger.error(f"Error processing query for user {session['user_id']}: {str(e)}")
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"Traceback: {error_detail}")
        return jsonify({"error": str(e)}), 500

# 📜 GET CHAT HISTORY
@app.route('/api/chat-history', methods=['GET'])
def get_chat_history_route():
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 403
    
    try:
        history = get_chat_history(session['user_id'])
        formatted_history = []
        for query, response, timestamp in history:
            formatted_history.append({
                "query": query,
                "response": response,
                "timestamp": timestamp
            })
        return jsonify({"history": formatted_history})
    except Exception as e:
        logger.error(f"Error retrieving chat history: {str(e)}")
        return jsonify({"error": str(e)}), 500


# 📊 GET VISUALIZATIONS
@app.route('/api/visualizations', methods=['GET'])
def get_visualizations():
    if 'user_id' not in session or 'dataset' not in session:
        return jsonify({"error": "No dataset available"}), 403
    
    try:
        from modules.visualizations import generate_visualizations, format_visualizations_for_json
        df = pd.read_csv(session['dataset'])
        visualizations = generate_visualizations(df)
        formatted = format_visualizations_for_json(visualizations)
        return jsonify(formatted)
    except Exception as e:
        logger.error(f"Error generating visualizations: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {request.path}")
    return render_template('error.html', error='Page not found'), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"500 error: {str(error)}")
    return render_template('error.html', error='Internal server error'), 500

@app.errorhandler(403)
def forbidden(error):
    logger.warning(f"403 error: {request.path}")
    return render_template('error.html', error='Access forbidden'), 403


# ------------------- RUN -------------------

if __name__ == "__main__":
    # Production setup
    import sys
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    
    logger.info(f"Starting AI Data Analyst server (Debug: {debug_mode})")
    
    try:
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('FLASK_PORT', 5000)),
            debug=debug_mode,
            use_reloader=debug_mode
        )
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}")
        sys.exit(1)