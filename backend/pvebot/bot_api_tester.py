import json
import redis
import time

from utils_bot import get_db_connection
import json

class Bot:
    @staticmethod
    def create(user_id, name, parameters):
        """
        Creates a bot entry in the database but does NOT start it yet.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        insert_query = """
            INSERT INTO bots (user_id, name, parameters, status)
            VALUES (%s, %s, %s, 'created') RETURNING id;
        """
        cursor.execute(insert_query, (user_id, name, json.dumps(parameters)))
        bot_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return bot_id

    @staticmethod
    def get_all_by_user(user_id):
        """
        Fetch all bots for a specific user.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT id, name, status FROM bots WHERE user_id = %s"
        cursor.execute(query, (user_id,))
        bots = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{'id': bot[0], 'name': bot[1], 'status': bot[2]} for bot in bots]

    @staticmethod
    def update_status(bot_id, status):
        """
        Updates the bot status in the database.
        """
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "UPDATE bots SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
        cursor.execute(query, (status, bot_id))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def stop(bot_id):
        """
        Stops a bot and updates the status in the database.
        """
        Bot.update_status(bot_id, 'stopped')


# Initialize Redis connection
redis_client = redis.Redis(host='localhost', port=6379, db=0)

# Load example bot configuration
with open("boll.json", "r") as f:
    data = json.load(f)

# Example user ID
USER_ID = 674380096

# Bot configuration
config = {
    "data_source": 1,
    "api_key": "CQ16qbTLFEbJqLtS4W",
    "api_secret": "E0p4bPZpsgew4STE8kttc6LGhfoXuaRLxgdA",
    "symbol": data["symbol"],
    "timeframe": data["timeframe"],
    "nodes": data,
}


def create_bot():
    """
    Directly creates a bot in MySQL using Bot.create().
    """
    bot_id = Bot.create(USER_ID, "TestBot3", config)
    print(f"✅ Bot Created Successfully! Bot ID: {bot_id}")
    return bot_id


def launch_bot(bot_id):
    """
    Directly starts the bot using Redis (not Flask).
    """
    Bot.update_status(bot_id, "to_be_launched")
    redis_client.publish('bot-launch-channel', str(bot_id))
    print(f"🚀 Bot {bot_id} Launch Request Sent via Redis!")

def stop_bot(bot_id):
    """
    Directly starts the bot using Redis (not Flask).
    """
    Bot.update_status(bot_id, "to_be_stopped")
    redis_client.publish('bot-stop-channel', str(bot_id))
    print(f" Bot {bot_id} Stop Request Sent via Redis!")

def main():
    """
    Simulates creating and launching a bot.
    """
    print("🔄 Creating a bot...")
    bot_id = create_bot()

    if bot_id:
        time.sleep(2)  # Give some time before launching
        print(f"🔄 Launching bot {bot_id}...")
        launch_bot(bot_id)
        time.sleep(100)
        stop_bot(bot_id)

if __name__ == "__main__":
    main()
