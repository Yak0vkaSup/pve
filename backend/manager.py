import os
import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
import pandas as pd
from pybit.unified_trading import MarketHTTP
import asyncpg
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import traceback

# Load environment variables for database credentials
DB_NAME = os.getenv('DB_NAME', 'postgres')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_HOST = os.getenv('DB_HOST', '192.168.1.171')
DB_PORT = int(os.getenv('DB_PORT', 5432))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('data_updater.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize the pybit MarketHTTP session
session = MarketHTTP(testnet=False)

# Asynchronous database connection pool
db_pool = None

# Constants
TIMEFRAME = '1'  # 1-minute interval
CHUNK_SIZE = 1000  # Number of records per API call
MAX_CONCURRENT_TASKS = 100  # Limit the number of concurrent tasks
RETRY_ATTEMPTS = 5  # Number of retry attempts for API calls
RATE_LIMIT = 600  # Max requests per second

# Global rate limiter instance
request_counter = 0
request_counter_lock = asyncio.Lock()

class AsyncRateLimiter:
    def __init__(self, max_calls, period):
        self._max_calls = max_calls
        self._period = period
        self._tokens = max_calls
        self._lock = asyncio.Lock()
        self._last_time = time.monotonic()

    async def acquire(self):
        async with self._lock:
            current_time = time.monotonic()
            elapsed = current_time - self._last_time
            self._last_time = current_time
            self._tokens += elapsed * (self._max_calls / self._period)
            if self._tokens > self._max_calls:
                self._tokens = self._max_calls
            if self._tokens < 1:
                await asyncio.sleep((1 - self._tokens) * (self._period / self._max_calls))
                self._tokens = 0
            else:
                self._tokens -= 1

rate_limiter = AsyncRateLimiter(max_calls=RATE_LIMIT, period=5)  # 600 requests per second

async def init_db_pool():
    global db_pool
    db_pool = await asyncpg.create_pool(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST,
        port=DB_PORT,
        min_size=1,
        max_size=50,
    )

async def close_db_pool():
    await db_pool.close()

@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception)
)
async def fetch_candles(symbol, start_time, end_time):
    global request_counter
    """Fetch candle data from Bybit API."""
    logger.debug(f"Fetching candles for {symbol} from {start_time} to {end_time}")
    all_candles = []
    while start_time < end_time:
        await rate_limiter.acquire()  # Wait if rate limit exceeded

        try:
            response = session.get_kline(
                category='linear',
                symbol=symbol,
                interval=TIMEFRAME,
                start=int(start_time.timestamp() * 1000),
                limit=CHUNK_SIZE
            )
        except Exception as e:
            logger.error(f"Exception during API call for {symbol}: {e}")
            raise

        async with request_counter_lock:
            request_counter += 1

        if response['retCode'] != 0:
            logger.error(f"API error for {symbol}: {response.get('retMsg', 'Unknown error')}")
            raise Exception(f"API error: {response.get('retMsg', 'Unknown error')}")

        candles_list = response['result']['list']
        if not candles_list:
            break

        df = pd.DataFrame(candles_list, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ])

        # Convert 'timestamp' to timezone-aware datetime objects in UTC
        df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms', utc=True)
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['open'] = pd.to_numeric(df['open'], errors='coerce')
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['low'] = pd.to_numeric(df['low'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        df = df.drop_duplicates(subset='timestamp', keep='first')

        df = df.sort_values('timestamp')
        all_candles.append(df)

        last_timestamp = df['timestamp'].iloc[-1]
        start_time = last_timestamp.to_pydatetime() + timedelta(minutes=1)

        if len(candles_list) < CHUNK_SIZE:
            break

    if all_candles:
        return pd.concat(all_candles, ignore_index=True)
    else:
        return pd.DataFrame()

async def get_last_timestamp(symbol):
    """Retrieve the last timestamp for a symbol from the database."""
    async with db_pool.acquire() as conn:
        result = await conn.fetchval(
            """
            SELECT MAX(timestamp)
            FROM candles
            WHERE symbol = $1
            """,
            symbol
        )
        return result  # Should be timezone-aware due to TIMESTAMPTZ

async def insert_data(df, symbol):
    """Insert candle data into the database."""
    if df.empty:
        logger.info(f"No new data to insert for {symbol}")
        return

    # Data integrity verification
    expected_columns = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
    if not expected_columns.issubset(df.columns):
        logger.error(f"Data integrity error for {symbol}: Missing columns")
        return

    # Convert data types
    df = df.astype({
        'open': 'float',
        'high': 'float',
        'low': 'float',
        'close': 'float',
        'volume': 'float',
    })

    # Convert 'timestamp' to naive datetime objects in UTC
    df['timestamp'] = df['timestamp'].apply(lambda x: x.to_pydatetime().astimezone(timezone.utc).replace(tzinfo=None))

    records = df.to_dict('records')

    async with db_pool.acquire() as conn:
        async with conn.transaction():
            insert_query = """
            INSERT INTO candles (symbol, timestamp, open, high, low, close, volume)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (symbol, timestamp) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
            """
            values = [
                (
                    symbol,
                    record['timestamp'],
                    record['open'],
                    record['high'],
                    record['low'],
                    record['close'],
                    record['volume']
                )
                for record in records
            ]
            await conn.executemany(insert_query, values)
            logger.info(f"Inserted {len(values)} records for {symbol}")


async def update_symbol(symbol, days):
    """Update candle data for a single symbol."""
    try:
        last_timestamp = await get_last_timestamp(symbol)

        if last_timestamp is None:
            start_time = pd.Timestamp.now(tz=timezone.utc) - timedelta(days=days)
        else:
            start_time = pd.Timestamp(last_timestamp, tz=timezone.utc) - timedelta(minutes=3)
        end_time = pd.Timestamp.now(tz=timezone.utc)
        # print(type(last_timestamp), type(start_time), type(end_time))
        # print(last_timestamp, start_time, end_time)
        # exit()
        if start_time >= end_time:
            logger.info(f"No new data to fetch for {symbol}")
            return

        df = await fetch_candles(symbol, start_time, end_time)
        await insert_data(df, symbol)
        logger.info(f"{symbol} updated")
    except Exception as e:
        logger.error(f"Error updating {symbol}: {e}\n{traceback.format_exc()}")



async def get_symbols_by_turnover(turnover_threshold):
    """Retrieve symbols with turnover greater than the specified threshold."""
    response = session.get_tickers(category='linear')
    if response['retCode'] != 0:
        logger.error(f"Failed to get tickers info: {response.get('retMsg', 'Unknown error')}")
        return []

    symbols = [
        ticker['symbol']
        for ticker in response['result']['list']
        if float(ticker.get('turnover24h', 0)) > turnover_threshold
    ]

    logger.info(f"Symbols with turnover > {turnover_threshold}: {symbols}")
    return symbols

async def update_all_symbols(symbols, days):
    """Update all symbols concurrently."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    tasks = []
    for symbol in symbols:
        tasks.append(update_symbol_with_semaphore(symbol, days, semaphore))

    await asyncio.gather(*tasks)

async def update_symbol_with_semaphore(symbol, days, semaphore):
    """Update symbol with concurrency control."""
    async with semaphore:
        await update_symbol(symbol, days)

async def continuous_update(symbols):
    """Continuously update symbols at specified intervals."""
    while True:
        logger.info("Starting continuous update...")
        await update_all_symbols(symbols, days=0)
        logger.info("Continuous update cycle completed. Waiting for the next cycle.")
        await asyncio.sleep(1)  # Wait for 3 minutes

async def monitor_requests():
    global request_counter
    while True:
        await asyncio.sleep(1)
        async with request_counter_lock:
            logger.info(f"Requests in the last second: {request_counter}")
            request_counter = 0  # Reset the counter

async def main():
    await init_db_pool()
    try:
        turnover_threshold = 50_000_000  # Adjust as needed
        symbols = await get_symbols_by_turnover(turnover_threshold)
        if not symbols:
            logger.error("No symbols to update. Exiting.")
            return

        initial_days = 3
        logger.info("Starting initial data update...")
        await update_all_symbols(symbols, days=initial_days)
        logger.info("Initial data update completed.")

        # Start monitoring task
        monitoring_task = asyncio.create_task(monitor_requests())

        # Start continuous updates
        await continuous_update(symbols)

    finally:
        await close_db_pool()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user. Exiting.")
