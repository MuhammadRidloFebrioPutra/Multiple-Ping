# wsgi.py
import atexit
import logging
from app import create_app
from app.utils.multi_ping_service import get_multi_ping_service
from app.routes.whatsapp_routes import get_whatsapp_service
from config import Config

# logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = create_app()

# Services (same logic, but DO NOT call app.run here)
config = Config()
monitoring_service = get_multi_ping_service(config)
whatsapp_service = None
service_name = "Multi-Ping Monitoring Service"

def initialize_services():
    global monitoring_service, whatsapp_service
    try:
        if monitoring_service:
            monitoring_service.start()
            logger.info("%s started", service_name)
            logger.info("Ping interval: %ss", config.PING_INTERVAL)
            logger.info("CSV output: %s", config.CSV_OUTPUT_DIR)
            logger.info("Max workers: %s", config.MAX_PING_WORKERS)
            logger.info("Ping timeout: %ss", config.PING_TIMEOUT)
            logger.info("Active devices: %s", monitoring_service.get_device_count())
        else:
            logger.error("Failed to initialize Multi-Ping Monitoring Service")
    except Exception:
        logger.exception("Error starting monitoring_service")

    try:
        whatsapp_service = get_whatsapp_service()
        whatsapp_status = whatsapp_service.test_setup()
        if whatsapp_status.get('overall_status') == 'ready':
            logger.info("WhatsApp Alert Service initialized")
            logger.info("Contacts loaded: %s", whatsapp_status['contacts_file']['contacts_loaded'])
            logger.info("Chrome binary exists: %s", whatsapp_status['chrome_binary']['exists'])
        else:
            logger.warning("WhatsApp Alert Service needs setup")
    except Exception:
        logger.exception("Failed to initialize WhatsApp service")
        whatsapp_service = None

def cleanup_services():
    global monitoring_service, whatsapp_service
    try:
        if monitoring_service:
            monitoring_service.stop()
            logger.info("%s stopped", service_name)
    except Exception:
        logger.exception("Error stopping monitoring_service")

    try:
        if whatsapp_service:
            whatsapp_service.cleanup()
            logger.info("WhatsApp Alert Service stopped")
    except Exception:
        logger.exception("Error cleaning up whatsapp_service")

# register cleanup on process exit
atexit.register(cleanup_services)

# initialize at import time (Gunicorn will import this module)
initialize_services()
