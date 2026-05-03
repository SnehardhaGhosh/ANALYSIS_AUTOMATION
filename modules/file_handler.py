import os
import pandas as pd
import json

UPLOAD_FOLDER = "uploads"

def save_file(file):
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    filepath = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(filepath)
    return filepath


def load_csv(filepath):
    """
    Robust CSV loader with multi-level fallback strategy
    Handles: inconsistent columns, different delimiters, malformed rows, encoding issues
    """
    attempts = [
        # Attempt 1: Standard CSV reading (default)
        {'kwargs': {}, 'desc': 'Standard CSV'},
        # Attempt 2: Skip bad lines, use Python engine (handles inconsistent columns)
        {'kwargs': {'on_bad_lines': 'skip', 'engine': 'python'}, 'desc': 'Skip bad lines'},
        # Attempt 3: Different delimiter (semicolon)
        {'kwargs': {'delimiter': ';', 'on_bad_lines': 'skip', 'engine': 'python'}, 'desc': 'Semicolon delimiter'},
        # Attempt 4: Tab-separated
        {'kwargs': {'delimiter': '\t', 'on_bad_lines': 'skip', 'engine': 'python'}, 'desc': 'Tab-separated'},
        # Attempt 5: Auto-detect delimiter
        {'kwargs': {'sep': None, 'engine': 'python', 'on_bad_lines': 'skip'}, 'desc': 'Auto-detect delimiter'},
        # Attempt 6: Handle encoding issues
        {'kwargs': {'encoding': 'latin-1', 'on_bad_lines': 'skip', 'engine': 'python'}, 'desc': 'Latin-1 encoding'},
        # Attempt 7: Very lenient parsing
        {'kwargs': {'encoding': 'utf-8', 'on_bad_lines': 'skip', 'engine': 'python', 'dtype': str}, 'desc': 'Lenient parsing'},
    ]
    
    for attempt in attempts:
        try:
            df = pd.read_csv(filepath, **attempt['kwargs'])
            if len(df) > 0:  # Ensure we got data
                return df
        except Exception as e:
            continue
    
    raise ValueError(f"Failed to load CSV with all attempted strategies")


def load_excel(filepath):
    """
    Fast Excel loader — tries engines in order of speed:
    1. calamine  (fastest — no style parsing)
    2. openpyxl read_only mode
    3. openpyxl standard (fullback)
    """
    # Strategy 1: calamine — up to 5x faster than openpyxl for large files
    try:
        import python_calamine  # noqa
        df = pd.read_excel(filepath, sheet_name=0, engine='calamine')
        if len(df) > 0:
            return df
    except Exception:
        pass

    # Strategy 2: openpyxl in read_only mode — skips style/formatting load
    try:
        df = pd.read_excel(filepath, sheet_name=0, engine='openpyxl',
                           engine_kwargs={'read_only': True, 'data_only': True})
        if len(df) > 0:
            return df
    except Exception:
        pass

    # Strategy 3: standard openpyxl (safest fallback)
    try:
        df = pd.read_excel(filepath, sheet_name=0, engine='openpyxl')
        if len(df) > 0:
            return df
    except Exception:
        pass

    try:
        # Last resort: concat all sheets
        all_sheets = pd.read_excel(filepath, sheet_name=None, engine='openpyxl')
        if isinstance(all_sheets, dict):
            dfs = [d for d in all_sheets.values() if len(d) > 0]
            if dfs:
                return pd.concat(dfs, ignore_index=True)
    except Exception:
        pass

    raise ValueError("Failed to load Excel file")


