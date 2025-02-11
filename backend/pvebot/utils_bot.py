# utils_bot.py
import pandas as pd
import logging
from datetime import datetime, timedelta, timezone
from bybit_api import Bybit
import json
import os
import psycopg2
import pandas_ta as ta
from functools import wraps
from typing import Union

logger = logging.getLogger(__name__)

def get_db_connection():
    try:
        DB_HOST = os.environ.get('DB_HOST', '192.168.1.171')
        DB_NAME = os.environ.get('DB_NAME', 'postgres')
        DB_USER = os.environ.get('DB_USER', 'postgres')
        DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        # current_app.logger.info("Database connection established")
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

def get_data(days_ago, symbol, timeframe):
    start_date = pd.Timestamp.now(tz=timezone.utc) - timedelta(days=days_ago)
    end_date = pd.Timestamp.now(tz=timezone.utc) - timedelta(minutes=1)
    df = fetch_data(symbol, start_date, end_date)

    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)

    # And here we need to resample it based on timeframe
    df_resampled = df.resample(timeframe).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
    })

    df_resampled.reset_index(inplace=True)
    return df_resampled

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

def prepare_data(symbol, days, timeframe):
    """
    Fetch data for the past `days` days. This is just an example
    reusing your logic.
    """
    bybit_anon = Bybit(api_key="", api_secret="", testnet=False)  # or separate session
    start_date = pd.Timestamp.now(tz=timezone.utc) - timedelta(days=days)
    end_date = pd.Timestamp.now(tz=timezone.utc) - timedelta(minutes=1)
    df = get_candles(bybit_anon, symbol, timeframe, start_date, end_date)
    return df

def get_candles(bybit_instance, symbol, timeframe, start_date, end_date):
    logging.debug(f"Fetching candles for {symbol} from {start_date} to {end_date}")
    candles_data = []
    limit_bars = 1000
    while start_date < end_date:
        candles = bybit_instance.session.get_kline(symbol=symbol, interval=timeframe, start=int(start_date.timestamp() * 1000),
                                    limit=limit_bars)
        candles_list = candles['result']['list']
        start_date = pd.to_datetime(int(candles_list[0][0]), unit='ms', utc=True)
        candles_data += candles_list[::-1]  # .extend(candles_list.reverse())
        if len(candles_list) < limit_bars:
            break

    df = pd.DataFrame(candles_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)

    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['open'] = pd.to_numeric(df['open'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low'] = pd.to_numeric(df['low'], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

    df = df.drop_duplicates(subset='timestamp', keep='first')
    print(f"Candles fetched and processed successfully for symbol - {symbol}")
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

@type_check
def bollinger(close: pd.Series, window: int):
    return ta.bbands(close, window, talib=True)

def seconds_since_midnight():
    """Return the number of seconds since midnight."""
    now = datetime.now()
    return now.hour * 3600 + now.minute * 60 + now.second


timeframes = {
    "1min": 60,
    "3min": 180,
    "5min": 300,
    "15min": 900,
    "30min": 1800,
    "1h": 3600
}
symbols_db = ['1000000MOGUSDT', '1000BONKUSDT', '1000FLOKIUSDT', '1000NEIROCTOUSDT', '1000PEPEUSDT', '1000XUSDT', 'AAVEUSDT', 'ACTUSDT', 'ADAUSDT', 'APEUSDT', 'APTUSDT', 'ARBUSDT', 'ATOMUSDT', 'AVAXUSDT', 'BANUSDT', 'BCHUSDT', 'BNBUSDT', 'BOMEUSDT', 'BRETTUSDT', 'BTCPERP', 'BTCUSDT', 'CATIUSDT', 'CRVUSDT', 'DEGENUSDT', 'DOGEUSDT', 'DOGSUSDT', 'DOTUSDT', 'DRIFTUSDT', 'EIGENUSDT', 'ENAUSDT', 'ETCUSDT', 'ETHFIUSDT', 'ETHUSDT', 'FTMUSDT', 'GALAUSDT', 'GOATUSDT', 'GRASSUSDT', 'HBARUSDT', 'INJUSDT', 'JUPUSDT', 'KASUSDT', 'LDOUSDT', 'LINKUSDT', 'LTCUSDT', 'MEWUSDT', 'MOODENGUSDT', 'NEARUSDT', 'NEIROETHUSDT', 'NOTUSDT', 'OMUSDT', 'ONDOUSDT', 'OPUSDT', 'ORDIUSDT', 'PNUTUSDT', 'POLUSDT', 'POPCATUSDT', 'RENDERUSDT', 'SEIUSDT', 'SHIB1000USDT', 'SLERFUSDT', 'SOLUSDT', 'STRKUSDT', 'STXUSDT', 'SUIUSDT', 'TAOUSDT', 'TIAUSDT', 'TONUSDT', 'TROYUSDT', 'UNIUSDT', 'WIFUSDT', 'WLDUSDT', 'XLMUSDT', 'XRPUSDT']