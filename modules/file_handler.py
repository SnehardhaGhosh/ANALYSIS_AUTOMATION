import os
import pandas as pd

UPLOAD_FOLDER = "uploads"

def save_file(file):
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    return filepath


def load_file(filepath):
    """Load CSV, Excel, or JSON files"""
    file_ext = os.path.splitext(filepath)[1].lower()
    
    if file_ext == '.csv':
        return pd.read_csv(filepath)
    elif file_ext in ['.xlsx', '.xls']:
        return pd.read_excel(filepath)
    elif file_ext == '.json':
        return pd.read_json(filepath)
    else:
        raise ValueError(f"Unsupported file type: {file_ext}")


# Backward compatibility
def load_csv(filepath):
    return load_file(filepath)