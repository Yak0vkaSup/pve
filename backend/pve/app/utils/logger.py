# app/utils/logger.py
import logging
import os
import time
from ..socketio_setup import socketio
from flask import request, current_app
from functools import wraps

def setup_logging(app):
    handler = logging.FileHandler('logs/app.log')  # Log to 'app.log' file
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    # app.logger.setLevel(logging.INFO)

def log_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_app.logger.info(f"Endpoint {request.path} called with method {request.method}")
        return f(*args, **kwargs)
    return decorated_function

def delete_file_after_delay(file_path, delay):
    """Delete the file after a delay (5 minutes = 300 seconds)."""
    time.sleep(delay)
    if os.path.exists(file_path):
        os.remove(file_path)

class SocketIOLogHandler(logging.Handler):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id

    def emit(self, record):
        try:
            msg = self.format(record)
            # Emit log message via SocketIO
            socketio.emit('log_message', {'message': msg}, to=self.user_id)
        except Exception:
            self.handleError(record)