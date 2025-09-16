from app import create_app
from app.utils.multi_ping_service import get_multi_ping_service
from config import Config
import atexit

app = create_app()

# Initialize Multi-Ping Monitoring Service
config = Config()
monitoring_service = get_multi_ping_service(config)
service_name = "Multi-Ping Monitoring Service"

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
    
    # Register cleanup function
    def cleanup():
        if monitoring_service:
            monitoring_service.stop()
            print(f"🛑 {service_name} stopped")
    
    atexit.register(cleanup)
else:
    print("❌ Failed to initialize Multi-Ping Monitoring Service")

if __name__ == "__main__":
    try:
        print(f"🚀 Starting Flask app on http://localhost:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)
    finally:
        # Ensure service is stopped when app exits
        if monitoring_service:
            monitoring_service.stop()
