import time
from pybit.unified_trading import HTTP
from datetime import datetime, timedelta
import threading
from queue import Queue

# Configuration
CATEGORIES = ['linear']  # Categories to fetch
TOP_N = 10  # Number of top positive and negative rates to display
DAYS_BACK = 60  # Number of days to look back
MAX_THREADS = 10  # Number of concurrent threads to use

def get_all_symbols(session, category):
    """
    Fetches all symbols for a given category.

    Args:
        session (HTTP): The pybit HTTP session.
        category (str): The category to fetch symbols for.

    Returns:
        list: A list of symbol names.
    """
    try:
        response = session.get_tickers(category=category)
        if response['retCode'] != 0:
            print(f"Error fetching tickers for category '{category}': {response['retMsg']}")
            return []
        symbols = [item['symbol'] for item in response['result']['list'] if 'fundingRate' in item]
        return symbols
    except Exception as e:
        print(f"Exception while fetching tickers for category '{category}': {e}")
        return []

def fetch_funding_rates(session, category, symbol, start_time, end_time, queue):
    """
    Fetches funding rate history for a specific symbol and adds to the queue.

    Args:
        session (HTTP): The pybit HTTP session.
        category (str): The category of the symbol.
        symbol (str): The symbol name.
        start_time (int): Start timestamp in ms.
        end_time (int): End timestamp in ms.
        queue (Queue): Thread-safe queue to store results.
    """
    try:
        response = session.get_funding_rate_history(
            category=category,
            symbol=symbol,
            startTime=start_time,
            endTime=end_time,
            limit=200  # Maximum records per request
        )
        if response['retCode'] != 0:
            print(f"Error fetching funding rates for {symbol}: {response['retMsg']}")
            return
        rates = response['result']['list']
        for rate in rates:
            try:
                funding_rate = float(rate['fundingRate'])
                funding_timestamp = int(rate['fundingRateTimestamp'])
                queue.put((symbol, funding_rate, funding_timestamp))
            except ValueError:
                print(f"Invalid funding rate for symbol '{symbol}': {rate['fundingRate']}")
    except Exception as e:
        print(f"Exception while fetching funding rates for {symbol}: {e}")

def worker(session, category, symbols, start_time, end_time, queue):
    """
    Worker thread to process symbols.

    Args:
        session (HTTP): The pybit HTTP session.
        category (str): The category of symbols.
        symbols (list): List of symbol names.
        start_time (int): Start timestamp in ms.
        end_time (int): End timestamp in ms.
        queue (Queue): Thread-safe queue to store results.
    """
    for symbol in symbols:
        fetch_funding_rates(session, category, symbol, start_time, end_time, queue)
        # To respect rate limits, add a small delay
        time.sleep(0.1)

def main():
    # Initialize the HTTP session (default is live API)
    session = HTTP()  # Use `HTTP(testnet=True)` for testnet

    # Calculate time range for the last 3 days
    end_datetime = datetime.utcnow()
    start_datetime = end_datetime - timedelta(days=DAYS_BACK)
    end_time_ms = int(end_datetime.timestamp() * 1000)
    start_time_ms = int(start_datetime.timestamp() * 1000)

    print(f"Fetching funding rates from {start_datetime} to {end_datetime} UTC")

    all_funding_rates = []
    queue = Queue()

    for category in CATEGORIES:
        print(f"\nProcessing category: {category}")
        symbols = get_all_symbols(session, category)
        if not symbols:
            print(f"No symbols found for category '{category}'.")
            continue
        print(f"Found {len(symbols)} symbols in category '{category}'.")

        # Split symbols into chunks for threading
        chunk_size = max(1, len(symbols) // MAX_THREADS)
        symbol_chunks = [symbols[i:i + chunk_size] for i in range(0, len(symbols), chunk_size)]

        threads = []
        for chunk in symbol_chunks:
            thread = threading.Thread(target=worker, args=(session, category, chunk, start_time_ms, end_time_ms, queue))
            threads.append(thread)
            thread.start()

        # Wait for all threads to finish
        for thread in threads:
            thread.join()

    # Collect all funding rates from the queue
    while not queue.empty():
        symbol, rate, timestamp = queue.get()
        all_funding_rates.append((symbol, rate, timestamp))

    if not all_funding_rates:
        print("No funding rates retrieved.")
        return

    # Sort funding rates
    sorted_rates = sorted(all_funding_rates, key=lambda x: x[1], reverse=True)

    top_positive = sorted_rates[:TOP_N]
    top_negative = sorted_rates[-TOP_N:]

    # Display results
    print(f"\nTop {TOP_N} Positive Funding Rates over the Last {DAYS_BACK} Days:")
    for symbol, rate, timestamp in top_positive:
        funding_date = datetime.utcfromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{symbol}: {rate * 100:.4f}% on {funding_date} UTC")

    print(f"\nTop {TOP_N} Negative Funding Rates over the Last {DAYS_BACK} Days:")
    for symbol, rate, timestamp in reversed(top_negative):
        funding_date = datetime.utcfromtimestamp(timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
        print(f"{symbol}: {rate * 100:.4f}% on {funding_date} UTC")

if __name__ == "__main__":
    main()
