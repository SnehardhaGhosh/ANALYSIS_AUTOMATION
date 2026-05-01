import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)


def normalize_columns(df):
    """Normalize column names for consistency"""
    try:
        df.columns = [col.strip().lower() for col in df.columns]
    except Exception as e:
        logger.warning(f"Column normalization warning: {e}")
    return df


def safe_to_numeric(series, handle_errors='coerce'):
    """
    Safely convert any series to numeric, handling all data types
    """
    try:
        return pd.to_numeric(series, errors=handle_errors)
    except Exception as e:
        logger.warning(f"Numeric conversion error: {e}")
        return pd.Series([np.nan] * len(series), index=series.index)


def safe_to_datetime(series, handle_errors='coerce'):
    """
    Safely convert any series to datetime, handling all data types
    """
    try:
        return pd.to_datetime(series, errors=handle_errors)
    except Exception as e:
        logger.warning(f"Datetime conversion error: {e}")
        return pd.Series([pd.NaT] * len(series), index=series.index)


def detect_numeric_column(series):
    """
    Detect if a column is predominantly numeric
    """
    try:
        converted = safe_to_numeric(series)
        numeric_ratio = converted.notna().sum() / len(series)
        return numeric_ratio > 0.8
    except:
        return False


def detect_datetime_column(series):
    """
    Detect if a column is predominantly datetime
    """
    try:
        converted = safe_to_datetime(series)
        datetime_ratio = converted.notna().sum() / len(series)
        return datetime_ratio > 0.8
    except:
        return False


def get_safe_stats(series):
    """
    Get statistics from a series safely, handling all data types
    """
    stats = {}
    try:
        converted = safe_to_numeric(series)
        valid_data = converted.dropna()
        
        if len(valid_data) > 0:
            stats['min'] = float(valid_data.min())
            stats['max'] = float(valid_data.max())
            stats['mean'] = float(valid_data.mean())
            stats['median'] = float(valid_data.median())
            stats['std'] = float(valid_data.std())
            stats['count'] = int(len(valid_data))
    except Exception as e:
        logger.warning(f"Stats calculation error: {e}")
        stats['error'] = str(e)
    
    return stats


def handle_mixed_types_in_column(series):
    """
    Intelligently handle a column with mixed types
    Returns: (converted_series, detected_type)
    """
    if series.dtype in ['int64', 'float64']:
        return series, 'numeric'
    
    if series.dtype == 'datetime64[ns]':
        return series, 'datetime'
    
    if series.dtype == 'bool':
        return series, 'boolean'
    
    # Try numeric
    numeric_converted = safe_to_numeric(series)
    numeric_ratio = numeric_converted.notna().sum() / len(series)
    if numeric_ratio > 0.8:
        return numeric_converted, 'numeric'
    
    # Try datetime
    datetime_converted = safe_to_datetime(series)
    datetime_ratio = datetime_converted.notna().sum() / len(series)
    if datetime_ratio > 0.8:
        return datetime_converted, 'datetime'
    
    # Default to string
    return series.astype(str), 'string'


def remove_empty_columns(df):
    """
    Remove columns with no valid data
    """
    try:
        cols_to_drop = []
        for col in df.columns:
            valid_count = df[col].notna().sum()
            if valid_count == 0:
                cols_to_drop.append(col)
        
        if cols_to_drop:
            df = df.drop(columns=cols_to_drop)
            logger.info(f"Removed {len(cols_to_drop)} empty columns: {cols_to_drop}")
    except Exception as e:
        logger.warning(f"Empty column removal error: {e}")
    
    return df


def detect_outliers_safe(series, method='iqr'):
    """
    Detect outliers in a series safely
    """
    try:
        numeric_series = safe_to_numeric(series)
        valid_data = numeric_series.dropna()
        
        if len(valid_data) < 4:
            return pd.Series(False, index=series.index)
        
        if method == 'iqr':
            Q1 = valid_data.quantile(0.25)
            Q3 = valid_data.quantile(0.75)
            IQR = Q3 - Q1
            
            if IQR == 0 or pd.isna(IQR):
                return pd.Series(False, index=series.index)
            
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
            
            outliers = (numeric_series < lower) | (numeric_series > upper)
            return outliers
        
        elif method == 'zscore':
            mean = valid_data.mean()
            std = valid_data.std()
            
            if std == 0 or pd.isna(std):
                return pd.Series(False, index=series.index)
            
            z_scores = np.abs((numeric_series - mean) / std)
            outliers = z_scores > 3
            return outliers
    
    except Exception as e:
        logger.warning(f"Outlier detection error: {e}")
        return pd.Series(False, index=series.index)


def cap_outliers(series, method='iqr'):
    """
    Cap outliers in a series instead of removing
    """
    try:
        numeric_series = safe_to_numeric(series)
        outlier_mask = detect_outliers_safe(series, method)
        
        if not outlier_mask.any():
            return numeric_series
        
        valid_data = numeric_series.dropna()
        
        if method == 'iqr':
            Q1 = valid_data.quantile(0.25)
            Q3 = valid_data.quantile(0.75)
            IQR = Q3 - Q1
            lower = Q1 - 1.5 * IQR
            upper = Q3 + 1.5 * IQR
        
        elif method == 'zscore':
            mean = valid_data.mean()
            std = valid_data.std()
            lower = mean - 3 * std
            upper = mean + 3 * std
        
        result = numeric_series.copy()
        result[result < lower] = lower
        result[result > upper] = upper
        
        return result
    
    except Exception as e:
        logger.warning(f"Outlier capping error: {e}")
        return numeric_series


def fill_missing_values_safe(df):
    """
    Fill missing values in dataframe safely by column type
    """
    try:
        df = df.copy()
        
        for col in df.columns:
            if df[col].isnull().sum() == 0:
                continue
            
            # Try to convert to numeric
            numeric_col = safe_to_numeric(df[col])
            if numeric_col.notna().sum() > 0.5 * len(df):
                # Use median for numeric
                valid_values = numeric_col.dropna()
                if len(valid_values) > 0:
                    df[col] = numeric_col.fillna(valid_values.median())
                continue
            
            # Try to convert to datetime
            datetime_col = safe_to_datetime(df[col])
            if datetime_col.notna().sum() > 0.5 * len(df):
                df[col] = datetime_col.fillna(method='ffill').fillna(method='bfill')
                continue
            
            # Default to string fill
            df[col] = df[col].fillna('unknown')
        
    except Exception as e:
        logger.warning(f"Missing value fill error: {e}")
    
    return df