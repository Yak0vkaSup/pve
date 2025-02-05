from ..utils.database import get_db_connection
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
