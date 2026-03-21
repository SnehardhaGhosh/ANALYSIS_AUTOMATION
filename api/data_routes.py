from flask import request, jsonify
import os
import pandas as pd
from api import data_bp
from modules.data_cleaning import clean_data

UPLOAD_FOLDER = "uploads"


@data_bp.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files['file']
    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)

    # Load CSV
    df = pd.read_csv(filepath)

    # Clean Data
    df = clean_data(df)

    # Save cleaned version
    cleaned_path = f"cleaned_data/cleaned_{file.filename}"
    df.to_csv(cleaned_path, index=False)

    return jsonify({
        "message": "File uploaded & cleaned",
        "columns": df.columns.tolist(),
        "preview": df.head().to_dict()
    })