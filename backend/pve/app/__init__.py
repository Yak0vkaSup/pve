# app/__init__.py
from flask import Flask
from flask_cors import CORS
from celery import Celery
import redis
from .routes import register_blueprints
from .utils.logger import setup_logging
from .socketio_setup import socketio
from ..config import Config  # Changed from 'from config' to 'from ..config'
from celery.signals import worker_process_init

@worker_process_init.connect
def init_flask_context(**kwargs):
    app = create_app()
    app.app_context().push()

redis_client = redis.Redis(host='redis', port=6379, db=0)
celery = Celery('app', broker='redis://redis:6379/0', include=['pve.app.vpl.tasks'])
include=['pve.app.vpl.tasks']


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app)
    setup_logging(app)
    register_blueprints(app)
    socketio.init_app(app)
    celery.conf.update(app.config)
    from .websocket import socket_handlers
    return app