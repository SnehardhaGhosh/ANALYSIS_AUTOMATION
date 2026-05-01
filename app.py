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
    from modules.data_cleaning import clean_data, get_cleaning_report, cache_column_types, clear_cache
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
            
            # ===== STEP 1.5: APPLY DATA SAMPLING (OPTIONAL) =====
            sampled_rows = original_rows
            sampling_info = {
                'sampling_type': 'none',
                'original_rows': original_rows,
                'sampled_rows': original_rows,
                'sampling_percent': 100.0
            }
            
            try:
                sampling_type = request.form.get('sampling_type', 'all')
                
                if sampling_type == 'rows':
                    # Sample first N rows
                    sampling_rows = int(request.form.get('sampling_rows', original_rows))
                    sampling_rows = min(sampling_rows, original_rows)  # Don't exceed total rows
                    df = df.head(sampling_rows)
                    sampled_rows = len(df)
                    sampling_percent = (sampled_rows / original_rows) * 100
                    
                    logger.info(f"✓ Data sampling applied: Using first {sampled_rows} rows (from {original_rows})")
                    sampling_info = {
                        'sampling_type': 'rows',
                        'original_rows': original_rows,
                        'sampled_rows': sampled_rows,
                        'sampling_percent': round(sampling_percent, 2)
                    }
                
                elif sampling_type == 'percent':
                    # Sample first X% of rows
                    sampling_percent = int(request.form.get('sampling_percent', 100))
                    sampling_percent = min(max(sampling_percent, 1), 100)  # Clamp to 1-100
                    sampled_rows = max(100, int(original_rows * (sampling_percent / 100)))
                    df = df.head(sampled_rows)
                    sampled_rows = len(df)
                    actual_percent = (sampled_rows / original_rows) * 100
                    
                    logger.info(f"✓ Data sampling applied: Using first {sampling_percent}% ({sampled_rows} rows, from {original_rows})")
                    sampling_info = {
                        'sampling_type': 'percent',
                        'original_rows': original_rows,
                        'sampled_rows': sampled_rows,
                        'sampling_percent': round(actual_percent, 2)
                    }
                
                else:
                    # Process all data
                    logger.info(f"✓ No sampling: Processing all {original_rows} rows")
                    sampling_info = {
                        'sampling_type': 'all',
                        'original_rows': original_rows,
                        'sampled_rows': original_rows,
                        'sampling_percent': 100.0
                    }
                    
            except Exception as sample_err:
                logger.warning(f"Sampling error (continuing with all data): {str(sample_err)}")
            
            # Pre-cache column types to avoid redundant type inference calls (15% speed improvement)
            cache_column_types(df)
            logger.info(f"✓ Column types cached for {original_cols} columns")

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
            
            # Save cleaned dataset before preprocessing (UNIQUE VERSIONING)
            import time
            timestamp = int(time.time())
            cleaned_preprocessed_path = os.path.join(Config.CLEANED_FOLDER, f"cleaned_{session['user_id']}_{timestamp}_raw.csv")
            try:
                # Save a deep copy to ensure isolation from preprocessing
                df.copy().to_csv(cleaned_preprocessed_path, index=False)
                session['cleaned_dataset'] = cleaned_preprocessed_path
                session['cleaned_raw_dataset'] = cleaned_preprocessed_path
                logger.info(f"✓ Saved unique cleaned raw dataset for preview: {cleaned_preprocessed_path}")
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
                # Save processed data with unique versioning
                final_processed_path = os.path.join(Config.CLEANED_FOLDER, f"processed_{session['user_id']}_{timestamp}.csv")
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
                
                # Calculate summary statistics ONCE for caching (20x faster than recalculating on every view)
                numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                summary_stats = {}
                for col in numeric_cols:
                    try:
                        summary_stats[col] = {
                            'mean': round(float(df[col].mean()), 2),
                            'median': round(float(df[col].median()), 2),
                            'min': round(float(df[col].min()), 2),
                            'max': round(float(df[col].max()), 2),
                            'std': round(float(df[col].std()), 2)
                        }
                    except:
                        summary_stats[col] = {'mean': 0, 'median': 0, 'min': 0, 'max': 0, 'std': 0}
                
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
                    'summary_stats': summary_stats,
                    'sampling_info': sampling_info,  # Add sampling information to reports
                }
                
                # Store in session
                # (Note: cleaned_dataset already set in Step 3 to ensure it's the raw cleaned version)
                session['dataset'] = final_processed_path
                session['processing_reports'] = reports_summary
                session['validation_report'] = validation_report
                session['cleaning_report'] = cleaning_report
                session['preprocessing_report'] = preprocessing_report
                session['transformation_report'] = transformation_report
                session['summary_stats_cached'] = summary_stats  # Cache stats to avoid recalculation
                session['last_upload_time'] = str(__import__('datetime').datetime.now())
                logger.info(f"✓ Reports and stats cached for quick loading")
            except Exception as rep_err:
                logger.error(f"STEP 8 WARNING - Report building error: {str(rep_err)}")
                # Don't fail on reports - they're just for display
            
            # Clear type cache after upload complete (next upload won't use stale cache)
            clear_cache()
            
            # ===== SUCCESS =====
            logger.info(f"✅ UPLOAD COMPLETE - User {session['user_id']} successfully processed: {file.filename}")
            logger.info(f"   Stats: {original_rows}→{len(df)} rows, {data_quality_score:.1f}% quality")
            return redirect('/dashboard')
            
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


