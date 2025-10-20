"""
Watzap Routes - API endpoints untuk Watzap service
Terpisah dari whatsapp_routes.py (legacy Selenium)
"""
from flask import Blueprint, request, jsonify
import logging
from app.utils.watzap_service import WatzapService

logger = logging.getLogger(__name__)

watzap_bp = Blueprint('watzap', __name__)

# Global Watzap service instance
watzap_service = None

def get_watzap_service():
    """Get or create Watzap service instance"""
    global watzap_service
    if watzap_service is None:
        watzap_service = WatzapService()
        logger.info("Watzap service initialized")
    
    return watzap_service

@watzap_bp.route('/watzap/status', methods=['GET'])
def get_status():
    """Get Watzap service status"""
    try:
        service = get_watzap_service()
        status = service.get_status()
        
        return jsonify({
            "status": "success",
            "data": status
        })
    except Exception as e:
        logger.error(f"Error getting Watzap status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@watzap_bp.route('/watzap/connection', methods=['GET'])
def check_connection():
    """Check Watzap API connection"""
    try:
        service = get_watzap_service()
        connection = service.check_connection()
        
        return jsonify({
            "status": "success",
            "data": connection
        })
    except Exception as e:
        logger.error(f"Error checking connection: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@watzap_bp.route('/watzap/send', methods=['POST'])
def send_message():
    """
    Send message to WhatsApp group
    
    Body:
    {
        "group_id": "120363404926282780@g.us",  // optional, default group if not provided
        "message": "Your message here"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing 'message' field"
            }), 400
        
        message = data['message']
        group_id = data.get('group_id', None)
        
        service = get_watzap_service()
        result = service.send_message(group_id, message)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@watzap_bp.route('/watzap/timeout-alert', methods=['POST'])
def send_timeout_alert():
    """
    Send timeout alert for device
    
    Body:
    {
        "ip_address": "192.168.1.100",
        "hostname": "CCTV-01",
        "device_id": "CCTV-001",
        "merk": "Hikvision",
        "kondisi": "Aktif",
        "consecutive_timeouts": 15,
        "first_timeout": "2025-10-20 10:00:00",
        "last_timeout": "2025-10-20 10:15:00",
        "group_ids": ["120363404926282780@g.us"]  // optional
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "status": "error",
                "message": "Missing device data"
            }), 400
        
        # Extract group_ids if provided
        group_ids = data.pop('group_ids', None)
        
        # Rest of data is device_data
        device_data = data
        
        service = get_watzap_service()
        result = service.send_timeout_alert(device_data, group_ids)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error sending timeout alert: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@watzap_bp.route('/watzap/broadcast', methods=['POST'])
def broadcast_message():
    """
    Broadcast message to multiple groups
    
    Body:
    {
        "message": "Your message here",
        "group_ids": ["120363404926282780@g.us", "another_group@g.us"]  // optional
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'message' not in data:
            return jsonify({
                "status": "error",
                "message": "Missing 'message' field"
            }), 400
        
        message = data['message']
        group_ids = data.get('group_ids', None)
        
        service = get_watzap_service()
        result = service.broadcast_message(message, group_ids)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error broadcasting message: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@watzap_bp.route('/watzap/test', methods=['GET'])
def test_watzap():
    """
    Test Watzap service with a simple message
    """
    try:
        service = get_watzap_service()
        
        from datetime import datetime
        test_message = f"""🧪 TEST MESSAGE

Ini adalah pesan test dari Watzap API.

Waktu: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} WIB

Jika Anda menerima pesan ini, berarti integrasi berhasil! ✅"""
        
        result = service.send_message(message=test_message)
        
        return jsonify({
            "status": "success",
            "message": "Test message sent",
            "data": result
        })
        
    except Exception as e:
        logger.error(f"Error testing Watzap: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