def load_json(filepath):
    """
    Robust JSON loader with fallback strategies
    Handles: nested JSON, list of objects, JSONL format, different encoding
    """
    file_ext = os.path.splitext(filepath)[1].lower()
    
    # For JSONL files, always try lines=True first
    if file_ext == '.jsonl':
        try:
            df = pd.read_json(filepath, lines=True)
            if len(df) > 0:
                return df
        except Exception:
            pass
    
    # Standard JSON attempts
    attempts = [
        # Attempt 1: Standard JSON-to-dataframe conversion
        {'kwargs': {}, 'desc': 'Standard JSON'},
        # Attempt 2: JSON with lines format (each line is a JSON object)
        {'kwargs': {'lines': True}, 'desc': 'JSON lines'},
        # Attempt 3: JSON with records orient
        {'kwargs': {'orient': 'records'}, 'desc': 'Records orient'},
    ]
    
    for attempt in attempts:
        try:
            df = pd.read_json(filepath, **attempt['kwargs'])
            if len(df) > 0:
                return df
        except Exception:
            pass
    
    # Last attempt: Manual JSON parsing
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # Try to detect if it's JSONL
            content = f.read()
        
        # Try JSONL format (one JSON per line)
        lines = content.strip().split('\n')
        records = []
        for line in lines:
            if line.strip():
                try:
                    records.append(json.loads(line))
                except:
                    pass
        
        if records and all(isinstance(r, dict) for r in records):
            return pd.DataFrame(records)
        
        # Try standard JSON
        data = json.loads(content)
        
        # Handle various JSON structures
        if isinstance(data, list):
            # List of objects
            if all(isinstance(item, dict) for item in data):
                return pd.DataFrame(data)
        elif isinstance(data, dict):
            # Single object or nested structure
            # Try to find array-like structures
            for key, value in data.items():
                if isinstance(value, list) and value and isinstance(value[0], dict):
                    return pd.DataFrame(value)
            # If no array found, wrap the dict
            return pd.DataFrame([data])
    except Exception:
        pass
    
    raise ValueError(f"Failed to load JSON file with all attempted strategies")


def detect_and_skip_header_rows(df):
    """
    Detects and removes duplicate header rows that may have been loaded as data
    Returns cleaned dataframe without header rows in data
    """
    if len(df) == 0:
        return df
    
    # Check if first row contains column names or looks like a header
    first_row = df.iloc[0]
    columns_in_first = sum(1 for val in first_row if str(val).lower() in [str(c).lower() for c in df.columns])
    
    # If first row contains column names, it's a duplicate header
    if columns_in_first > len(df.columns) * 0.5 and len(df) > 1:
        df = df.iloc[1:].reset_index(drop=True)
    
    return df


def convert_columns_to_proper_types(df):
    """
    Intelligently converts dataframe columns to proper types.
    Uses a SAMPLE of rows for type inference to keep large files fast.
    """
    df = df.copy()
    # Sample at most 500 rows for type inference — avoids O(n) on every column
    sample_size = min(500, len(df))
    sample = df.sample(n=sample_size, random_state=42) if len(df) > sample_size else df

    for col in df.columns:
        non_null = sample[col].dropna()
        if len(non_null) == 0:
            continue

        # Try numeric conversion
        try:
            numeric_converted = pd.to_numeric(non_null, errors='coerce')
            if numeric_converted.notna().sum() / len(non_null) > 0.8:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                continue
        except Exception:
            pass

        # Try datetime conversion (sample check only)
        try:
            s = non_null.astype(str).head(5)
            dt_pat = r'^\d{4}-\d{2}-\d{2}|^\d{2}/\d{2}/\d{4}|^\d{1,2}-\w+-\d{2,4}|^\d{1,2}/\d{1,2}/\d{2,4}'
            if s.str.match(dt_pat).sum() / len(s) > 0.6:
                df[col] = pd.to_datetime(df[col], errors='coerce')
                continue
        except Exception:
            pass

        # Fallback: keep as string
        df[col] = df[col].astype(str)

    return df


def load_file(filepath):
    """
    Universal file loader - detects format and uses appropriate robust loader
    Supports: CSV, Excel (.xlsx, .xls), JSON, JSONL
    Includes automatic type conversion and header detection
    """
    file_ext = os.path.splitext(filepath)[1].lower()
    
    try:
        if file_ext == '.csv':
            df = load_csv(filepath)
        elif file_ext in ['.xlsx', '.xls']:
            df = load_excel(filepath)
        elif file_ext in ['.json', '.jsonl']:
            df = load_json(filepath)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}. Supported: CSV, JSON, JSONL, XLS, XLSX")
        
        # Post-load processing
        df = detect_and_skip_header_rows(df)
        df = convert_columns_to_proper_types(df)
        
        return df
    
    except Exception as e:
        raise ValueError(f"Failed to load file {filepath}: {str(e)}")


# Backward compatibility
def load_csv_legacy(filepath):
    return load_file(filepath)