# app/socketio_setup.py

from flask_socketio import SocketIO
from config import Config

socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=False,
    engineio_logger=False
)

def init_socketio(app):
    socketio.init_app(app)
    from .websocket import socket_handlers  # Import handlers after initializing socketio
