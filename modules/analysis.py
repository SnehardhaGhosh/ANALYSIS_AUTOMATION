import pandas as pd
import numpy as np


def safe_to_numeric(series):
    """Safely convert any data type to numeric, handling mixed types"""
    try:
        return pd.to_numeric(series, errors='coerce')
    except:
        return pd.Series([np.nan] * len(series), index=series.index)


def add_profit_column(df):
    """Add profit column, coercing revenue and cost to numeric if needed"""
    try:
        if 'revenue' in df.columns and 'cost' in df.columns:
            revenue = safe_to_numeric(df['revenue'])
            cost = safe_to_numeric(df['cost'])
            df['profit'] = revenue - cost
    except Exception as e:
        print(f"Warning: Could not add profit column: {e}")
    return df


def summary_stats(df):
    """Generate summary statistics, handling mixed data types"""
    try:
        # Only describe numeric columns
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) > 0:
            return numeric_df.describe().to_dict()
        else:
            # Try to coerce all columns to numeric
            numeric_data = {}
            for col in df.columns:
                converted = safe_to_numeric(df[col])
                if converted.notna().sum() > 0:
                    numeric_data[col] = converted
            
            if numeric_data:
                temp_df = pd.DataFrame(numeric_data)
                return temp_df.describe().to_dict()
            else:
                return {"message": "No numeric data available for summary"}
    except Exception as e:
        return {"error": f"Could not generate summary: {str(e)}"}