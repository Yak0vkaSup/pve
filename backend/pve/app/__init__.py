# app/__init__.py

from flask import Flask
from flask_cors import CORS
from .routes import register_blueprints
from .utils.logger import setup_logging
from .socketio_setup import socketio
from config import Config

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app)
    setup_logging(app)
    register_blueprints(app)
    socketio.init_app(app)

    # Import socket handlers to register them
    from .websocket import socket_handlers

    return app
