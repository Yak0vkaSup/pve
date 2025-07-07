# utils_bot.py
import pandas as pd
import logging
from datetime import datetime, timedelta, timezone
import os
import psycopg2


logger = logging.getLogger(__name__)

def get_db_connection(host):
    try:
        DB_HOST = os.environ.get('DB_HOST', host)
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
    try:
        conn = get_db_connection('postgresql')
    except Exception as e:
        logging.error(f"Failed to connect to database: {e}")
        return pd.DataFrame()  # Return empty DataFrame on connection failure
        
    if conn is None:
        return pd.DataFrame()  # Return empty DataFrame instead of None
    
    try:
        # Set a query timeout to prevent hanging
        with conn.cursor() as cur:
            # Set statement timeout to 30 seconds
            cur.execute("SET statement_timeout = 30000")
            
        query = f"""
            SELECT timestamp AS date, open, high, low, close, volume
            FROM candles
            WHERE symbol = '{symbol}' AND
                  timestamp >= '{start_date}' AND
                  timestamp < '{end_date}'
            ORDER BY timestamp;
        """
        df = pd.read_sql(query, conn)
        conn.close()
        logging.info(f"Fetched data for {symbol} from {start_date} to {end_date}")
        df['date'] = pd.to_datetime(df['date'], utc=True)
        return df
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        try:
            conn.close()
        except:
            pass
        return pd.DataFrame()

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
