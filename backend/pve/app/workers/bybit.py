import logging
from decimal import Decimal
import json
import time
from pybit.unified_trading import HTTP

logger = logging.getLogger(__name__)

def fetch_and_save_bybit_instruments_info(json_filepath="bybit_instruments_info.json"):
    """
    Calls Bybit’s API to get the instruments info and saves the JSON
    response to a local file.
    """
    session = HTTP(testnet=False)
    try:
        # You can remove the symbol parameter here if you wish to get info for all symbols.
        response = session.get_instruments_info(category="linear")
        with open(json_filepath, "w") as f:
            json.dump(response, f, indent=4)
        logger.info(f"Successfully fetched and saved instruments info to '{json_filepath}'.")
    except Exception as e:
        logger.error(f"Error fetching instruments info from Bybit: {e}")


def main_loop():
    symbol = "BTCUSDT"  # Change to your symbol of interest.
    while True:
        try:
            logger.info("========== Starting new iteration ==========")
             # --- Update local JSON file with latest instruments info ---
            fetch_and_save_bybit_instruments_info()

            # --- Use local JSON file to extract the same data ---
            #precision_local, min_move_local = get_precision_and_min_move_local(symbol)
            #logger.debug(
            #    f"Local JSON - Fetched precision: {precision_local}, min_move: {min_move_local} for symbol: {symbol}")

            # --- Wait for 12 hours before next iteration ---
            logger.info("Sleeping for 12 hours...")
            time.sleep(12 * 60 * 60)
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            # Wait a minute before restarting the loop if an unexpected error occurs.
            time.sleep(10)


if __name__ == "__main__":
    main_loop()