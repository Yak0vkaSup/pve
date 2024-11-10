# app/nodes/utils.py
import pandas as pd
import pandas_ta as ta
from ..utils.database import get_db_connection
import logging
from functools import wraps
import pandas as pd
from typing import Union


def calculate_ma(df, length, ma_type, calculate_on):
    ma_function = getattr(ta, ma_type)
    return ma_function(df[calculate_on], length, talib=True)

def fetch_data(symbol, start_date, end_date):
    conn = get_db_connection()
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
    logging.info(f"Fetched data for {symbol} from {start_date} to {end_date}")
    df['date'] = pd.to_datetime(df['date'], utc=True)
    return df

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
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' does not exist in the DataFrame.")
    df.drop(columns=[column_name], inplace=True)
    return df

@type_check
def multiply_column(column: pd.Series, factor: Union[int, float]) -> pd.Series:
    return column * factor

@type_check
def ma(name: str, column: pd.Series, window: int) -> pd.Series:
    return ta.ma(name, column, length=window)


@type_check
def super_trend(high: pd.Series, low: pd.Series, close: pd.Series,  window: int) -> pd.Series:
    return ta.supertrend(high, low, close, window)
