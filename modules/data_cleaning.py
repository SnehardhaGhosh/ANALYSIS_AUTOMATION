import pandas as pd
import numpy as np
from datetime import datetime

def clean_data(df):
    """
    Type-aware data cleaning pipeline
    - String columns: Replace missing with "unknown"
    - Numeric columns: Use statistical methods
    - Datetime: Keep as-is or interpolate
    """
    cleaning_report = {
        'original_shape': df.shape,
        'steps': []
    }
    
    df = df.copy()
    
    # Step 1: Remove duplicate rows (exact duplicates)
    initial_rows = len(df)
    df_deduplicated = df.drop_duplicates()
    duplicates_removed = initial_rows - len(df_deduplicated)
    
    if duplicates_removed > 0:
        df = df_deduplicated
        cleaning_report['steps'].append({
            'step': 'Remove Duplicate Rows',
            'description': 'Removed rows that are exact duplicates across all columns',
            'duplicates_removed': int(duplicates_removed),
            'rows_after': len(df)
        })
    
    # Step 2: Type-aware missing value handling
    missing_value_report = []
    
    for col in df.columns:
        col_dtype = infer_column_type(df[col])
        missing_count = df[col].isnull().sum()
        
        if missing_count == 0:
            continue
        
        missing_value_report.append({
            'column': col,
            'data_type': col_dtype,
            'missing_count': int(missing_count),
            'action': 'Handled'
        })
        
        if col_dtype == 'string':
            # For string columns: replace with "unknown"
            df[col] = df[col].fillna('unknown')
        
        elif col_dtype == 'numeric':
            # For numeric columns: use median (resistant to outliers)
            median_val = df[col].median()
            if pd.notna(median_val):
                df[col] = df[col].fillna(median_val)
            else:
                # If all values are missing, use 0
                df[col] = df[col].fillna(0)
        
        elif col_dtype == 'datetime':
            # For datetime: forward fill then backward fill
            df[col] = df[col].fillna(method='ffill').fillna(method='bfill')
        
        elif col_dtype == 'boolean':
            # For boolean: use mode (most common value)
            mode_val = df[col].mode()
            if len(mode_val) > 0:
                df[col] = df[col].fillna(mode_val[0])
            else:
                df[col] = df[col].fillna(False)
    
    if missing_value_report:
        cleaning_report['steps'].append({
            'step': 'Handle Missing Values',
            'description': 'Applied type-aware imputation strategies',
            'details': missing_value_report,
            'rows_after': len(df)
        })
    
    # Step 3: Fix string formatting issues
    string_cols = [col for col in df.columns if infer_column_type(df[col]) == 'string']
    string_fixes = []
    
    for col in string_cols:
        # Strip leading/trailing whitespace
        before = (df[col].astype(str).str.match(r'^\s|\s$')).sum()
        df[col] = df[col].astype(str).str.strip()
        if before > 0:
            string_fixes.append({
                'column': col,
                'issue': 'Leading/trailing whitespace',
                'count': int(before)
            })
    
    if string_fixes:
        cleaning_report['steps'].append({
            'step': 'Clean String Formatting',
            'description': 'Removed leading/trailing whitespace from string columns',
            'fixes': string_fixes
        })
    
    # Step 4: Handle outliers in numeric columns using IQR method
    numeric_cols = [col for col in df.columns if infer_column_type(df[col]) == 'numeric']
    outlier_report = []
    
    for col in numeric_cols:
        Q1 = df[col].quantile(0.25)
        Q3 = df[col].quantile(0.75)
        IQR = Q3 - Q1
        
        if IQR == 0:  # No variation in data
            continue
        
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
        outlier_count = outlier_mask.sum()
        
        if outlier_count > 0:
            # Cap outliers instead of removing (preserves row count)
            df.loc[df[col] < lower_bound, col] = lower_bound
            df.loc[df[col] > upper_bound, col] = upper_bound
            
            outlier_report.append({
                'column': col,
                'outliers_capped': int(outlier_count),
                'lower_bound': round(lower_bound, 4),
                'upper_bound': round(upper_bound, 4)
            })
    
    if outlier_report:
        cleaning_report['steps'].append({
            'step': 'Cap Outliers (IQR Method)',
            'description': 'Capped extreme values while preserving rows',
            'details': outlier_report,
            'rows_after': len(df)
        })
    
    # Step 5: Standardize column names
    original_cols = set(df.columns)
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('[^a-z0-9_]', '', regex=True)
    
    if len(original_cols) != len(set(df.columns)):
        cleaning_report['steps'].append({
            'step': 'Standardize Column Names',
            'description': 'Converted to lowercase, replaced spaces with underscores, removed special characters',
            'columns_standardized': len(original_cols)
        })
    
    # Step 6: Remove columns with all null/unknown values
    cols_to_drop = []
    for col in df.columns:
        col_dtype = infer_column_type(df[col])
        if col_dtype == 'string':
            valid_values = (df[col].astype(str).str.lower() != 'unknown').sum()
        else:
            valid_values = df[col].notna().sum()
        
        if valid_values == 0:
            cols_to_drop.append(col)
    
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
        cleaning_report['steps'].append({
            'step': 'Remove Empty Columns',
            'description': 'Removed columns with no valid data',
            'columns_removed': len(cols_to_drop),
            'removed_columns': cols_to_drop,
            'columns_after': len(df.columns)
        })
    
    # Step 7: Data consistency checks
    consistency_checks = []
    
    # Check for columns that should be numeric but aren't
    for col in df.columns:
        if 'amount' in col.lower() or 'price' in col.lower() or 'cost' in col.lower() or 'revenue' in col.lower():
            if infer_column_type(df[col]) != 'numeric':
                consistency_checks.append({
                    'column': col,
                    'issue': f"Column '{col}' appears to be numeric (based on name) but is stored as {infer_column_type(df[col])}",
                    'recommendation': 'Consider converting to numeric if possible'
                })
    
    if consistency_checks:
        cleaning_report['steps'].append({
            'step': 'Data Consistency Checks',
            'description': 'Identified potential type mismatches',
            'checks': consistency_checks
        })
    
    cleaning_report['final_shape'] = df.shape
    cleaning_report['rows_removed'] = initial_rows - len(df)
    df._cleaning_report = cleaning_report
    
    return df


def infer_column_type(col):
    """
    Intelligently infer column data type
    """
    col_clean = col.dropna()
    
    if len(col_clean) == 0:
        return 'unknown'
    
    # Check for boolean
    if col_clean.dtype == bool or set(col_clean.unique()).issubset({True, False, 0, 1}):
        return 'boolean'
    
    # Check for datetime
    if col_clean.dtype == 'datetime64[ns]':
        return 'datetime'
    
    # Try to detect numeric
    try:
        pd.to_numeric(col_clean, errors='coerce')
        numeric_count = pd.to_numeric(col_clean, errors='coerce').notna().sum()
        if numeric_count / len(col_clean) > 0.8:
            return 'numeric'
    except:
        pass
    
    # Default to string
    return 'string'


def get_cleaning_report(df):
    """Return the cleaning report stored in the dataframe"""
    if hasattr(df, '_cleaning_report'):
        return df._cleaning_report
    return None