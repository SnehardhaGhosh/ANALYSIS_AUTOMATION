import pandas as pd
import numpy as np

def safe_numeric_conversion(series):
    """Safely convert series to numeric, handling all data types"""
    try:
        return pd.to_numeric(series, errors='coerce')
    except:
        return pd.Series([np.nan] * len(series), index=series.index)


def transform_data(df):
    """
    Comprehensive data transformation pipeline including feature engineering
    Production-grade with all type handling
    """
    transformation_report = {
        'new_features': [],
        'steps': [],
        'errors': []
    }
    
    df = df.copy()
    original_cols = set(df.columns)
    
    # Step 1: Create aggregate features from numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # Also try to coerce other columns to numeric
    for col in df.columns:
        if col not in numeric_cols:
            converted = safe_numeric_conversion(df[col])
            if converted.notna().sum() > 0.5 * len(df):  # At least 50% numeric
                numeric_cols.append(col)
                df[col] = converted
    
    if len(numeric_cols) > 0:
        try:
            # Total sum feature
            df['total_numeric_sum'] = df[numeric_cols].sum(axis=1, skipna=True)
            transformation_report['new_features'].append('total_numeric_sum')
            
            # Mean of numeric columns
            df['avg_numeric'] = df[numeric_cols].mean(axis=1, skipna=True)
            transformation_report['new_features'].append('avg_numeric')
            
            # Standard deviation
            if len(numeric_cols) > 1:
                df['numeric_std'] = df[numeric_cols].std(axis=1, skipna=True)
                transformation_report['new_features'].append('numeric_std')
        except Exception as agg_err:
            transformation_report['errors'].append(f"Aggregation error: {str(agg_err)}")
    
    transformation_report['steps'].append({
        'step': 'Create Aggregate Features',
        'features_created': len([f for f in transformation_report['new_features'] if 'numeric' in f]),
        'numeric_columns_found': len(numeric_cols)
    })
    
    # Step 2: Create ratio features (if revenue and cost exist)
    if 'revenue' in df.columns and 'cost' in df.columns:
        try:
            revenue = safe_numeric_conversion(df['revenue'])
            cost = safe_numeric_conversion(df['cost'])
            
            # Avoid division by zero
            with np.errstate(divide='ignore', invalid='ignore'):
                profit_margin = (revenue - cost) / revenue * 100
                profit_margin = profit_margin.replace([np.inf, -np.inf], 0).fillna(0).round(2)
            
            df['profit_margin'] = profit_margin
            transformation_report['new_features'].append('profit_margin')
            transformation_report['steps'].append({
                'step': 'Create Business Metrics',
                'metrics_created': ['profit_margin']
            })
        except Exception as metric_err:
            transformation_report['errors'].append(f"Metric creation error: {str(metric_err)}")
    
    # Step 3: Create time-based features if date column exists
    date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
    if len(date_cols) > 0:
        for col in date_cols:
            try:
                df[f'{col}_year'] = df[col].dt.year
                df[f'{col}_month'] = df[col].dt.month
                df[f'{col}_quarter'] = df[col].dt.quarter
                transformation_report['new_features'].extend([
                    f'{col}_year', f'{col}_month', f'{col}_quarter'
                ])
            except Exception as date_err:
                transformation_report['errors'].append(f"Date feature error on {col}: {str(date_err)}")
        
        transformation_report['steps'].append({
            'step': 'Extract Time-Based Features',
            'date_columns_processed': len(date_cols)
        })
    
    # Step 4: Binning for numerical columns (create categories)
    binned_cols = []
    for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
        try:
            col_data = safe_numeric_conversion(df[col])
            col_min = col_data.min()
            col_max = col_data.max()
            
            if pd.notna(col_min) and pd.notna(col_max) and col_max - col_min > 0:
                df[f'{col}_binned'] = pd.cut(col_data, bins=5, labels=['Very_Low', 'Low', 'Medium', 'High', 'Very_High'], duplicates='drop')
                transformation_report['new_features'].append(f'{col}_binned')
                binned_cols.append(f'{col}_binned')
        except Exception as bin_err:
            transformation_report['errors'].append(f"Binning error on {col}: {str(bin_err)}")
    
    if binned_cols:
        transformation_report['steps'].append({
            'step': 'Bin Numeric Columns',
            'binned_columns': binned_cols
        })
    
    # Step 5: Create interaction features (for top 2 numeric columns)
    if len(numeric_cols) >= 2:
        try:
            col1 = safe_numeric_conversion(df[numeric_cols[0]])
            col2 = safe_numeric_conversion(df[numeric_cols[1]])
            
            with np.errstate(invalid='ignore'):
                df[f'{numeric_cols[0]}_x_{numeric_cols[1]}'] = col1 * col2
            
            transformation_report['new_features'].append(f'{numeric_cols[0]}_x_{numeric_cols[1]}')
            transformation_report['steps'].append({
                'step': 'Create Interaction Features',
                'interactions_created': 1
            })
        except Exception as interact_err:
            transformation_report['errors'].append(f"Interaction error: {str(interact_err)}")
    
    transformation_report['total_features_created'] = len(df.columns) - len(original_cols)
    transformation_report['original_columns'] = len(original_cols)
    transformation_report['final_columns'] = len(df.columns)
    
    # Store report using object.__setattr__ to avoid pandas warnings
    object.__setattr__(df, '_transformation_report', transformation_report)
    
    return df


def aggregate_by_column(df, group_col, agg_cols=None):
    """
    Aggregate data by a specific column
    Handles mixed types safely
    """
    try:
        if agg_cols is None:
            agg_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            # Also try to coerce other columns
            for col in df.columns:
                if col not in agg_cols and col != group_col:
                    converted = safe_numeric_conversion(df[col])
                    if converted.notna().sum() > 0:
                        df[col] = converted
                        agg_cols.append(col)
        
        if not agg_cols:
            return f"No numeric columns found for aggregation"
        
        return df.groupby(group_col)[agg_cols].agg(['sum', 'mean', 'count'])
    except Exception as e:
        return f"Aggregation error: {str(e)}"


def get_transformation_report(df):
    """Return the transformation report stored in the dataframe"""
    if hasattr(df, '_transformation_report'):
        return df._transformation_report
    return None


def pivot_data(df, index_col, columns_col, values_col):
    """
    Create a pivot table
    """
    return df.pivot_table(index=index_col, columns=columns_col, values=values_col, aggfunc='sum')


def get_transformation_report(df):
    """Return the transformation report stored in the dataframe"""
    if hasattr(df, '_transformation_report'):
        return df._transformation_report
    return None


def get_feature_importance_estimate(df):
    """
    Estimate feature importance based on variance and correlation
    """
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    importance = {}
    for col in numeric_cols:
        # Variance-based importance
        if df[col].std() > 0:
            importance[col] = df[col].std() / df[numeric_cols].std().max()
    
    return sorted(importance.items(), key=lambda x: x[1], reverse=True)
