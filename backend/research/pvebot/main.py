# main.py
import logging
import sys
from bot_manager import BotManager

def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("trading_bots.log")
        ]
    )

def main():
    setup_logging()
    manager = BotManager(storage_path="bot_states.json")

    # Load any previously saved bots
    manager.load_bots_from_storage()

    # Example: create or get an existing bot
    config = {
        'api_key': "",
        'api_secret': "",
        'symbol': 'SOLUSDT',
        'timeframe': 15,
        'profit_target': 1.0,
        'first_order_size_usdt': 10,
        'step_percentage': 0.5,
        'num_orders': 3,
        'martingale_factor': 1.25,
        'candles_to_close': 3000,
        'max_trade_duration': 3600,  # 1 hour
    }

    # Create a new bot or fetch existing
    bot_id = "SOL_DCA_BOT"
    bot = manager.create_bot(bot_id, config)

    # Start the bot
    manager.start_bot(bot_id)

    # ... you can start more bots if you want ...
    # manager.create_bot("ETH_DCA_BOT", config_for_eth)
    # manager.start_bot("ETH_DCA_BOT")

    # Keep the main thread alive, or do any other tasks
    try:
        while True:
            # In a real app, you might do more advanced scheduling here
            pass
    except KeyboardInterrupt:
        logging.info("Shutting down all bots...")
        manager.stop_all()

if __name__ == "__main__":
    main()
