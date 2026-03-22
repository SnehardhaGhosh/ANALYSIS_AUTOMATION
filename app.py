from flask import Flask, render_template, request, redirect, session, url_for, jsonify
import os
import pandas as pd
import logging
from dotenv import load_dotenv
from flask_session import Session

# Load environment variables first
load_dotenv(dotenv_path=".env")

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
    from modules.ai_engine import ask_groq, ask_gemini, ask_huggingface
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

# Configure Flask-Session to use filesystem
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = os.path.join(os.getcwd(), 'flask_session')
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = 86400  # 24 hours
Session(app)

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
        file = None
        filepath = None
        try:
            # ===== STEP 0: FILE VALIDATION =====
            file = request.files.get('file')
            if not file or file.filename == '':
                logger.warning(f"User {session['user_id']} attempted upload without file")
                return redirect('/upload?error=no_file')
            
            # Check file size (max 50MB)
            file.seek(0, os.SEEK_END)
            file_size_mb = file.tell() / (1024 * 1024)
            file.seek(0)
            if file_size_mb > 50:
                logger.warning(f"User {session['user_id']} uploaded file exceeding 50MB: {file_size_mb}MB")
                return redirect('/upload?error=size')
            
            # Check file extension
            allowed_extensions = ['.csv', '.xlsx', '.xls', '.json', '.jsonl']
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in allowed_extensions:
                logger.warning(f"User {session['user_id']} attempted upload of unsupported file: {file_ext}")
                return redirect('/upload?error=unsupported')

            # Save file
            filepath = save_file(file)
            logger.info(f"File saved: {filepath} ({file_size_mb:.2f}MB)")
            
            # ===== STEP 1: LOAD FILE =====
            logger.info(f"STEP 1: Loading file {file.filename}...")
            try:
                df = load_file(filepath)
                if df is None or len(df) == 0:
                    logger.error(f"File loaded but is empty: {file.filename}")
                    os.remove(filepath)
                    return redirect('/upload?error=empty')
            except Exception as load_err:
                logger.error(f"STEP 1 FAILED - File load error: {str(load_err)}")
                try:
                    os.remove(filepath)
                except:
                    pass
                return redirect('/upload?error=corrupt')
            
            original_rows = len(df)
            original_cols = len(df.columns)
            logger.info(f"✓ File loaded successfully: {original_rows} rows × {original_cols} cols")

            # ===== STEP 2: VALIDATE DATA =====
            logger.info(f"STEP 2: Validating data...")
            try:
                validation_report = validate_data(df)
                data_quality_score = check_data_quality(df)
                logger.info(f"✓ Data validation complete. Quality score: {data_quality_score:.1f}%")
            except Exception as val_err:
                logger.error(f"STEP 2 FAILED - Validation error: {str(val_err)}")
                return redirect('/upload?error=validate')
            
            # ===== STEP 3: CLEAN DATA =====
            logger.info(f"STEP 3: Cleaning data...")
            try:
                df = clean_data(df)
                if df is None or len(df) == 0:
                    logger.error("Data cleaning resulted in empty dataset")
                    return redirect('/upload?error=clean')
                cleaning_report = get_cleaning_report(df)
                rows_after_clean = len(df)
                logger.info(f"✓ Data cleaned: {original_rows} → {rows_after_clean} rows")
            except Exception as clean_err:
                logger.error(f"STEP 3 FAILED - Cleaning error: {str(clean_err)}")
                import traceback
                logger.error(traceback.format_exc())
                return redirect('/upload?error=clean')
            
            # Save cleaned dataset before preprocessing (exact cleaned values, unknown replacements applied)
            cleaned_preprocessed_path = os.path.join(Config.CLEANED_FOLDER, f"cleaned_{session['user_id']}_raw.csv")
            try:
                df.to_csv(cleaned_preprocessed_path, index=False)
                session['cleaned_raw_dataset'] = cleaned_preprocessed_path
                logger.info(f"✓ Saved cleaned raw dataset before preprocessing: {cleaned_preprocessed_path}")
            except Exception as save_raw_err:
                logger.warning(f"Could not save cleaned raw dataset: {save_raw_err}")

            # ===== STEP 4: PREPROCESS DATA =====
            logger.info(f"STEP 4: Preprocessing data...")
            try:
                df = preprocess_data(df)
                if df is None:
                    logger.error("Preprocessing resulted in None")
                    return redirect('/upload?error=preprocess')
                preprocessing_report = get_preprocessing_report(df)
                logger.info(f"✓ Preprocessing complete")
            except Exception as prep_err:
                logger.error(f"STEP 4 FAILED - Preprocessing error: {str(prep_err)}")
                import traceback
                logger.error(traceback.format_exc())
                return redirect('/upload?error=preprocess')
            
            # ===== STEP 5: TRANSFORM DATA =====
            logger.info(f"STEP 5: Transforming data...")
            try:
                df = transform_data(df)
                if df is None:
                    logger.error("Transformation resulted in None")
                    return redirect('/upload?error=transform')
                transformation_report = get_transformation_report(df)
                logger.info(f"✓ Transformation complete")
            except Exception as trans_err:
                logger.error(f"STEP 5 FAILED - Transformation error: {str(trans_err)}")
                import traceback
                logger.error(traceback.format_exc())
                return redirect('/upload?error=transform')
            
            # ===== STEP 6: ADD ANALYSIS FEATURES =====
            logger.info(f"STEP 6: Adding analysis features...")
            try:
                df = add_profit_column(df)
                logger.info(f"✓ Features added")
            except Exception as feat_err:
                logger.warning(f"STEP 6 WARNING - Could not add features: {str(feat_err)}")
                # Don't fail on this - continue anyway

            # ===== STEP 7: SAVE PROCESSED DATA =====
            logger.info(f"STEP 7: Saving processed data...")
            try:
                final_processed_path = os.path.join(Config.CLEANED_FOLDER, f"processed_{session['user_id']}.csv")
                df.to_csv(final_processed_path, index=False)
                logger.info(f"✓ Data saved: {final_processed_path}")
            except Exception as save_err:
                logger.error(f"STEP 7 FAILED - Save error: {str(save_err)}")
                return redirect('/upload?error=save')
            
            # ===== STEP 8: BUILD REPORTS =====
            logger.info(f"STEP 8: Building reports...")
            try:
                import json
                original_columns = validation_report.get('dataset_info', {}).get('total_columns', original_cols)
                
                # Extract metrics from cleaning report
                duplicates_removed = 0
                nulls_handled = 0
                outliers_handled = 0
                
                if cleaning_report:
                    for step in cleaning_report.get('steps', []):
                        if step.get('step') == 'Remove Duplicate Rows':
                            duplicates_removed = step.get('duplicates_removed', 0)
                        if step.get('step') == 'Handle Missing Values':
                            nulls_handled = len(step.get('details', []))
                        if step.get('step') == 'Cap Outliers (IQR Method)':
                            outliers_handled = len(step.get('details', []))
                
                # Column-level null statistics
                column_nulls = {}
                for col in df.columns:
                    null_count = int(df[col].isnull().sum())
                    if null_count > 0:
                        column_nulls[col] = {
                            'count': null_count,
                            'percentage': round(null_count / len(df) * 100, 2)
                        }
                
                reports_summary = {
                    'original_rows': int(original_rows),
                    'final_rows': int(len(df)),
                    'rows_removed': int(original_rows - len(df)),
                    'original_columns': int(original_columns),
                    'final_columns': int(len(df.columns)),
                    'data_quality_score': float(data_quality_score) if isinstance(data_quality_score, (int, float)) else 0.0,
                    'duplicates_removed': duplicates_removed,
                    'nulls_handled': nulls_handled,
                    'outliers_handled': outliers_handled,
                    'column_null_counts': column_nulls,
                    'memory_usage_mb': round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
                }
                
                # Store in session
                session['cleaned_dataset'] = cleaned_preprocessed_path
                session['dataset'] = final_processed_path
                session['processing_reports'] = reports_summary
                session['validation_report'] = validation_report
                session['cleaning_report'] = cleaning_report
                session['preprocessing_report'] = preprocessing_report
                session['transformation_report'] = transformation_report
                session['last_upload_time'] = str(__import__('datetime').datetime.now())
                logger.info(f"✓ Reports built and stored")
            except Exception as rep_err:
                logger.error(f"STEP 8 WARNING - Report building error: {str(rep_err)}")
                # Don't fail on reports - they're just for display
            
            # ===== SUCCESS =====
            logger.info(f"✅ UPLOAD COMPLETE - User {session['user_id']} successfully processed: {file.filename}")
            logger.info(f"   Stats: {original_rows}→{len(df)} rows, {data_quality_score:.1f}% quality")
            return redirect('/processing-summary')
            
        except Exception as e:
            logger.error(f"❌ UPLOAD FAILED - Unexpected error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            # Clean up failed file
            if filepath and os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except:
                    pass
            return redirect('/upload?error=process')

    return render_template('upload.html')


# 👀 PREVIEW DATA
@app.route('/preview')
def preview():
    if 'user_id' not in session or ('dataset' not in session and 'cleaned_dataset' not in session):
        return redirect('/login')

    try:
        source = session.get('cleaned_dataset', session.get('dataset'))
        df = pd.read_csv(source)
        report = validate_data(df)
        return render_template(
            'preview.html',
            columns=df.columns,
            data=df.to_dict(orient='records'),
            report=report,
            source_type='cleaned' if 'cleaned_dataset' in session else 'processed'
        )
    except:
        return "Error loading dataset", 500


# 📋 PROCESSING SUMMARY - Shows all data processing steps
@app.route('/processing-summary')
def processing_summary():
    if 'user_id' not in session or 'dataset' not in session:
        return redirect('/login')
    
    try:
        import json
        # Get reports from session
        reports = session.get('processing_reports', {})
        validation_report = session.get('validation_report', {})
        cleaning_report = session.get('cleaning_report', {})
        preprocessing_report = session.get('preprocessing_report', {})
        transformation_report = session.get('transformation_report', {})
        
        # Load cleaned dataset (exact clean values before ML transformation)
        cleaned_df = None
        cleaned_data = []
        if 'cleaned_dataset' in session and session['cleaned_dataset']:
            cleaned_df = pd.read_csv(session['cleaned_dataset'])
            # Convert all values to strings to avoid template issues
            cleaned_data = cleaned_df.astype(str).to_dict(orient='records')
        
        # Load final dataset (after preprocessing/transformation)
        df = pd.read_csv(session['dataset'])
        
        # Calculate summary statistics for final dataset
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        summary_stats = {}
        for col in numeric_cols:
            summary_stats[col] = {
                'mean': round(df[col].mean(), 2),
                'median': round(df[col].median(), 2),
                'min': round(df[col].min(), 2),
                'max': round(df[col].max(), 2),
                'std': round(df[col].std(), 2)
            }
        
        # Build comprehensive report object
        full_reports = {
            'summary': reports,
            'validation': validation_report,
            'cleaning': cleaning_report,
            'preprocessing': preprocessing_report,
            'transformation': transformation_report,
            'summary_stats': summary_stats,
        }
        
        return render_template(
            'processing_summary.html',
            reports=full_reports,
            final_columns=df.columns,
            final_data=df.to_dict(orient='records'),
            final_shape=df.shape,
            cleaned_columns=cleaned_df.columns.tolist() if cleaned_df is not None else [],
            cleaned_data=cleaned_data,
            cleaned_shape=cleaned_df.shape if cleaned_df is not None else (0, 0),
            numeric_summary=summary_stats
        )
    except Exception as e:
        logger.error(f"Error loading processing summary for user {session['user_id']}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return "Error loading processing summary", 500


# 🤖 AI CHAT PAGE
@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect('/login')
    
    if 'dataset' not in session:
        return redirect('/upload')

    return render_template('chat.html')


# 📥 DOWNLOAD CLEANED DATASET
@app.route('/download_cleaned')
def download_cleaned():
    if 'user_id' not in session or 'cleaned_raw_dataset' not in session:
        return redirect('/login')
    
    cleaned_file = session['cleaned_raw_dataset']
    if not os.path.exists(cleaned_file):
        return "File not found", 404
    
    from flask import send_file
    return send_file(cleaned_file, as_attachment=True, download_name='cleaned_dataset.csv')


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
        # Use cleaned dataset for AI analysis
        dataset_file = session.get('cleaned_raw_dataset', session.get('dataset'))
        if not dataset_file:
            return jsonify({"error": "No dataset available"}), 400
        
        df = pd.read_csv(dataset_file)
        logger.info(f"User {session['user_id']} queried: {query} (using cleaned dataset)")
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
            
            # Determine available AI models and try them in order
            available_models = []
            if Config.GROQ_API_KEY:
                available_models.append("groq")
            if Config.HF_API_KEY:
                available_models.append("hf")
            if Config.GEMINI_API_KEY:
                available_models.append("gemini")
            
            if not available_models:
                raise Exception("No AI API keys configured. Please set GROQ_API_KEY, HF_API_KEY, or GEMINI_API_KEY in .env")
            
            ai_response = None
            for model in available_models:
                try:
                    if model == "groq":
                        ai_response = ask_groq(prompt)
                    elif model == "hf":
                        ai_response = ask_huggingface(prompt)
                    elif model == "gemini":
                        ai_response = ask_gemini(prompt)
                    logger.info(f"AI response generated using {model} for user {session['user_id']}")
                    break  # Success, exit loop
                except Exception as e:
                    logger.warning(f"Failed to use {model} for user {session['user_id']}: {str(e)}")
                    continue
            
            if ai_response is None:
                raise Exception("All AI models failed. Please check your API keys and network connection.")
            
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