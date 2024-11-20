# app/utils/database.py
import psycopg2
from flask import current_app
import pandas as pd
from typing import Union
import pandas as pd
from typing import Any
from functools import wraps


def connect_to_db():
    conn = psycopg2.connect(
        host='192.168.1.153',
        database='postgres',
        user='postgres',
        password='postgres',
        port='5432'
    )
    return conn if conn else print(conn)

def fetch_data(symbol, start_date, end_date):
    conn = connect_to_db()
    if conn is None:
        return None
    query = f"""
        SELECT timestamp AS date, open, high, low, close, volume
        FROM candles
        WHERE symbol = '{symbol}' AND
              timestamp BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY timestamp;
    """
    df = pd.read_sql(query, conn)
    conn.close()
    df['date'] = pd.to_datetime(df['date'], utc=True)
    return df

df = fetch_data('1000FLOKIUSDT', '2024-10-01','2025-10-30' )

def type_check(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        annotations = func.__annotations__
        for name, value in zip(annotations, args):
            expected_type = annotations.get(name)
            if expected_type and not isinstance(value, expected_type):
                raise TypeError(f"Argument '{name}' must be {expected_type}, got {type(value)}")
        return func(*args, **kwargs)
    return wrapper

@type_check
def get_open(df: pd.DataFrame) -> pd.Series:
    return df['open']

@type_check
def get_close(df: pd.DataFrame) -> pd.Series:
    return df['close']

@type_check
def get_high(df: pd.DataFrame) -> pd.Series:
    return df['high']

@type_check
def get_low(df: pd.DataFrame) -> pd.Series:
    return df['low']

@type_check
def get_volume(df: pd.DataFrame) -> pd.Series:
    return df['volume']

@type_check
def add_column(df: pd.DataFrame, column_name: str, column: pd.Series) -> pd.DataFrame:
    if column_name in df.columns:
        raise ValueError(f"Column '{column_name}' already exists in the DataFrame.")

    df[column_name] = column
    return df

@type_check
def delete_column(df: pd.DataFrame, column_name: str) -> pd.DataFrame:
    df.drop(columns=[column_name], inplace=True)
    return df

@type_check
def multiply_column(column: pd.Series, factor: Union[int, float]) -> pd.Series:
    column = column * factor
    return column

pve = get_open(df)
pve = multiply_column(pve, 10)
df = add_column(df, 'gavno', pve)
print(df.head(10))

pve = multiply_column(df['open'], 'str')