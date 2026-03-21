import pandas as pd
import numpy as np

def transform_data(df):
    """
    Comprehensive data transformation pipeline including feature engineering
    """
    transformation_report = {
        'new_features': [],
        'steps': []
    }
    
    df = df.copy()
    original_cols = set(df.columns)
    
    # Step 1: Create aggregate features from numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    if len(numeric_cols) > 0:
        # Total sum feature
        df['total_numeric_sum'] = df[numeric_cols].sum(axis=1)
        transformation_report['new_features'].append('total_numeric_sum')
        
        # Mean of numeric columns
        df['avg_numeric'] = df[numeric_cols].mean(axis=1)
        transformation_report['new_features'].append('avg_numeric')
        
        # Standard deviation
        if len(numeric_cols) > 1:
            df['numeric_std'] = df[numeric_cols].std(axis=1)
            transformation_report['new_features'].append('numeric_std')
    
    transformation_report['steps'].append({
        'step': 'Create Aggregate Features',
        'features_created': 2 if len(numeric_cols) > 0 else 0
    })
    
    # Step 2: Create ratio features (if revenue and cost exist)
    if 'revenue' in df.columns and 'cost' in df.columns:
        df['profit_margin'] = ((df['revenue'] - df['cost']) / df['revenue'] * 100).round(2)
        transformation_report['new_features'].append('profit_margin')
        transformation_report['steps'].append({
            'step': 'Create Business Metrics',
            'metrics_created': ['profit_margin']
        })
    
    # Step 3: Create time-based features if date column exists
    date_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
    if len(date_cols) > 0:
        for col in date_cols:
            df[f'{col}_year'] = df[col].dt.year
            df[f'{col}_month'] = df[col].dt.month
            df[f'{col}_quarter'] = df[col].dt.quarter
            transformation_report['new_features'].extend([
                f'{col}_year', f'{col}_month', f'{col}_quarter'
            ])
        
        transformation_report['steps'].append({
            'step': 'Extract Time-Based Features',
            'date_columns_processed': len(date_cols)
        })
    
    # Step 4: Binning for numerical columns (create categories)
    for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
        if df[col].max() - df[col].min() > 0:
            df[f'{col}_binned'] = pd.cut(df[col], bins=5, labels=['Very_Low', 'Low', 'Medium', 'High', 'Very_High'])
            transformation_report['new_features'].append(f'{col}_binned')
    
    if any('_binned' in col for col in df.columns):
        transformation_report['steps'].append({
            'step': 'Bin Numeric Columns',
            'binned_columns': [col for col in df.columns if '_binned' in col]
        })
    
    # Step 5: Create interaction features (for top 2 numeric columns)
    if len(numeric_cols) >= 2:
        df[f'{numeric_cols[0]}_x_{numeric_cols[1]}'] = df[numeric_cols[0]] * df[numeric_cols[1]]
        transformation_report['new_features'].append(f'{numeric_cols[0]}_x_{numeric_cols[1]}')
        
        transformation_report['steps'].append({
            'step': 'Create Interaction Features',
            'interactions_created': 1
        })
    
    transformation_report['total_features_created'] = len(df.columns) - len(original_cols)
    transformation_report['original_columns'] = len(original_cols)
    transformation_report['final_columns'] = len(df.columns)
    
    df._transformation_report = transformation_report
    return df


def aggregate_by_column(df, group_col, agg_cols=None):
    """
    Aggregate data by a specific column
    """
    if agg_cols is None:
        agg_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    return df.groupby(group_col)[agg_cols].agg(['sum', 'mean', 'count'])


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
