import pandas as pd
import json
import numpy as np


def safe_to_numeric(series):
    """Safely convert any data type to numeric"""
    try:
        return pd.to_numeric(series, errors='coerce')
    except:
        return pd.Series([np.nan] * len(series), index=series.index)


def generate_visualizations(df):
    """Generate automated visualizations based on dataset, handling all data types"""
    visualizations = {
        "statistics": get_statistics(df),
        "numeric_columns": get_numeric_insights(df),
        "categorical_summary": get_categorical_summary(df),
        "correlations": get_correlation_matrix(df)
    }
    return visualizations


def get_statistics(df):
    """Get basic statistics, handling all data types"""
    try:
        stats = {}
        
        # Try numeric columns first
        numeric_df = df.select_dtypes(include=['number'])
        
        # Also coerce other columns to numeric
        for col in df.columns:
            if col not in numeric_df.columns:
                converted = safe_to_numeric(df[col])
                if converted.notna().sum() > 0:
                    numeric_df[col] = converted
        
        if len(numeric_df.columns) > 0:
            stats = {
                "mean": {col: float(numeric_df[col].mean()) if pd.notna(numeric_df[col].mean()) else None 
                        for col in numeric_df.columns},
                "median": {col: float(numeric_df[col].median()) if pd.notna(numeric_df[col].median()) else None 
                          for col in numeric_df.columns},
                "min": {col: float(numeric_df[col].min()) if pd.notna(numeric_df[col].min()) else None 
                       for col in numeric_df.columns},
                "max": {col: float(numeric_df[col].max()) if pd.notna(numeric_df[col].max()) else None 
                       for col in numeric_df.columns},
                "std": {col: float(numeric_df[col].std()) if pd.notna(numeric_df[col].std()) else None 
                       for col in numeric_df.columns},
            }
        
        return stats
    except Exception as e:
        return {"error": str(e)}


def get_numeric_insights(df):
    """Get insights for numeric columns suitable for charting"""
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    
    # Also include columns that can be coerced to numeric
    for col in df.columns:
        if col not in numeric_cols:
            converted = safe_to_numeric(df[col])
            if converted.notna().sum() > 0.5 * len(df):  # At least 50% numeric
                numeric_cols.append(col)
    
    charts = {}
    
    for col in numeric_cols:
        try:
            # Get numeric version of the column
            if col in df.columns:
                col_data = df[col]
            else:
                col_data = safe_to_numeric(df[col])
            
            col_data = safe_to_numeric(col_data)
            valid_data = col_data.dropna()
            
            if len(valid_data) > 0:
                charts[col] = {
                    "type": "line",
                    "data": [float(x) if pd.notna(x) else None for x in col_data],
                    "labels": [str(i) for i in range(len(col_data))],
                    "min": float(valid_data.min()),
                    "max": float(valid_data.max()),
                    "sum": float(valid_data.sum()) if 'profit' in col.lower() or 'revenue' in col.lower() or 'cost' in col.lower() else None
                }
        except Exception as e:
            continue
    
    return charts


def get_categorical_summary(df):
    """Get categorical column summaries"""
    cat_cols = df.select_dtypes(include=['object']).columns.tolist()
    summary = {}
    
    for col in cat_cols:
        try:
            value_counts = df[col].value_counts().head(10).to_dict()
            summary[col] = {
                "unique_values": len(df[col].unique()),
                "distribution": value_counts
            }
        except Exception as e:
            continue
    
    return summary


def get_correlation_matrix(df):
    """Get correlation matrix for numeric columns, handling all data types"""
    try:
        # Get native numeric columns
        numeric_df = df.select_dtypes(include=['number']).copy()
        
        # Also try to coerce other columns
        for col in df.columns:
            if col not in numeric_df.columns:
                converted = safe_to_numeric(df[col])
                if converted.notna().sum() > 0:
                    numeric_df[col] = converted
        
        if len(numeric_df.columns) > 1:
            corr = numeric_df.corr().to_dict()
            return corr
        return None
    except Exception as e:
        return None


def get_predictive_trends(df):
    """Analyze temporal patterns and provide simple predictive trends"""
    try:
        # Find potential date columns
        date_cols = []
        for col in df.columns:
            if 'date' in col.lower() or 'time' in col.lower() or 'year' in col.lower() or 'month' in col.lower():
                date_cols.append(col)
        
        # Also check for datetime types
        dt_cols = df.select_dtypes(include=['datetime']).columns.tolist()
        date_cols = list(set(date_cols + dt_cols))
        
        # If no date columns, use index as time proxy
        time_series_data = {}
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        
        if not numeric_cols:
            return None
            
        target_col = numeric_cols[0] # Default to first numeric column
        # Try to find 'revenue', 'sales', 'profit', etc.
        for col in numeric_cols:
            if any(x in col.lower() for x in ['revenue', 'sales', 'profit', 'total', 'count']):
                target_col = col
                break
        
        # Prepare data
        values = df[target_col].dropna().values.tolist()
        if len(values) < 5:
            return None
            
        # Simple Prediction: Moving Average + Trend Line
        # We'll provide the original data and a 'forecast' (next 5 points)
        
        # Simple Linear Trend
        n = len(values)
        x = np.arange(n)
        y = np.array(values)
        
        # Regression: y = mx + c
        if n > 1:
            m, c = np.polyfit(x, y, 1)
            trend_line = [float(m * i + c) for i in range(n + 5)] # n original + 5 forecast
        else:
            trend_line = values + [values[-1]] * 5
            
        return {
            "target": target_col,
            "historical": [float(v) for v in values],
            "forecast": trend_line[n:],
            "labels": [f"T-{n-i}" for i in range(n)] + [f"F+{i+1}" for i in range(5)]
        }
    except Exception as e:
        return {"error": str(e)}


def format_visualizations_for_json(visualizations):
    """Convert visualizations to JSON-serializable format"""
    result = {}
    
    for key, value in visualizations.items():
        if value is None:
            continue
        try:
            # Handle numpy arrays and other non-standard types
            if isinstance(value, np.ndarray):
                result[key] = value.tolist()
            elif isinstance(value, dict):
                result[key] = json.loads(json.dumps(value, default=str))
            else:
                result[key] = value
        except:
            result[key] = str(value)
    
    return result
