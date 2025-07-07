import os

class Config:
    DEBUG = False
    TESTING = False

    # Database configurations
    DB_HOST = os.environ.get('DB_HOST', 'postgresql')
    DB_NAME = os.environ.get('DB_NAME', 'postgres')
    DB_USER = os.environ.get('DB_USER', 'postgres')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'postgres')

    # Telegram Bot Token - REQUIRED: Get from @BotFather on Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    FLASK_ENV = os.getenv('FLASK_ENV', 'dev')
    
    # Only require Telegram token in production
    if FLASK_ENV not in ['dev', 'development'] and not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required for production")

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    TESTING = True
