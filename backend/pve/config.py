import os

class Config:
    DEBUG = False
    TESTING = False

    # Database configurations
    DB_HOST = os.environ.get('DB_HOST', 'postgresql')
    DB_NAME = os.environ.get('DB_NAME', 'postgres')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')

    # Telegram Bot Token
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '6180226975:AAHePZ0wipSWogSkZDFXmf6tm8DwDXVPgJI')

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    TESTING = True
