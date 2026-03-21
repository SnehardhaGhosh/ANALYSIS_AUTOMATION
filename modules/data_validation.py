import pandas as pd
import numpy as np
import re

def validate_data(df):
    """
    Comprehensive data validation with analyst-friendly reporting
    Detects: null counts, missing values, wrong patterns, data types
    """
    report = {
        'dataset_info': {
            'total_rows': int(len(df)),
            'total_columns': len(df.columns)
        },
        'data_quality_analysis': {
            'columns': {}
        },
        'data_type_analysis': {},
        'pattern_validation': {},
        'quality_warnings': [],
        'quality_score': 0
    }
    
    # Analyze each column
    for col in df.columns:
        col_data = df[col]
        col_analysis = {}
        
        # 1. Data Type Detection
        inferred_dtype = infer_column_type(col_data)
        col_analysis['detected_type'] = inferred_dtype
        col_analysis['pandas_dtype'] = str(col_data.dtype)
        
        # 2. Null & Missing Values Analysis
        null_count = int(col_data.isnull().sum())
        # For string columns, also check for empty strings, whitespace
        if inferred_dtype == 'string':
            empty_str_count = (col_data.fillna('').astype(str).str.strip() == '').sum()
            missing_count = null_count + empty_str_count
        else:
            missing_count = null_count
        
        col_analysis['null_count'] = null_count
        col_analysis['missing_values_count'] = missing_count
        col_analysis['non_null_count'] = int(col_data.notna().sum())
        col_analysis['missing_percentage'] = round(missing_count / len(df) * 100, 2)
        
        # 3. Data Type Specific Analysis
        if inferred_dtype == 'numeric':
            valid_numeric = col_data.dropna()
            col_analysis['statistics'] = {
                'min': float(valid_numeric.min()) if len(valid_numeric) > 0 else None,
                'max': float(valid_numeric.max()) if len(valid_numeric) > 0 else None,
                'mean': float(valid_numeric.mean()) if len(valid_numeric) > 0 else None,
                'median': float(valid_numeric.median()) if len(valid_numeric) > 0 else None,
                'std_dev': float(valid_numeric.std()) if len(valid_numeric) > 0 else None
            }
            
            # Check for outliers using IQR
            Q1 = valid_numeric.quantile(0.25)
            Q3 = valid_numeric.quantile(0.75)
            IQR = Q3 - Q1
            outlier_count = ((valid_numeric < Q1 - 1.5 * IQR) | (valid_numeric > Q3 + 1.5 * IQR)).sum()
            col_analysis['outlier_count'] = int(outlier_count)
            col_analysis['outlier_percentage'] = round(outlier_count / len(valid_numeric) * 100, 2) if len(valid_numeric) > 0 else 0
        
        elif inferred_dtype == 'datetime':
            col_analysis['date_range'] = {
                'min': str(col_data.min()),
                'max': str(col_data.max())
            }
        
        elif inferred_dtype == 'string':
            non_null = col_data.dropna()
            non_empty = non_null[non_null.astype(str).str.strip() != '']
            col_analysis['unique_values'] = int(col_data.nunique())
            col_analysis['top_values'] = non_empty.value_counts().head(3).to_dict()
            col_analysis['avg_string_length'] = round(non_empty.astype(str).str.len().mean(), 2) if len(non_empty) > 0 else 0
        
        elif inferred_dtype == 'boolean':
            col_analysis['value_counts'] = col_data.value_counts().to_dict()
        
        # 4. Pattern Validation
        pattern_issues = detect_pattern_issues(col_data, inferred_dtype, col)
        if pattern_issues:
            col_analysis['pattern_issues'] = pattern_issues
            report['pattern_validation'][col] = pattern_issues
        
        report['data_quality_analysis']['columns'][col] = col_analysis
        report['data_type_analysis'][col] = inferred_dtype
    
    # 5. Generate Quality Warnings
    warnings = []
    total_quality_issues = 0
    
    for col, col_info in report['data_quality_analysis']['columns'].items():
        # High missing percentage
        if col_info['missing_percentage'] > 50:
            warnings.append({
                'column': col,
                'severity': 'critical',
                'issue': f"High missing values: {col_info['missing_percentage']:.1f}%",
                'action': 'Consider column removal or imputation strategy'
            })
            total_quality_issues += 3
        elif col_info['missing_percentage'] > 20:
            warnings.append({
                'column': col,
                'severity': 'warning',
                'issue': f"Moderate missing values: {col_info['missing_percentage']:.1f}%",
                'action': 'Plan imputation (use "unknown" for strings, median for numbers)'
            })
            total_quality_issues += 2
        
        # Outliers in numeric columns
        if col_info.get('outlier_count', 0) > 0:
            if col_info['outlier_percentage'] > 10:
                warnings.append({
                    'column': col,
                    'severity': 'warning',
                    'issue': f"Significant outliers detected: {col_info['outlier_percentage']:.1f}%",
                    'action': 'Review or remove outliers (IQR method)'
                })
                total_quality_issues += 1
        
        # Pattern issues
        if 'pattern_issues' in col_info:
            for pattern_issue in col_info['pattern_issues']:
                warnings.append({
                    'column': col,
                    'severity': 'info',
                    'issue': pattern_issue,
                    'action': 'Review and handle pattern violations'
                })
                total_quality_issues += 1
    
    report['quality_warnings'] = warnings
    
    # 6. Calculate Overall Quality Score
    max_issues = len(df.columns) * 5
    quality_score = max(0, 100 - (total_quality_issues / max_issues * 100))
    report['quality_score'] = round(quality_score, 2)
    
    return report


