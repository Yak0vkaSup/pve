# app/utils/database.py
import psycopg2
from flask import current_app

def get_db_connection():
    try:

        conn = psycopg2.connect(
            host=current_app.config['DB_HOST'],
            database=current_app.config['DB_NAME'],
            user=current_app.config['DB_USER'],
            password=current_app.config['DB_PASSWORD']
        )
        # current_app.logger.info("Database connection established")
        return conn
    except Exception as e:
        current_app.logger.error(f"Database connection error: {e}")
        return None
