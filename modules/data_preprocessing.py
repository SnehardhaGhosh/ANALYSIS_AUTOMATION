import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler

def preprocess_data(df):
    """
    Comprehensive data preprocessing pipeline
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
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    log_transformed = []
    
    for col in numeric_cols:
        if df[col].min() > 0:  # Log transformation requires positive values
            skewness = df[col].skew()
            if abs(skewness) > 2:  # Highly skewed
                df[col] = np.log1p(df[col])
                log_transformed.append(col)
    
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
            df[col] = scaler.fit_transform(df[[col]])
            scaled_cols.append(col)
    
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
    
    df._preprocessing_report = preprocessing_report
    return df


def standardize_data(df):
    """
    Standardize numeric columns using z-score normalization
    """
    df = df.copy()
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    scaler = StandardScaler()
    df[numeric_cols] = scaler.fit_transform(df[numeric_cols])
    
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
            df[col] = pd.factorize(df[col])[0]
    elif method == 'one_hot':
        df = pd.get_dummies(df, columns=categorical_cols, drop_first=True)
    
    return df


def get_preprocessing_report(df):
    """Return the preprocessing report stored in the dataframe"""
    if hasattr(df, '_preprocessing_report'):
        return df._preprocessing_report
    return None