def infer_column_type(col):
    """
    Intelligently infer column data type
    Returns: 'numeric', 'string', 'datetime', 'boolean', 'mixed'
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
        if numeric_count / len(col_clean) > 0.8:  # 80% are numeric
            return 'numeric'
    except:
        pass
    
    # Check for datetime strings
    sample = col_clean.astype(str).iloc[:10]
    date_pattern = r'^\d{4}-\d{2}-\d{2}|^\d{2}/\d{2}/\d{4}|^\d{1,2}-\w+-\d{2,4}'
    if sample.str.match(date_pattern).any():
        return 'datetime'
    
    # Default to string
    return 'string'


def detect_pattern_issues(col, dtype, col_name):
    """
    Detect improper patterns in data (formatting issues, inconsistencies)
    """
    issues = []
    col_clean = col.dropna()
    
    if dtype == 'numeric':
        # Check for numbers stored as strings
        try:
            numeric_vals = pd.to_numeric(col, errors='coerce')
            if numeric_vals.isna().sum() > 0 and col.notna().sum() > 0:
                non_numeric_count = col.astype(str)[numeric_vals.isna() & col.notna()].count()
                if non_numeric_count > 0:
                    issues.append(f"Non-numeric values found in numeric column: {non_numeric_count} values")
        except:
            pass
    
    elif dtype == 'string':
        # Check for leading/trailing whitespace
        whitespace_count = col_clean.astype(str).str.match(r'^\s|\s$').sum()
        if whitespace_count > 0:
            issues.append(f"Leading/trailing whitespace: {whitespace_count} values")
        
        # Check for special encoding issues
        try:
            col_clean.astype(str).encode('ascii')
        except UnicodeEncodeError:
            issues.append("Contains non-ASCII characters (may cause issues)")
        
        # Check for very long strings (potential data entry errors)
        long_strings = (col_clean.astype(str).str.len() > 500).sum()
        if long_strings > 0:
            issues.append(f"Unusually long strings: {long_strings} values (>500 chars)")
    
    elif dtype == 'datetime':
        # Check for mixed date formats
        try:
            parsed = pd.to_datetime(col_clean, errors='coerce')
            if parsed.isna().sum() > 0:
                unparseable = (parsed.isna() & col_clean.notna()).sum()
                issues.append(f"Unparseable dates: {unparseable} values (check date format)")
        except:
            issues.append("Multiple date formats or invalid dates detected")
    
    return issues


def check_data_quality(df):
    """
    Overall data quality score (0-100)
    """
    report = validate_data(df)
    return report['quality_score']