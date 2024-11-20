from pybit.unified_trading import HTTP
import sys

def fetch_tickers(session, category):
    """
    Fetches tickers for a given category.

    Args:
        session (HTTP): The pybit HTTP session.
        category (str): The category to fetch tickers for.

    Returns:
        list: A list of ticker dictionaries.
    """
    try:
        response = session.get_tickers(category=category)
        if response['retCode'] != 0:
            print(f"Error fetching tickers for category '{category}': {response['retMsg']}")
            return []
        return response['result']['list']
    except Exception as e:
        print(f"Exception while fetching tickers for category '{category}': {e}")
        return []

def extract_funding_rates(tickers):
    """
    Extracts funding rates from tickers.

    Args:
        tickers (list): A list of ticker dictionaries.

    Returns:
        list: A list of tuples containing symbol and funding rate.
    """
    funding_rates = []
    for ticker in tickers:
        symbol = ticker.get('symbol')
        funding_rate_str = ticker.get('fundingRate')

        if funding_rate_str is None:
            continue  # Skip if funding rate is not available

        try:
            funding_rate = float(funding_rate_str)
            funding_rates.append((symbol, funding_rate))
        except ValueError:
            print(f"Invalid funding rate for symbol '{symbol}': {funding_rate_str}")
            continue

    return funding_rates

def display_top_rates(funding_rates, top_n=5):
    """
    Displays the top positive and negative funding rates.

    Args:
        funding_rates (list): A list of tuples containing symbol and funding rate.
        top_n (int): Number of top rates to display.
    """
    if not funding_rates:
        print("No funding rates available to display.")
        return

    # Sort by funding rate ascending for negative and descending for positive
    sorted_rates = sorted(funding_rates, key=lambda x: x[1], reverse=True)

    top_positive = sorted_rates[:top_n]
    top_negative = sorted_rates[-top_n:]

    print(f"\nTop {top_n} Positive Funding Rates:")
    for symbol, rate in top_positive:
        print(f"{symbol}: {rate * 100:.4f}%")

    print(f"\nTop {top_n} Negative Funding Rates:")
    for symbol, rate in reversed(top_negative):
        print(f"{symbol}: {rate * 100:.4f}%")

def main():
    # Initialize the HTTP session (default is live API)
    session = HTTP()  # Use `HTTP(testnet=True)` for testnet

    # Categories relevant for funding rates
    categories = ['linear', 'inverse']

    all_funding_rates = []

    for category in categories:
        print(f"Fetching tickers for category: {category}")
        tickers = fetch_tickers(session, category)
        funding_rates = extract_funding_rates(tickers)
        all_funding_rates.extend(funding_rates)

    display_top_rates(all_funding_rates, top_n=5)

if __name__ == "__main__":
    main()
