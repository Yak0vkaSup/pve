# app/models/user_model.py
from ..utils.database import get_db_connection

class User:
    def __init__(self, user_id, first_name, last_name, username, usertoken):
        self.id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.usertoken = usertoken

    def to_dict(self):
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'username': self.username,
        }

    def update(self, data):
        conn = get_db_connection()
        cursor = conn.cursor()
        update_query = """
            UPDATE users
            SET first_name = %s, last_name = %s
            WHERE id = %s
        """
        cursor.execute(update_query, (
            data.get('first_name'),
            data.get('last_name'),
            self.id
        ))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def get_user_by_id(user_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT id, first_name, last_name, username, usertoken
            FROM users
            WHERE id = %s
        """
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result:
            return User(*result)
        else:
            return None
