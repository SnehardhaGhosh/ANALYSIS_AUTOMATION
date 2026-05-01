import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler


def safe_to_numeric(series):
    """Safely convert any data type to numeric"""
    try:
        return pd.to_numeric(series, errors='coerce')
    except:
        return pd.Series([np.nan] * len(series), index=series.index)


def preprocess_data(df):
    """
    Comprehensive data preprocessing pipeline
    Handles all data types gracefully
    """
    preprocessing_report = {
        'steps': []
    }
    
    df = df.copy()
    
    # Step 1: Encode categorical variables
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    encodings = {}
    
    for col in categorical_cols:
        if df[col].nunique() < 20:  # Only encode low-cardinality categoricals
            unique_values = df[col].dropna().unique()
            encoding_map = {val: idx for idx, val in enumerate(unique_values)}
            df[col] = df[col].map(encoding_map)
            encodings[col] = encoding_map
    
    if encodings:
        preprocessing_report['steps'].append({
            'step': 'Encode Categorical Variables',
            'columns_encoded': len(encodings),
            'encoding_map': encodings
        })
    
    # Step 2: Handle skewed distributions with log transformation
    # Convert all numeric-like columns to actual numeric
    numeric_cols = []
    numeric_data = {}
    
    for col in df.columns:
        converted = safe_to_numeric(df[col])
        if converted.notna().sum() > 0.5 * len(df):  # At least 50% numeric
            numeric_cols.append(col)
            numeric_data[col] = converted
    
    log_transformed = []
    for col in numeric_cols:
        min_val = numeric_data[col].min()
        # Log transformation requires positive values
        if pd.notna(min_val) and min_val > 0:
            skewness = numeric_data[col].skew()
            if not pd.isna(skewness) and abs(skewness) > 2:  # Highly skewed
                numeric_data[col] = np.log1p(numeric_data[col])
                log_transformed.append(col)
    
    # Update df with converted numeric columns
    for col in numeric_cols:
        df[col] = numeric_data[col]
    
    if log_transformed:
        preprocessing_report['steps'].append({
            'step': 'Log Transform Skewed Columns',
            'columns_transformed': log_transformed
        })
    
    # Step 3: Normalize numeric columns (0-1 scaling)
    scaler = MinMaxScaler()
    scaled_cols = []
    
    for col in numeric_cols:
        if col not in log_transformed:  # Don't scale already transformed columns
            valid_data = df[col].dropna()
            if len(valid_data) > 0:
                try:
                    # Avoid mean imputation as requested by user
                    scaled_values = scaler.fit_transform(df[[col]].fillna(0))
                    df[col] = scaled_values
                    scaled_cols.append(col)
                except:
                    pass
    
    if scaled_cols:
        preprocessing_report['steps'].append({
            'step': 'Normalize Numeric Columns (Min-Max Scaling)',
            'columns_normalized': scaled_cols
        })
    
    # Step 4: Feature scaling for machine learning readiness
    preprocessing_report['steps'].append({
        'step': 'Feature Scaling Complete',
        'numeric_columns_processed': len(numeric_cols),
        'categorical_columns_processed': len(categorical_cols)
    })
    
    # Store report using object.__setattr__ to avoid pandas warnings
    object.__setattr__(df, '_preprocessing_report', preprocessing_report)
    
    return df


def standardize_data(df):
    """
    Standardize numeric columns using z-score normalization
    Handles mixed data types
    """
    df = df.copy()
    
    # Convert all numeric-like columns
    numeric_data = {}
    for col in df.columns:
        try:
            converted = pd.to_numeric(df[col], errors='coerce')
            if converted.notna().sum() > 0:
                numeric_data[col] = converted
        except:
            pass
    
    if numeric_data:
        numeric_df = pd.DataFrame(numeric_data)
        scaler = StandardScaler()
        # Avoid mean imputation as requested by user
        df[numeric_df.columns] = scaler.fit_transform(numeric_df.fillna(0))
    
    return df


def handle_categorical(df, method='label_encoding'):
    """
    Handle categorical variables
    method: 'label_encoding' or 'one_hot'
    """
    df = df.copy()
    categorical_cols = df.select_dtypes(include=['object']).columns.tolist()
    
    if method == 'label_encoding':
        for col in categorical_cols:
            try:
                df[col] = pd.factorize(df[col])[0]
            except:
                pass
    elif method == 'one_hot':
        try:
            df = pd.get_dummies(df, columns=categorical_cols, drop_first=True)
        except:
            pass
    
    return df


def get_preprocessing_report(df):
    """Return the preprocessing report stored in the dataframe"""
    if hasattr(df, '_preprocessing_report'):
        return df._preprocessing_report
    return None
