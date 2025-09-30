import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    #url and port for CORS
    CONFIG_HOST = os.getenv('CONFIG_HOST', '127.0.0.1')
    CONFIG_PORT = os.getenv('CONFIG_PORT', '5000')
    
    # Database configuration
    DB_CONNECTION = os.getenv('DB_CONNECTION', 'mysql+pymysql')
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_DATABASE = os.getenv('DB_DATABASE', 'kaido_kit')
    DB_USERNAME = os.getenv('DB_USERNAME', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    
    # SQLAlchemy database URI - Force PyMySQL driver
    if DB_PASSWORD:
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
    else:
        SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USERNAME}@{DB_HOST}:{DB_PORT}/{DB_DATABASE}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    
    # Ping monitoring configuration
    PING_INTERVAL = int(os.getenv('PING_INTERVAL', '5'))  # seconds
    CSV_OUTPUT_DIR = os.getenv('CSV_OUTPUT_DIR', 'ping_results')
    MAX_CSV_RECORDS = int(os.getenv('MAX_CSV_RECORDS', '1000'))  # Maximum records per CSV file
    
    # Multi-ping configuration
    MAX_PING_WORKERS = int(os.getenv('MAX_PING_WORKERS', '20'))  # Max concurrent ping threads
    PING_TIMEOUT = int(os.getenv('PING_TIMEOUT', '3'))  # Ping timeout in seconds
    
    # Timeout tracking configuration
    ENABLE_TIMEOUT_TRACKING = os.getenv('ENABLE_TIMEOUT_TRACKING', 'true').lower() == 'true'
    TIMEOUT_CRITICAL_THRESHOLD = int(os.getenv('TIMEOUT_CRITICAL_THRESHOLD', '5'))  # Critical consecutive timeouts
    
    # WhatsApp Alert Configuration for Timeout
    ENABLE_WHATSAPP_TIMEOUT_ALERTS = os.getenv('ENABLE_WHATSAPP_TIMEOUT_ALERTS', 'true').lower() == 'true'
    WHATSAPP_TIMEOUT_THRESHOLD = int(os.getenv('WHATSAPP_TIMEOUT_THRESHOLD', '20'))  # Send WA after 20 consecutive timeouts
    WHATSAPP_COOLDOWN_MINUTES = int(os.getenv('WHATSAPP_COOLDOWN_MINUTES', '60'))  # Cooldown between alerts for same device
    
    # Database monitoring configuration
    DEVICE_CHECK_INTERVAL = int(os.getenv('DEVICE_CHECK_INTERVAL', '30'))  # Check database every 30 seconds
    
    SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'