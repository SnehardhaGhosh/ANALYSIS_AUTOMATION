import pandas as pd
import numpy as np


def execute_safe_query(df, query_text):
    """
    Enhanced rule-based execution for common data analysis queries
    """
    query = query_text.lower().strip()

    # Basic aggregations
    if any(word in query for word in ['total', 'sum', 'total of']):
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if numeric_cols.empty:
            return "No numeric columns found for summation"
        return df[numeric_cols].sum().to_dict()

    if any(word in query for word in ['average', 'mean', 'avg']):
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if numeric_cols.empty:
            return "No numeric columns found for averaging"
        return df[numeric_cols].mean().to_dict()

    if any(word in query for word in ['count', 'number of rows', 'how many']):
        return f"Dataset contains {len(df)} rows"

    if 'describe' in query or 'summary' in query:
        return df.describe().to_dict()

    if 'columns' in query or 'fields' in query:
        return f"Available columns: {', '.join(df.columns.tolist())}"

    # Profit calculations (assuming revenue and cost columns)
    if 'profit' in query:
        if 'revenue' in df.columns and 'cost' in df.columns:
            df_copy = df.copy()
            df_copy['profit'] = df_copy['revenue'] - df_copy['cost']
            
            if 'month' in df.columns or 'date' in df.columns:
                date_col = 'month' if 'month' in df.columns else 'date'
                result = df_copy.groupby(date_col)['profit'].sum().to_dict()
                return result
            
            return f"Total profit: {df_copy['profit'].sum()}"
        else:
            return "Profit calculation requires 'revenue' and 'cost' columns"

    # Correlation analysis
    if 'correlation' in query or 'correlate' in query:
        numeric_df = df.select_dtypes(include=[np.number])
        if len(numeric_df.columns) < 2:
            return "Need at least 2 numeric columns for correlation analysis"
        corr_matrix = numeric_df.corr()
        return corr_matrix.to_dict()

    # Max/Min queries
    if 'maximum' in query or 'max' in query or 'highest' in query:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if numeric_cols.empty:
            return "No numeric columns found"
        max_values = df[numeric_cols].max()
        return max_values.to_dict()

    if 'minimum' in query or 'min' in query or 'lowest' in query:
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if numeric_cols.empty:
            return "No numeric columns found"
        min_values = df[numeric_cols].min()
        return min_values.to_dict()

    return "Query not recognized. Try asking about totals, averages, correlations, or data summaries."