import os
import asyncio
import logging
import time
import threading
import traceback
from datetime import datetime, timedelta, timezone
import decimal
from decimal import Decimal
import pandas as pd
import asyncpg
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pybit.unified_trading import MarketHTTP, WebSocket

# =============================================================================
# Configuration and Logging
# =============================================================================

# Database credentials (adjust as needed)
DB_NAME = os.getenv('DB_NAME', 'postgres')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'postgresql')
DB_PORT = int(os.getenv('DB_PORT', 5432))
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/data_manager.log'),
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# Global Constants and Initialization
# =============================================================================

# REST API session (production; set testnet=True if needed)
session = MarketHTTP(testnet=False)

# Global async DB pool (will be initialized later)
db_pool = None

# Constants for historical data updates
TIMEFRAME = '1'  # 1-minute interval (valid values: 1, 3, 5, 15, etc.)
CHUNK_SIZE = 1000  # Number of records per REST call
MAX_CONCURRENT_TASKS = 100  # Limit concurrent REST tasks
RETRY_ATTEMPTS = 5  # Retry attempts for API calls
RATE_LIMIT = 600  # Example: 600 requests per 5 seconds

# If the database is empty for a symbol, this default period will be used.
DEFAULT_HISTORY_HOURS = 72

# =============================================================================
# Async Rate Limiter (for REST API calls)
# =============================================================================

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

rate_limiter = AsyncRateLimiter(max_calls=RATE_LIMIT, period=5)  # 600 requests per 5 seconds

# =============================================================================
# Database Functions
# =============================================================================

async def init_db_pool():
    global db_pool
    while True:
        try:
            db_pool = await asyncpg.create_pool(
                user=DB_USER,
                password=DB_PASSWORD,
                database=DB_NAME,
                host=DB_HOST,
                port=DB_PORT,
                min_size=1,
                max_size=50,
            )
            logger.info("Database pool created.")
            break  # Exit the loop once the pool is successfully created.
        except Exception as e:
            logger.error("Database connection failed: %s", e)
            logger.info("Waiting 5 seconds before retrying...")
            await asyncio.sleep(5)


async def close_db_pool():
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed.")

async def get_last_timestamp(symbol):
    """Retrieve the last stored timestamp for a symbol from the database."""
    async with db_pool.acquire() as conn:
        result = await conn.fetchval(
            """
            SELECT MAX(timestamp)
            FROM candles
            WHERE symbol = $1
            """,
            symbol
        )
        return result

async def insert_data(df, symbol):
    """Insert a DataFrame of candle data into the database."""
    if df.empty:
        logger.info(f"No new data to insert for {symbol}")
        return

    expected_columns = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
    if not expected_columns.issubset(df.columns):
        logger.error(f"Data integrity error for {symbol}: Missing columns")
        return

    # Ensure correct types and convert timestamp to naive UTC datetime
    df = df.astype({
        'open': 'float',
        'high': 'float',
        'low': 'float',
        'close': 'float',
        'volume': 'float',
    })
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
            logger.info(f"Inserted/Updated {len(values)} records for {symbol}")

async def insert_single_candle(symbol, ts, open_price, high_price, low_price, close_price, volume):
    """Insert or update a single candle record into the database."""
    async with db_pool.acquire() as conn:
        async with conn.transaction():
            query = """
            INSERT INTO candles (symbol, timestamp, open, high, low, close, volume)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (symbol, timestamp) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
            """
            await conn.execute(query, symbol, ts, open_price, high_price, low_price, close_price, volume)
            logger.info(f"Upserted candle for {symbol} at {ts}")

# =============================================================================
# REST API Functions for Historical Data
# =============================================================================

@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception)
)
async def fetch_candles(symbol, start_time, end_time):
    """
    Fetch historical candle data from the Bybit API for a given symbol
    between start_time and end_time.
    """
    all_candles = []
    while start_time < end_time:
        await rate_limiter.acquire()
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

        if response['retCode'] != 0:
            logger.error(f"API error for {symbol}: {response.get('retMsg', 'Unknown error')}")
            raise Exception(f"API error: {response.get('retMsg', 'Unknown error')}")

        candles_list = response['result']['list']
        if not candles_list:
            break
        #logger.info(f"{candles_list}")
        df = pd.DataFrame(candles_list, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
        ])
        df['timestamp'] = pd.to_datetime(pd.to_numeric(df['timestamp']), unit='ms', utc=True)
        ""
        df['open'] = df['open'].astype(str).apply(lambda x: Decimal(x))
        df['high'] = df['high'].astype(str).apply(lambda x: Decimal(x))
        df['low'] = df['low'].astype(str).apply(lambda x: Decimal(x))
        df['close'] = df['close'].astype(str).apply(lambda x: Decimal(x))
        df['volume'] = df['volume'].astype(str).apply(lambda x: Decimal(x))

        df = df.drop_duplicates(subset='timestamp', keep='first')
        df = df.sort_values('timestamp')
        all_candles.append(df)

        # Advance the start time to the next minute after the last received candle.
        last_timestamp = df['timestamp'].iloc[-1]
        start_time = last_timestamp.to_pydatetime() + timedelta(minutes=1)

        if len(candles_list) < CHUNK_SIZE:
            break

    if all_candles:
        return pd.concat(all_candles, ignore_index=True)
    else:
        return pd.DataFrame()

