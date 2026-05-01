from flask import request, jsonify
import os
import pandas as pd
import logging
from api import data_bp
from modules.file_handler import load_file, save_file
from modules.data_cleaning import clean_data, get_cleaning_report
from modules.data_validation import validate_data
from modules.data_preprocessing import preprocess_data, get_preprocessing_report
from modules.data_transformation import transform_data, get_transformation_report
from modules.visualizations import generate_visualizations

logger = logging.getLogger(__name__)

UPLOAD_FOLDER = "uploads"
CLEANED_FOLDER = "cleaned_data"


@data_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    Production-grade file upload with comprehensive error handling
    """
    try:
        if 'file' not in request.files:
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files['file']
        
        if not file.filename:
            return jsonify({"error": "No file selected"}), 400
        
        # Save file
        try:
            filepath = save_file(file)
            logger.info(f"File saved: {filepath}")
        except Exception as save_err:
            logger.error(f"File save error: {str(save_err)}")
            return jsonify({"error": f"Failed to save file: {str(save_err)}"}), 400
        
        # Load file with format detection
        try:
            df = load_file(filepath)
            logger.info(f"File loaded: {df.shape[0]} rows, {df.shape[1]} columns")
        except Exception as load_err:
            logger.error(f"File load error: {str(load_err)}")
            return jsonify({"error": f"Failed to load file format: {str(load_err)}"}), 400
        
        if len(df) == 0:
            return jsonify({"error": "File is empty or could not be parsed"}), 400
        
        # Validate data quality
        try:
            validation_result = validate_data(df)
            quality_score = validation_result.get('quality_score', 0)
            logger.info(f"Validation complete. Quality score: {quality_score}%")
        except Exception as validate_err:
            logger.warning(f"Validation warning: {str(validate_err)}")
            quality_score = 0
        
        # Clean data
        try:
            df_cleaned = clean_data(df)
            cleaning_report = get_cleaning_report(df_cleaned)
            logger.info(f"Data cleaned: {df_cleaned.shape[0]} rows, {df_cleaned.shape[1]} columns")
        except Exception as clean_err:
            logger.error(f"Cleaning error: {str(clean_err)}")
            df_cleaned = df
            cleaning_report = {"error": str(clean_err)}
        
        # Preprocess data
        try:
            df_processed = preprocess_data(df_cleaned)
            preprocessing_report = get_preprocessing_report(df_processed)
        except Exception as preprocess_err:
            logger.warning(f"Preprocessing error: {str(preprocess_err)}")
            df_processed = df_cleaned
            preprocessing_report = {}
        
        # Transform data
        try:
            df_transformed = transform_data(df_processed)
            transformation_report = get_transformation_report(df_transformed)
        except Exception as transform_err:
            logger.warning(f"Transformation error: {str(transform_err)}")
            df_transformed = df_processed
            transformation_report = {}
        
        # Generate visualizations
        try:
            vis_data = generate_visualizations(df_transformed)
        except Exception as vis_err:
            logger.warning(f"Visualization error: {str(vis_err)}")
            vis_data = {}
        
        # Save processed data
        try:
            os.makedirs(CLEANED_FOLDER, exist_ok=True)
            cleaned_path = os.path.join(CLEANED_FOLDER, f"processed_{file.filename}.csv")
            df_transformed.to_csv(cleaned_path, index=False)
        except Exception as save_clean_err:
            logger.warning(f"Could not save cleaned file: {str(save_clean_err)}")
        
        return jsonify({
            "message": "File processed successfully",
            "file_info": {
                "original_rows": len(df),
                "processed_rows": len(df_transformed),
                "total_columns": len(df_transformed.columns),
                "columns": df_transformed.columns.tolist()[:10]  # First 10 columns
            },
            "quality_score": quality_score,
            "reports": {
                "validation": validation_result.get('quality_score'),
                "cleaning_steps": len(cleaning_report.get('steps', [])) if isinstance(cleaning_report, dict) else 0,
                "new_features": len(transformation_report.get('new_features', [])) if isinstance(transformation_report, dict) else 0
            },
            "preview": df_transformed.head(5).to_dict(orient='records')
        }), 200
    
    except Exception as e:
        logger.error(f"Unexpected upload error: {str(e)}", exc_info=True)
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500