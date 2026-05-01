import pandas as pd
import numpy as np


def safe_to_numeric(series):
    """Safely convert any data type to numeric, handling mixed types"""
    try:
        return pd.to_numeric(series, errors='coerce')
    except:
        return pd.Series([np.nan] * len(series), index=series.index)


def execute_safe_query(df, query_text):
    """
    Enhanced rule-based execution for common data analysis queries
    Handles all data types: dictionary, list, array, regex, str, int, float
    """
    query = query_text.lower().strip()

    # Basic aggregations - coerce to numeric for any data type
    if any(word in query for word in ['total', 'sum', 'total of']):
        numeric_data = {}
        for col in df.columns:
            numeric_col = safe_to_numeric(df[col])
            if numeric_col.notna().sum() > 0:
                numeric_data[col] = float(numeric_col.sum())
        
        if numeric_data:
            return numeric_data
        return "No numeric data found for summation"

    if any(word in query for word in ['average', 'mean', 'avg']):
        numeric_data = {}
        for col in df.columns:
            numeric_col = safe_to_numeric(df[col])
            if numeric_col.notna().sum() > 0:
                numeric_data[col] = float(numeric_col.mean())
        
        if numeric_data:
            return numeric_data
        return "No numeric data found for averaging"

    if any(word in query for word in ['count', 'number of rows', 'how many']):
        return f"Dataset contains {len(df)} rows"

    if 'describe' in query or 'summary' in query:
        try:
            numeric_df = df.select_dtypes(include=[np.number])
            if len(numeric_df.columns) > 0:
                return numeric_df.describe().to_dict()
            else:
                return "No numeric columns for description"
        except:
            return "Could not generate summary"

    if 'columns' in query or 'fields' in query:
        return f"Available columns: {', '.join(df.columns.tolist())}"

    # Profit calculations (coerce to numeric if needed)
    if 'profit' in query:
        if 'revenue' in df.columns and 'cost' in df.columns:
            df_copy = df.copy()
            revenue = safe_to_numeric(df_copy['revenue'])
            cost = safe_to_numeric(df_copy['cost'])
            df_copy['profit'] = revenue - cost
            
            if 'month' in df.columns or 'date' in df.columns:
                date_col = 'month' if 'month' in df.columns else 'date'
                try:
                    result = df_copy.groupby(date_col)['profit'].sum().to_dict()
                    return result
                except:
                    pass
            
            total_profit = df_copy['profit'].sum()
            return f"Total profit: {total_profit if pd.notna(total_profit) else 0}"
        else:
            return "Profit calculation requires 'revenue' and 'cost' columns"

    # Correlation analysis - coerce all to numeric
    if 'correlation' in query or 'correlate' in query:
        numeric_data = {}
        for col in df.select_dtypes(include=[np.number]).columns:
            numeric_data[col] = df[col]
        
        # Also try to coerce non-numeric columns
        for col in df.columns:
            if col not in numeric_data:
                converted = safe_to_numeric(df[col])
                if converted.notna().sum() > 0.5 * len(df):  # At least 50% numeric
                    numeric_data[col] = converted
        
        if len(numeric_data) < 2:
            return "Need at least 2 numeric columns for correlation analysis"
        
        numeric_df = pd.DataFrame(numeric_data)
        corr_matrix = numeric_df.corr()
        return corr_matrix.to_dict()

    # Max/Min queries - handle mixed types
    if 'maximum' in query or 'max' in query or 'highest' in query:
        max_values = {}
        for col in df.columns:
            numeric_col = safe_to_numeric(df[col])
            if numeric_col.notna().sum() > 0:
                max_values[col] = float(numeric_col.max())
        
        if max_values:
            return max_values
        return "No numeric columns found"

    if 'minimum' in query or 'min' in query or 'lowest' in query:
        min_values = {}
        for col in df.columns:
            numeric_col = safe_to_numeric(df[col])
            if numeric_col.notna().sum() > 0:
                min_values[col] = float(numeric_col.min())
        
        if min_values:
            return min_values
        return "No numeric columns found"

    return "Query not recognized. Try asking about totals, averages, correlations, or data summaries."