async def update_symbol(symbol):
    """
    Update historical candle data for a symbol by checking the last stored timestamp
    and fetching any missing data until now.
    """
    try:
        last_timestamp = await get_last_timestamp(symbol)
        if last_timestamp is None:
            # No records in DB: fetch a default period (e.g., the last 1 hour)
            start_time = pd.Timestamp.now(tz=timezone.utc) - timedelta(hours=DEFAULT_HISTORY_HOURS)
            logger.info(f"No existing data for {symbol}. Fetching candles from {start_time} to now.")
        else:
            # If data exists, fetch from (last timestamp + 1 minute) to now.
            start_time = pd.Timestamp(last_timestamp, tz=timezone.utc) + timedelta(minutes=1)
            logger.info(f"Existing data for {symbol} until {last_timestamp}. Filling gap from {start_time} to now.")
        end_time = pd.Timestamp.now(tz=timezone.utc)

        if start_time >= end_time:
            logger.info(f"No new data to fetch for {symbol}")
            return

        df = await fetch_candles(symbol, start_time, end_time)
        await insert_data(df, symbol)
        logger.info(f"Updated {symbol} from {start_time} to {end_time}.")
    except Exception as e:
        logger.error(f"Error updating {symbol}: {e}\n{traceback.format_exc()}")

async def update_all_symbols(symbols):
    """Update historical data concurrently for all symbols."""
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
    tasks = []
    for symbol in symbols:
        tasks.append(update_symbol_with_semaphore(symbol, semaphore))
    await asyncio.gather(*tasks)

async def update_symbol_with_semaphore(symbol, semaphore):
    async with semaphore:
        await update_symbol(symbol)

async def get_symbols_by_turnover(turnover_threshold):
    """
    Retrieve symbols (for the linear market) with 24h turnover greater than the specified threshold.
    """
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

# =============================================================================
# WebSocket Functions for Realtime Updates
# =============================================================================

async def process_ws_messages(queue: asyncio.Queue):
    """
    Process messages received via the WebSocket.
    Only process candles when 'confirm' is True (i.e. candle closed).
    """
    while True:
        message = await queue.get()
        try:
            if not message or 'data' not in message:
                queue.task_done()
                continue

            data_list = message.get('data', [])
            # Extract symbol from topic string, e.g., "kline.1.BTCUSDT"
            topic = message.get('topic', '')
            if not topic:
                queue.task_done()
                continue
            symbol = topic.split('.')[-1]

            for candle in data_list:
                if candle.get("confirm", False) is True:
                    # Use the candle "start" time as the timestamp (in ms)
                    ts = pd.to_datetime(candle["start"], unit="ms", utc=True)
                    ts = ts.to_pydatetime().astimezone(timezone.utc).replace(tzinfo=None)
                    try:
                        open_price = Decimal(candle["open"])
                        high_price = Decimal(candle["high"])
                        low_price = Decimal(candle["low"])
                        close_price = Decimal(candle["close"])
                        volume = Decimal(candle["volume"])
                        logger.info(f"{open_price, high_price, low_price, close_price}")
                    except Exception as e:
                        logger.error(f"Error parsing candle data for {symbol}: {e}")
                        continue
                    await insert_single_candle(symbol, ts, open_price, high_price, low_price, close_price, volume)
        except Exception as e:
            logger.error(f"Error processing WS message: {e}\n{traceback.format_exc()}")
        finally:
            queue.task_done()

def run_websocket_subscription(symbols, interval, callback):
    """
    Run a WebSocket subscription that subscribes to kline updates for all symbols.
    The provided callback is called on each message.
    """
    ws = WebSocket(testnet=False, channel_type="linear")
    logger.info("Starting WebSocket subscription...")
    for symbol in symbols:
        logger.info(f"Subscribing to {symbol} kline stream (interval: {interval})")
        ws.kline_stream(
            interval=interval,
            symbol=symbol,
            callback=callback
        )
    # Keep the thread alive
    while True:
        time.sleep(1)

# =============================================================================
# Main Routine
# =============================================================================

async def main():
    await init_db_pool()
    try:
        # Retrieve symbols with turnover above a threshold (adjust as needed)
        turnover_threshold = 50_000_000
        symbols = await get_symbols_by_turnover(turnover_threshold)
        if not symbols:
            logger.error("No symbols to update. Exiting.")
            return

        # Fill any historical gaps by checking the DB for each symbol
        logger.info("Filling historical gaps for symbols...")
        await update_all_symbols(symbols)
        logger.info("Historical update completed.")

        # Set up an asyncio queue for WebSocket messages
        ws_message_queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        # Define the WebSocket callback.
        def ws_handle_message(message):
            # This callback is invoked in the WS thread.
            asyncio.run_coroutine_threadsafe(ws_message_queue.put(message), loop)

        # Start the WebSocket subscription in a separate daemon thread.
        ws_thread = threading.Thread(
            target=run_websocket_subscription,
            args=(symbols, TIMEFRAME, ws_handle_message),
            daemon=True
        )
        ws_thread.start()

        logger.info("Started WebSocket thread. Now processing realtime updates...")
        # Process incoming WebSocket messages indefinitely.
        await process_ws_messages(ws_message_queue)

    finally:
        await close_db_pool()

if __name__ == '__main__':
    try:
        time.sleep(10)
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Process interrupted by user. Exiting.")
