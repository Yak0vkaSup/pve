# main.py
import logging
import sys
from bot_manager import BotManager
import json
from nodes_bot import process_graph

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

    with open("boll.json", "r") as f:
        data = json.load(f)

    # datasource 0 is api bybit
    # 1 is DB local
    config = {
        'data_source': 1,
        'api_key': "CQ16qbTLFEbJqLtS4W",
        'api_secret': "E0p4bPZpsgew4STE8kttc6LGhfoXuaRLxgdA",
        'symbol': data['symbol'],
        'timeframe': data['timeframe'],
        'nodes': data,
    }

    # Create a new bot or fetch existing
    bot_id = 228

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
