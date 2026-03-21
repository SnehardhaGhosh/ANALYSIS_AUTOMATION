import pandas as pd
import json


def generate_visualizations(df):
    """Generate automated visualizations based on dataset"""
    visualizations = {
        "statistics": get_statistics(df),
        "numeric_columns": get_numeric_insights(df),
        "categorical_summary": get_categorical_summary(df),
        "correlations": get_correlation_matrix(df)
    }
    return visualizations


def get_statistics(df):
    """Get basic statistics"""
    try:
        stats = df.describe().to_dict()
        return {
            "mean": {col: df[col].mean() for col in df.select_dtypes(include=['number']).columns},
            "median": {col: df[col].median() for col in df.select_dtypes(include=['number']).columns},
            "min": {col: df[col].min() for col in df.select_dtypes(include=['number']).columns},
            "max": {col: df[col].max() for col in df.select_dtypes(include=['number']).columns},
            "std": {col: df[col].std() for col in df.select_dtypes(include=['number']).columns},
        }
    except Exception as e:
        return {"error": str(e)}


def get_numeric_insights(df):
    """Get insights for numeric columns suitable for charting"""
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    charts = {}
    
    for col in numeric_cols:
        try:
            charts[col] = {
                "type": "line",  # Default to line chart
                "data": df[col].tolist(),
                "labels": [str(i) for i in range(len(df))],
                "min": float(df[col].min()),
                "max": float(df[col].max()),
                "sum": float(df[col].sum()) if 'profit' in col.lower() or 'revenue' in col.lower() or 'cost' in col.lower() else None
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
            value_counts = df[col].value_counts().to_dict()
            summary[col] = {
                "unique_values": len(value_counts),
                "distribution": value_counts
            }
        except Exception as e:
            continue
    
    return summary


def get_correlation_matrix(df):
    """Get correlation matrix for numeric columns"""
    try:
        numeric_df = df.select_dtypes(include=['number'])
        if len(numeric_df.columns) > 1:
            corr = numeric_df.corr().to_dict()
            return corr
        return None
    except Exception as e:
        return None


def format_visualizations_for_json(visualizations):
    """Convert visualizations to JSON-serializable format"""
    result = {}
    
    for key, value in visualizations.items():
        if value is None:
            continue
        try:
            result[key] = json.loads(json.dumps(value, default=str))
        except:
            try:
                result[key] = str(value)
            except:
                result[key] = "Cannot serialize"
    
    return result
