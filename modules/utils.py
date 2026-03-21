def normalize_columns(df):
    df.columns = [col.strip().lower() for col in df.columns]
    return df