def add_profit_column(df):
    if 'revenue' in df.columns and 'cost' in df.columns:
        df['profit'] = df['revenue'] - df['cost']
    return df


def summary_stats(df):
    return df.describe().to_dict()