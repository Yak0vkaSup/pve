import eventlet
eventlet.monkey_patch()

from pve.app import create_app
from pve.app.socketio_setup import socketio
from pve.config import DevelopmentConfig

app = create_app(config_class=DevelopmentConfig)
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)