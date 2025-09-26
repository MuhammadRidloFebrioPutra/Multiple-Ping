from app import create_app
from app.utils.multi_ping_service import get_multi_ping_service
from app.routes.whatsapp_routes import get_whatsapp_service
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

# Initialize WhatsApp Service
whatsapp_service = None

def initialize_services():
    """Initialize all services"""
    global monitoring_service, whatsapp_service
    
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
    
    # Initialize WhatsApp Service
    try:
        whatsapp_service = get_whatsapp_service()
        whatsapp_status = whatsapp_service.test_setup()
        
        if whatsapp_status.get('overall_status') == 'ready':
            print("✅ WhatsApp Alert Service initialized")
            contacts_count = whatsapp_status['contacts_file']['contacts_loaded']
            print(f"   - Contacts loaded: {contacts_count}")
            print(f"   - Chrome binary: {'✅' if whatsapp_status['chrome_binary']['exists'] else '❌'}")
        else:
            print("⚠️  WhatsApp Alert Service needs setup")
            print("   - Check contacts.txt file and Chrome installation")
            
    except Exception as e:
        print(f"❌ Failed to initialize WhatsApp service: {e}")
        whatsapp_service = None

def cleanup_services():
    """Cleanup all services"""
    if monitoring_service:
        monitoring_service.stop()
        print(f"🛑 {service_name} stopped")
    
    if whatsapp_service:
        whatsapp_service.cleanup()
        print("🛑 WhatsApp Alert Service stopped")

# Register cleanup function
atexit.register(cleanup_services)

# Initialize services
initialize_services()

if __name__ == "__main__":
    try:
        print(f"🚀 Starting integrated Flask application on http://localhost:5000")
        print(f"📡 Available endpoints:")
        print(f"   - Ping API: http://localhost:5000/api/ping/")
        print(f"   - WhatsApp API: http://localhost:5000/api/whatsapp/")
        print(f"   - WhatsApp Alert: http://localhost:5000/api/whatsapp/alert?id=CCTV-1")
        
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down services...")
    finally:
        # Ensure services are stopped when app exits
        cleanup_services()
