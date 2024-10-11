import time
from pybit.unified_trading import HTTP
import pandas as pd
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from psycopg2 import pool
import psycopg2
from psycopg2.extras import execute_values
import logging
import os
import pytz

# logging.basicConfig(level=logging.BASIC_FORMAT, format='%(asctime)s - %(levelname)s - %(message)s')

DB_NAME = 'postgres'
DB_USER = 'postgres'
DB_PASSWORD = 'postgres'
DB_HOST = 'localhost'
DB_PORT = 5432

# Connection pool
db_pool = psycopg2.pool.SimpleConnectionPool(
    1, 50000,  # Min and max connections
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT
)
session = HTTP(testnet=False)


def connect_to_db():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    return conn


def fetch_data(symbol, start_date, end_date):
    conn = connect_to_db()
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


def update_all_symbols(symbols, num_days):
    with ThreadPoolExecutor(max_workers=len(symbols)) as executor:
        futures = [executor.submit(update_symbol, symbol, num_days) for symbol in symbols]
        for future in futures:
            try:
                future.result()
            except Exception as e:
                logging.error(f"Error in worker thread: {e}")


def insert_data(df, symbol):
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()

        records = df.to_dict('records')
        values = [(symbol, record['timestamp'], record['open'], record['high'], record['low'], record['close'],
                   record['volume']) for record in records]

        insert_query = """
        INSERT INTO candles (symbol, timestamp, open, high, low, close, volume) 
        VALUES %s 
        ON CONFLICT (symbol, timestamp) 
        DO UPDATE SET open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low, close = EXCLUDED.close, volume = EXCLUDED.volume;
        """
        execute_values(cur, insert_query, values)
        conn.commit()
        cur.close()
        db_pool.putconn(conn)
        logging.debug(f"Data for {symbol} inserted successfully")
    except Exception as e:
        logging.error(f"Error inserting data for {symbol}: {e}")


def get_candles(symbol, timeframe, start_date, end_date):
    logging.debug(f"Fetching candles for {symbol} from {start_date} to {end_date}")
    candles_data = []
    limit_bars = 1000
    while start_date < end_date:
        candles = session.get_kline(symbol=symbol, interval=timeframe, start=int(start_date.timestamp() * 1000),
                                    limit=limit_bars)
        # print("Loading")
        candles_list = candles['result']['list']
        start_date = pd.to_datetime(int(candles_list[0][0]), unit='ms', utc=True)
        candles_data += candles_list[::-1]  # .extend(candles_list.reverse())
        if len(candles_list) < limit_bars:
            break

    df = pd.DataFrame(candles_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'])
    df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms', utc=True)
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    df['open'] = pd.to_numeric(df['open'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low'] = pd.to_numeric(df['low'], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

    df = df.drop_duplicates(subset='timestamp', keep='first')
    print(f"Candles fetched and processed successfully for symbol - {symbol}")
    return df


def prepare_data(symbol, days):
    last_timestamp = get_last_timestamp(symbol)
    # if last_timestamp is None:
    #     start_date = pd.Timestamp.now(tz=timezone.utc) - timedelta(days=days)
    # else:
    start_date = pd.Timestamp.now(tz=timezone.utc) - timedelta(days=days)
    end_date = pd.Timestamp.now(tz=timezone.utc) - timedelta(minutes=1)
    logging.info(f"Loading new data for {symbol} from {start_date} to {end_date}")
    df = get_candles(symbol, 1, start_date, end_date)
    return df


def get_last_timestamp(symbol):
    try:
        conn = db_pool.getconn()
        cur = conn.cursor()
        cur.execute("SELECT MAX(timestamp) FROM candles WHERE symbol = %s;", (symbol,))
        last_timestamp = cur.fetchone()[0]
        cur.close()
        db_pool.putconn(conn)
        return last_timestamp
    except Exception as e:
        logging.error(f"Error fetching last timestamp for {symbol}: {e}")
        return None


def get_symbols_by_volume(volume):
    response = session.get_tickers(category="linear")
    if response['retCode'] != 0:
        logging.error("Failed to get tickers info")
        exit()
    filtered_symbols = [ticker['symbol'] for ticker in response['result']['list'] if
                        float(ticker['volume24h']) > volume]
    logging.info(
        f"Symbols with volume greater than {volume}$: {filtered_symbols}, Total number: {len(filtered_symbols)}")
    return filtered_symbols


def get_symbols_by_turnover(turnover):
    response = session.get_tickers(category="linear")
    if response['retCode'] != 0:
        logging.error("Failed to get tickers info")
        exit()
    filtered_symbols = [ticker['symbol'] for ticker in response['result']['list'] if
                        float(ticker['turnover24h']) > turnover]
    logging.info(
        f"Symbols with turnover greater than {turnover}$: {filtered_symbols}, Total number: {len(filtered_symbols)}")
    return filtered_symbols


def update_symbols_continuously(symbols):
    while True:
        logging.debug("Updating symbols continuously")
        with ThreadPoolExecutor(max_workers=len(symbols)) as executor:
            futures = [executor.submit(update_symbol_continuously, symbol) for symbol in symbols]
            for future in futures:
                try:
                    future.result()
                except Exception as e:
                    logging.error(f"Error in worker thread: {e}")
        time.sleep(1)  # Wait for 3 minutes before the next update


def update_symbol_continuously(symbol):
    try:
        df = prepare_data(symbol, 0.0021)  # Fetch data for the last 3 minutes
        if not df.empty:
            insert_data(df, symbol)
    except Exception as e:
        logging.error(f"Error updating data for {symbol}: {e}")


def update_symbol(symbol, num_days):
    try:
        df = prepare_data(symbol, num_days)  # Fetch data for the last 15 days initially
        if not df.empty:
            insert_data(df, symbol)
    except Exception as e:
        logging.error(f"Error updating data for {symbol}: {e}")


if __name__ == '__main__':
    volume = 50_000_000
    symbols = get_symbols_by_turnover(volume)  # in usdt
    # i = 0
    # for symbol in symbols:
    #     print(symbol, i)
    #     i += 1
    # update_symbol(symbols[21])
    print(symbols)
    num_days = 30 # last days
    update_all_symbols(symbols, num_days)
    update_symbols_continuously(symbols)
