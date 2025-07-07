# app/socketio_setup.py

from flask_socketio import SocketIO
from ..config import Config

socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode='eventlet',
    logger=False,
    engineio_logger=False,
    max_http_buffer_size= 20 * 1024 * 1024,
    ping_timeout=2500,
    ping_interval=2500,
    message_queue='redis://redis:6379/0'
)

def init_socketio(app):
    socketio.init_app(app)
    from .websocket import socket_handlers  # Import handlers after initializing socketio