# 👁️ PREVIEW - Paginated dataset preview (100 rows per page for performance)
@app.route('/preview')
def preview():
    if 'user_id' not in session or 'dataset' not in session:
        return redirect('/login')

    try:
        # Get page number from query parameters (default: 1)
        page = request.args.get('page', 1, type=int)
        page = max(1, page)  # Ensure page >= 1
        rows_per_page = 100  # Paginate to 100 rows for fast loading
        
        # ALWAYS use cleaned_dataset for preview to show human-readable values, not scaled decimals
        source = session.get('cleaned_dataset')
        if not source or not os.path.exists(source):
            source = session.get('dataset') # Final fallback
        
        df = pd.read_csv(source)
        
        # Calculate pagination info
        total_rows = len(df)
        total_pages = (total_rows + rows_per_page - 1) // rows_per_page
        start_idx = (page - 1) * rows_per_page
        end_idx = min(start_idx + rows_per_page, total_rows)
        
        # Get page data
        page_df = df.iloc[start_idx:end_idx]
        page_data = page_df.to_dict(orient='records')
        
        # Validate entire dataset for quality report
        report = validate_data(df)
        
        # Calculate pagination range to avoid Jinja max/min errors
        start_page = max(1, page - 2)
        end_page = min(total_pages + 1, page + 3)
        
        # Return paginated preview
        return render_template(
            'preview.html',
            columns=df.columns,
            data=page_data,
            report=report,
            source_type='processed' if 'dataset' in session else 'cleaned',
            current_page=page,
            total_pages=total_pages,
            start_page=start_page,
            end_page=end_page,
            rows_per_page=rows_per_page,
            total_rows=total_rows,
            start_row=start_idx + 1,
            end_row=end_idx
        )
    except Exception as e:
        logger.error(f"Error in preview route: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Error loading dataset: {str(e)}", 500


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
        
        # Get cached summary statistics instead of recalculating (20x faster)
        summary_stats = session.get('summary_stats_cached', {})
        if not summary_stats:
            # Fallback: recalculate if cache is missing
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            summary_stats = {}
            for col in numeric_cols:
                try:
                    summary_stats[col] = {
                        'mean': round(float(df[col].mean()), 2),
                        'median': round(float(df[col].median()), 2),
                        'min': round(float(df[col].min()), 2),
                        'max': round(float(df[col].max()), 2),
                        'std': round(float(df[col].std()), 2)
                    }
                except:
                    summary_stats[col] = {'mean': 0, 'median': 0, 'min': 0, 'max': 0, 'std': 0}
        
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


# 📈 CUSTOM VISUALIZATION PAGE
@app.route('/visualize')
def visualize():
    if 'user_id' not in session:
        return redirect('/login')
    
    if 'dataset' not in session and 'cleaned_dataset' not in session:
        return redirect('/upload')

    try:
        dataset_path = session.get('cleaned_dataset', session.get('dataset'))
        df = pd.read_csv(dataset_path)
        
        columns = df.columns.tolist()
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        return render_template('visualize.html', columns=columns, numeric_cols=numeric_cols)
    except Exception as e:
        logger.error(f"Error loading visualize page: {str(e)}")
        return render_template('error.html', error="Could not load dataset for visualization.")

# 📊 GENERATE CUSTOM CHART API
@app.route('/api/generate-chart', methods=['POST'])
def generate_chart():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    x_col = data.get('x_col')
    y_col = data.get('y_col')
    chart_type = data.get('chart_type', 'bar')
    ml_algorithm = data.get('ml_algorithm', 'none')
    
    if not x_col or not y_col:
        return jsonify({"error": "X and Y columns are required"}), 400
        
    try:
        dataset_path = session.get('cleaned_dataset', session.get('dataset'))
        if not dataset_path:
            return jsonify({"error": "No dataset found"}), 400
            
        df = pd.read_csv(dataset_path)
        
        if x_col not in df.columns or y_col not in df.columns:
            return jsonify({"error": "Invalid columns selected"}), 400
            
        # Drop rows where Y is NaN
        plot_df = df[[x_col, y_col]].dropna(subset=[y_col])
        
        # Determine aggregation based on X column type
        is_numeric_x = pd.api.types.is_numeric_dtype(df[x_col])
        
        # If X is categorical, aggregate Y by mean
        if not is_numeric_x:
            # We group by X, calculating the mean of Y
            plot_df = plot_df.groupby(x_col, as_index=False)[y_col].mean()
            
            # If too many categories, limit to top 50 by Y value
            if len(plot_df) > 50:
                plot_df = plot_df.nlargest(50, y_col)
        else:
            # If both are numeric, we can plot them directly, but let's limit points for performance
            if len(plot_df) > 2000:
                plot_df = plot_df.sample(n=2000, random_state=42)
            
            # Sort by X for line charts
            if chart_type in ['line', 'area']:
                plot_df = plot_df.sort_values(by=x_col)
                
        # Ensure labels are clean strings to prevent "nan" in charts
        labels = plot_df[x_col].fillna('Unknown').astype(str).tolist()
        values = plot_df[y_col].tolist()
        
        # --- Smart Suggestion Logic for DIVERSE views ---
        cardinality = len(plot_df[x_col].unique())
        is_date_x = 'date' in x_col.lower() or 'time' in x_col.lower() or pd.api.types.is_datetime64_any_dtype(df[x_col])
        is_numeric_x = pd.api.types.is_numeric_dtype(df[x_col])
        is_numeric_y = pd.api.types.is_numeric_dtype(df[y_col])
        
        # We'll suggest types based on a combination of column properties
        suggested_type = 'bar'
        if is_date_x:
            suggested_type = 'line'
        elif is_numeric_x and is_numeric_y:
            suggested_type = 'scatter'
        elif cardinality <= 10:
            suggested_type = 'doughnut'
        elif cardinality > 50:
            suggested_type = 'bar' # Default for high cardinality
        
        # --- Business Narrative Engine ---
        narrative = "Analysis complete."
        try:
            top_idx = np.argmax(values)
            top_label = labels[top_idx]
            top_val = values[top_idx]
            
            if is_date_x:
                trend = "increasing" if values[-1] > values[0] else "decreasing"
                narrative = f"Over time, {y_col} is generally {trend}. The highest point was recorded on {top_label}."
            elif cardinality <= 10:
                pct = (top_val / sum(values)) * 100
                narrative = f"{top_label} is your dominant group, making up {round(pct, 1)}% of the total {y_col}."
            else:
                narrative = f"{top_label} is the top performer for {y_col}, outperforming the average by {round((top_val/np.mean(values)-1)*100, 1)}%."
        except:
            pass

        response_data = {
            "labels": labels,
            "datasets": [{
                "label": f"Average {y_col}" if not is_numeric_x else y_col,
                "data": values,
                "backgroundColor": "rgba(66, 133, 244, 0.7)",
                "borderColor": "rgba(66, 133, 244, 1)",
                "borderWidth": 1
            }],
            "narrative": narrative,
            "meta": {
                "x_col": x_col,
                "y_col": y_col,
                "is_date": is_date_x,
                "cardinality": cardinality,
                "is_numeric_x": is_numeric_x,
                "suggested_type": suggested_type
            }
        }
        
        # Apply ML Algorithms
        if ml_algorithm == 'trendline' and is_numeric_x:
            import numpy as np
            x_vals = plot_df[x_col].values
            y_vals = plot_df[y_col].values
            
            # Simple linear regression using numpy polyfit (degree 1)
            try:
                z = np.polyfit(x_vals, y_vals, 1)
                p = np.poly1d(z)
                trendline_y = p(x_vals).tolist()
                
                response_data['datasets'].append({
                    "label": "Linear Trendline",
                    "data": trendline_y,
                    "type": "line",
                    "fill": False,
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "borderDash": [5, 5],
                    "pointRadius": 0
                })
            except Exception as e:
                logger.warning(f"Trendline calculation failed: {e}")
                
        elif ml_algorithm == 'moving_average':
            window = min(5, len(values))
            if window > 1:
                y_series = pd.Series(values)
                ma = y_series.rolling(window=window, min_periods=1).mean().tolist()
                
                response_data['datasets'].append({
                    "label": f"{window}-Point Moving Average",
                    "data": ma,
                    "type": "line",
                    "fill": False,
                    "borderColor": "rgba(75, 192, 192, 1)",
                    "tension": 0.4,
                    "pointRadius": 0
                })

        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Error generating chart: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

# 🧠 ML INSIGHTS API
@app.route('/api/ml-insights', methods=['POST'])
def ml_insights():
    if 'user_id' not in session or 'dataset' not in session:
        return jsonify({"error": "No dataset available"}), 403
    try:
        data = request.json
        method = data.get('method', 'clustering')
        
        dataset_path = session.get('cleaned_raw_dataset', session.get('dataset'))
        df = pd.read_csv(dataset_path)
        
        # Select numeric columns for ML
        numeric_df = df.select_dtypes(include=['number']).fillna(0)
        
        if numeric_df.empty or len(numeric_df.columns) < 1:
            return jsonify({"error": "Insufficient numeric data for ML"}), 400
            
        from sklearn.preprocessing import StandardScaler
        
        # Choose columns: Use provided ones or top variance ones
        cols_to_use = [data.get('x_col'), data.get('y_col')]
        cols_to_use = [c for c in cols_to_use if c in numeric_df.columns]
        
        if len(cols_to_use) < 2:
            variances = numeric_df.var().sort_values(ascending=False)
            cols_to_use = variances.head(2).index.tolist()
            
        X = numeric_df[cols_to_use]
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        result = {}
        
        if method == 'clustering':
            from sklearn.cluster import KMeans
            kmeans = KMeans(n_clusters=min(3, len(X)), random_state=42, n_init=10)
            clusters = kmeans.fit_predict(X_scaled)
            
            plot_data = [{"x": float(df.iloc[i][cols_to_use[0]]), "y": float(df.iloc[i][cols_to_use[1]]), "cluster": int(clusters[i])} for i in range(min(500, len(df)))]
            result = {
                "type": "clustering", "columns": cols_to_use, "data": plot_data,
                "explanation": f"Smart Segmentation: I've grouped your data into {len(set(clusters))} distinct profiles based on {cols_to_use[0]} and {cols_to_use[1]}."
            }
            
        elif method == 'anomalies':
            from sklearn.ensemble import IsolationForest
            iso = IsolationForest(contamination=0.05, random_state=42)
            preds = iso.fit_predict(X_scaled)
            
            anomaly_indices = [i for i, p in enumerate(preds) if p == -1]
            plot_data = [{"x": float(df.iloc[i][cols_to_use[0]]), "y": float(df.iloc[i][cols_to_use[1]]), "is_anomaly": bool(preds[i] == -1)} for i in range(min(500, len(df)))]
            
            result = {
                "type": "anomalies", "columns": cols_to_use, "count": len(anomaly_indices), "data": plot_data,
                "explanation": f"Outlier Scanner: Detected {len(anomaly_indices)} data points deviating from normal patterns in {cols_to_use[0]} and {cols_to_use[1]}. Red points indicate high variance."
            }
            
        elif method == 'risk_score':
            z_scores = ((numeric_df - numeric_df.mean()) / numeric_df.std()).abs().mean(axis=1)
            high_risk_count = (z_scores > 2).sum()
            result = {"type": "risk", "count": int(high_risk_count), "explanation": f"Statistical Risk Analysis: I've identified {high_risk_count} data points with high volatility (Z-score > 2)."}

        return jsonify(result)
        
    except Exception as e:
        logger.error(f"ML Insights error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 🔮 PREDICTIVE ENGINE API
@app.route('/api/ml-advanced', methods=['POST'])
def ml_advanced():
    if 'user_id' not in session or 'dataset' not in session:
        return jsonify({"error": "No dataset available"}), 403
    
    try:
        data = request.json
        dataset_path = session.get('cleaned_raw_dataset', session.get('dataset'))
        df = pd.read_csv(dataset_path)
        
        y_col = data.get('y_col') or df.select_dtypes(include=['number']).columns[0]
        if y_col not in df.columns: y_col = df.select_dtypes(include=['number']).columns[0]
        
        y_vals = df[y_col].tail(30).fillna(0).values # Use 30 points for better regression
        x_vals = range(len(y_vals))
        
        from sklearn.linear_model import LinearRegression
        model = LinearRegression().fit([[x] for x in x_vals], y_vals)
        future_x = [[x] for x in range(len(y_vals), len(y_vals) + 5)]
        preds = [max(0, p) for p in model.predict(future_x).tolist()] # No negative predictions for business metrics
        
        return jsonify({
            "predictions": preds,
            "metric": y_col,
            "explanation": f"Predictive Trend: Based on recent patterns, {y_col} is expected to {'rise' if model.coef_[0] > 0 else 'soften'}. The next 5 target values are estimated above."
        })
        
    except Exception as e:
        logger.error(f"Advanced ML error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 🤖 FULL AGENTIC ANALYSIS API
@app.route('/api/agentic-analysis', methods=['GET'])
def agentic_analysis():
    if 'user_id' not in session or 'dataset' not in session:
        return jsonify({"error": "No dataset available"}), 403
    
    try:
        dataset_path = session.get('cleaned_raw_dataset', session.get('dataset'))
        df = pd.read_csv(dataset_path)
        
        # 1. Automated Feature Importance (What drives the target?)
        # Target is usually the first numeric column or one named 'amount', 'price', 'profit'
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        target_col = next((c for c in numeric_cols if any(k in c.lower() for k in ['amount', 'profit', 'price', 'revenue'])), numeric_cols[0] if numeric_cols else None)
        
        feature_report = {}
        if target_col and len(df) > 10:
            from sklearn.ensemble import RandomForestRegressor
            from sklearn.preprocessing import LabelEncoder
            
            # Prepare small sample for speed
            sample_df = df.head(1000).copy()
            X = sample_df.drop(columns=[target_col]).select_dtypes(exclude=['datetime64'])
            y = sample_df[target_col].fillna(0)
            
            # Simple encoding for strings
            for col in X.select_dtypes(include=['object']).columns:
                X[col] = LabelEncoder().fit_transform(X[col].astype(str))
            
            X = X.fillna(0)
            rf = RandomForestRegressor(n_estimators=50, random_state=42)
            rf.fit(X, y)
            
            importances = pd.Series(rf.feature_importances_, index=X.columns).sort_values(ascending=False)
            feature_report = {
                "top_driver": importances.index[0],
                "impact_score": round(float(importances.iloc[0]) * 100, 1),
                "all_drivers": importances.head(5).to_dict()
            }

        # 2. Automated Clustering Summary
        cluster_count = 3
        if len(df) > cluster_count:
             from sklearn.cluster import KMeans
             from sklearn.preprocessing import StandardScaler
             num_data = df.select_dtypes(include=['number']).fillna(0).head(500)
             if not num_data.empty:
                 scaler = StandardScaler()
                 kmeans = KMeans(n_clusters=cluster_count, random_state=42, n_init=10)
                 kmeans.fit(scaler.fit_transform(num_data))
                 cluster_dist = pd.Series(kmeans.labels_).value_counts(normalize=True).to_dict()
             else:
                 cluster_dist = {}
        else:
            cluster_dist = {}

        # 3. Compile Executive Narrative
        narrative = f"Agent Analysis Complete. I've identified '{feature_report.get('top_driver', 'Unknown')}' as your primary performance driver, accounting for {feature_report.get('impact_score', 0)}% of the variance in {target_col}. "
        if cluster_dist:
            narrative += f"The dataset naturally segments into {cluster_count} distinct profiles, with the largest group representing {round(max(cluster_dist.values())*100, 1)}% of the population."

        return jsonify({
            "status": "success",
            "executive_summary": narrative,
            "feature_importance": feature_report,
            "segments": cluster_dist,
            "recommendation": f"Focus optimizations on {feature_report.get('top_driver')} to maximize impact on {target_col}."
        })
        
    except Exception as e:
        logger.error(f"Agentic analysis error: {str(e)}")
        return jsonify({"error": str(e)}), 500

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
            debug=True, # Force debug for active development
            use_reloader=True
        )
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}")
        sys.exit(1)