from app import create_app
from app.utils.multi_ping_service import get_multi_ping_service
# from app.routes.whatsapp_routes import get_whatsapp_service  # DISABLED - Menggunakan Watzap
from app.routes.watzap_routes import get_watzap_service
from config import Config
import atexit
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = create_app()

# Initialize Multi-Ping Monitoring Service
config = Config()
monitoring_service = get_multi_ping_service(config)
service_name = "Multi-Ping Monitoring Service"

# Initialize Watzap Service only (WhatsApp Selenium disabled)
watzap_service = None

def initialize_services():
    """Initialize all services"""
    global monitoring_service, watzap_service
    
    # Initialize Multi-Ping Service
    if monitoring_service:
        monitoring_service.start()
        print(f"✅ {service_name} started")
        print(f"⚙️  Configuration:")
        print(f"   - Ping interval: {config.PING_INTERVAL}s")
        print(f"   - CSV output: {config.CSV_OUTPUT_DIR}")
        print(f"   - Max workers: {config.MAX_PING_WORKERS}")
        print(f"   - Ping timeout: {config.PING_TIMEOUT}s")
        
        # Get device count
        device_count = monitoring_service.get_device_count()
        print(f"   - Active devices: {device_count}")
    else:
        print("❌ Failed to initialize Multi-Ping Monitoring Service")
    
    # WhatsApp Selenium Service DISABLED - Using Watzap API instead
    print("ℹ️  WhatsApp Selenium service disabled (using Watzap API)")
    
    # Initialize Watzap Service
    try:
        watzap_service = get_watzap_service()
        watzap_status = watzap_service.get_status()
        
        if watzap_status.get('overall_status') == 'ready':
            print("✅ Watzap Service initialized")
            print(f"   - API Key: {watzap_status.get('api_key', 'Not configured')}")
            print(f"   - Number Key: configured")
            print(f"   - Default Group: {watzap_status.get('default_group', 'Not set')}")
            conn_status = watzap_status.get('connection_status', {})
            print(f"   - Connection: {'✅ Connected' if conn_status.get('status') == 'success' else '❌ Error'}")
        else:
            print("⚠️  Watzap Service needs setup")
            print("   - Check WATZAP_API_KEY configuration")
            
    except Exception as e:
        print(f"❌ Failed to initialize Watzap service: {e}")
        watzap_service = None

def cleanup_services():
    """Cleanup all services"""
    if monitoring_service:
        monitoring_service.stop()
        print(f"🛑 {service_name} stopped")
    
    # WhatsApp Selenium cleanup disabled
    
    if watzap_service:
        print("🛑 Watzap Service stopped")

# Register cleanup function
atexit.register(cleanup_services)

# Initialize services
initialize_services()

if __name__ == "__main__":
    try:
        print(f"\n🚀 Starting integrated Flask application on http://localhost:5000")
        print(f"📡 Available endpoints:")
        print(f"   - Ping API: http://localhost:5000/api/ping/")
        print(f"   - Watzap API: http://localhost:5000/api/watzap/")
        print(f"")
        print(f"📤 Watzap Endpoints:")
        print(f"   - Status: GET  http://localhost:5000/api/watzap/status")
        print(f"   - Send:   POST http://localhost:5000/api/watzap/send")
        print(f"   - Alert:  POST http://localhost:5000/api/watzap/timeout-alert")
        print(f"   - Broadcast: POST http://localhost:5000/api/watzap/broadcast")
        print(f"   - Test:   GET  http://localhost:5000/api/watzap/test")
        print(f"")
        print(f"ℹ️  WhatsApp Selenium endpoints disabled - Using Watzap API")
        
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
    finally:
        # Ensure services are stopped when app exits
        cleanup_services()
