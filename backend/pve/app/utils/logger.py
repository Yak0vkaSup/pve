# app/utils/logger.py
import logging
from flask import request, current_app
from functools import wraps

def setup_logging(app):
    handler = logging.FileHandler('app.log')  # Log to 'app.log' file
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

def log_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        current_app.logger.info(f"Endpoint {request.path} called with method {request.method}")
        return f(*args, **kwargs)
    return decorated_function
