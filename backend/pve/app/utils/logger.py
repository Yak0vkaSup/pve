# app/utils/logger.py
from datetime import datetime, timezone
import logging
import os
import time
from ..socketio_setup import socketio
from .database import get_db_connection
from flask import request, current_app
from functools import wraps

def log_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_app.logger.info(
            f"Endpoint {request.path} called with method {request.method}"
        )
        return f(*args, **kwargs)
    return decorated_function

def delete_file_after_delay(file_path, delay):
    """Delete the file after a delay (5 minutes = 300 seconds)."""
    time.sleep(delay)
    if os.path.exists(file_path):
        os.remove(file_path)

def setup_logging(app, logfile='logs/app.log'):
    """
    Call once at application startup (e.g. in your Flask factory or run.py)
    to configure the root logger for file output and ensure INFO+ is enabled.
    """
    root = logging.getLogger()          # the ROOT logger
    root.setLevel(logging.INFO)         # capture INFO and up

    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    logging.getLogger("py.warnings").setLevel(logging.ERROR)

    fh = logging.FileHandler(logfile)
    fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    fh.setFormatter(logging.Formatter(fmt))
    fh.setLevel(logging.INFO)
    root.addHandler(fh)

    # Let Flask’s own logger bubble up to the root
    app.logger.propagate = True

class SocketIOLogHandler(logging.Handler):
    """Stream everything at INFO+ up to the given Socket.IO user room."""
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.setLevel(logging.INFO)
        fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        self.setFormatter(logging.Formatter(fmt))

    def emit(self, record):
        try:
            msg = self.format(record)
            socketio.emit('log_message', {'message': msg}, to=str(self.user_id))
        except Exception:
            self.handleError(record)


class DBLogHandler(logging.Handler):
    """
    A logging.Handler that pushes each record into bot_logs.
    """
    def __init__(self, bot_id):
        super().__init__()
        self.bot_id = bot_id
        # Optionally: hold one persistent conn/pool
        try:
            # Try Flask context first
            self.conn = get_db_connection()
        except RuntimeError:
            # If no Flask context, use bot utils version
            from ..pvebot.utils_bot import get_db_connection as bot_get_db_connection
            self.conn = bot_get_db_connection("postgresql")

    def emit(self, record):
        try:
            # format() will apply your Formatter, including timestamp
            msg = self.format(record)
            ts = datetime.fromtimestamp(record.created, tz=timezone.utc)
            cur = self.conn.cursor()
            cur.execute(
                """
                INSERT INTO bot_logs (bot_id, timestamp, level, message)
                VALUES (%s, %s, %s, %s)
                """,
                (self.bot_id, ts, record.levelname, msg)
            )
            # commit per record; for high-volume you could batch
            self.conn.commit()
            cur.close()
        except Exception:
            self.handleError(record)