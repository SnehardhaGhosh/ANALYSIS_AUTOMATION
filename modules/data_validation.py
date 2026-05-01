import pandas as pd
import numpy as np
import re
import logging
from modules.data_cleaning import get_cached_type

logger = logging.getLogger(__name__)

def validate_data(df):
    """
    Comprehensive data validation with analyst-friendly reporting
    Detects: null counts, missing values, wrong patterns, data types
    Includes error handling to prevent crashes
    """
    try:
        return _validate_data_internal(df)
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        # Return safe default report on error
        return {
            'dataset_info': {
                'total_rows': int(len(df)),
                'total_columns': len(df.columns)
            },
            'data_quality_analysis': {
                'columns': {}
            },
            'data_type_analysis': {},
            'pattern_validation': {},
            'quality_warnings': [
                {
                    'severity': 'warning',
                    'issue': f'Validation warning: {str(e)}',
                    'action': 'Continue with caution'
                }
            ],
            'quality_score': 50
        }

def _validate_data_internal(df):
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
    
    # Analyze each column with error protection
    for col in df.columns:
        try:
            col_data = df[col]
            col_analysis = {}
            
            # 1. Data Type Detection (use cached type to avoid redundant calls)
            try:
                inferred_dtype = get_cached_type(col, col_data)
            except Exception as type_err:
                logger.warning(f"Could not infer type for column {col}: {type_err}")
                inferred_dtype = 'unknown'
            
            col_analysis['detected_type'] = inferred_dtype
            col_analysis['pandas_dtype'] = str(col_data.dtype)
            
            # 2. Null & Missing Values Analysis
            null_count = int(col_data.isnull().sum())
            # For string columns, also check for empty strings, whitespace
            if inferred_dtype == 'string':
                try:
                    empty_str_count = (col_data.fillna('').astype(str).str.strip() == '').sum()
                    missing_count = null_count + int(empty_str_count)
                except:
                    missing_count = null_count
            else:
                missing_count = null_count
            
            col_analysis['null_count'] = null_count
            col_analysis['missing_values_count'] = missing_count
            col_analysis['non_null_count'] = int(col_data.notna().sum())
            col_analysis['missing_percentage'] = round(missing_count / len(df) * 100, 2) if len(df) > 0 else 0
            
            # 3. Data Type Specific Analysis
            if inferred_dtype == 'numeric':
                try:
                    # Coerce to numeric, handling mixed types
                    valid_numeric = pd.to_numeric(col_data, errors='coerce')
                    valid_numeric = valid_numeric.dropna()
                    
                    if len(valid_numeric) > 0:
                        col_analysis['statistics'] = {
                            'min': round(float(valid_numeric.min()), 2),
                            'max': round(float(valid_numeric.max()), 2),
                            'mean': round(float(valid_numeric.mean()), 2),
                            'median': round(float(valid_numeric.median()), 2),
                            'std_dev': round(float(valid_numeric.std()), 2)
                        }
                        
                        # Check for outliers using IQR
                        Q1 = valid_numeric.quantile(0.25)
                        Q3 = valid_numeric.quantile(0.75)
                        IQR = Q3 - Q1
                        
                        if IQR > 0:  # Only check outliers if there's variation
                            outlier_count = ((valid_numeric < Q1 - 1.5 * IQR) | (valid_numeric > Q3 + 1.5 * IQR)).sum()
                            col_analysis['outlier_count'] = int(outlier_count)
                            col_analysis['outlier_percentage'] = round(outlier_count / len(valid_numeric) * 100, 2)
                        else:
                            col_analysis['outlier_count'] = 0
                            col_analysis['outlier_percentage'] = 0
                    else:
                        col_analysis['statistics'] = None
                        col_analysis['outlier_count'] = 0
                        col_analysis['outlier_percentage'] = 0
                except Exception as num_err:
                    logger.warning(f"Error analyzing numeric column {col}: {num_err}")
                    col_analysis['statistics'] = {'error': 'Could not compute statistics'}
                    col_analysis['outlier_count'] = 0
                    col_analysis['outlier_percentage'] = 0
            
            elif inferred_dtype == 'datetime':
                try:
                    # Try to coerce to datetime, handling mixed types
                    datetime_col = pd.to_datetime(col_data, errors='coerce')
                    valid_datetime = datetime_col.dropna()
                    
                    if len(valid_datetime) > 0:
                        col_analysis['date_range'] = {
                            'min': valid_datetime.min().strftime('%Y-%m-%d'),
                            'max': valid_datetime.max().strftime('%Y-%m-%d')
                        }
                    else:
                        col_analysis['date_range'] = {}
                except Exception as dt_err:
                    logger.warning(f"Error analyzing datetime column {col}: {dt_err}")
                    col_analysis['date_range'] = {}
            
            elif inferred_dtype == 'string':
                try:
                    non_null = col_data.dropna()
                    non_empty = non_null[non_null.astype(str).str.strip() != '']
                    col_analysis['unique_values'] = int(col_data.nunique())
                    col_analysis['top_values'] = non_empty.value_counts().head(3).to_dict()
                    col_analysis['avg_string_length'] = round(non_empty.astype(str).str.len().mean(), 2) if len(non_empty) > 0 else 0
                except Exception as str_err:
                    logger.warning(f"Error analyzing string column {col}: {str_err}")
                    col_analysis['unique_values'] = int(col_data.nunique())
                    col_analysis['top_values'] = {}
                    col_analysis['avg_string_length'] = 0
            
            elif inferred_dtype == 'boolean':
                try:
                    col_analysis['value_counts'] = col_data.value_counts().to_dict()
                except Exception as bool_err:
                    logger.warning(f"Error analyzing boolean column {col}: {bool_err}")
                    col_analysis['value_counts'] = {}
            
            # 4. Pattern Validation
            try:
                pattern_issues = detect_pattern_issues(col_data, inferred_dtype, col)
                if pattern_issues:
                    col_analysis['pattern_issues'] = pattern_issues
                    report['pattern_validation'][col] = pattern_issues
            except Exception as pattern_err:
                logger.warning(f"Error detecting patterns for column {col}: {pattern_err}")
            
            report['data_quality_analysis']['columns'][col] = col_analysis
            report['data_type_analysis'][col] = inferred_dtype
        
        except Exception as col_err:
            logger.warning(f"Error analyzing column {col}: {str(col_err)}")
            # Add minimal analysis for failed column
            report['data_quality_analysis']['columns'][col] = {
                'detected_type': 'unknown',
                'pandas_dtype': str(df[col].dtype),
                'error': f'Analysis failed: {str(col_err)}'
            }
            report['data_type_analysis'][col] = 'unknown'
    
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
    Handles any data type including dict, list, array, regex, int, float, str
    """
    try:
        col_clean = col.dropna()
        
        if len(col_clean) == 0:
            return 'unknown'
        
        # Check for boolean
        if col_clean.dtype == bool or set(col_clean.unique()).issubset({True, False, 0, 1}):
            return 'boolean'
        
        # Check for datetime
        if col_clean.dtype == 'datetime64[ns]':
            return 'datetime'
        
        # Try to detect numeric (coerce any type to numeric)
        try:
            numeric_converted = pd.to_numeric(col_clean, errors='coerce')
            numeric_count = numeric_converted.notna().sum()
            if numeric_count / len(col_clean) > 0.8:  # 80% are numeric
                return 'numeric'
        except:
            pass
        
        # Check for datetime strings
        try:
            sample = col_clean.astype(str).iloc[:min(10, len(col_clean))]
            date_pattern = r'^\d{4}-\d{2}-\d{2}|^\d{2}/\d{2}/\d{4}|^\d{1,2}-\w+-\d{2,4}'
            if sample.str.match(date_pattern).any():
                return 'datetime'
        except:
            pass
        
        # Default to string (handles all other types: dict, list, regex, etc.)
        return 'string'
    except:
        # Fallback for any unexpected type handling
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
            for val in col_clean.astype(str):
                try:
                    val.encode('ascii')
                except UnicodeEncodeError:
                    issues.append("Contains non-ASCII characters (may cause issues)")
                    break
        except Exception:
            pass
        
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