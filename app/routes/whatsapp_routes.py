from flask import Blueprint, request, jsonify
import os
import logging
from app.utils.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)

whatsapp_bp = Blueprint('whatsapp', __name__)

# Global WhatsApp service instance
whatsapp_service = None

def get_whatsapp_service():
    """Get or create WhatsApp service instance"""
    global whatsapp_service
    if whatsapp_service is None:
        # Get project root directory
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        contacts_file = os.path.join(project_root, "contacts.txt")
        profile_path = os.path.abspath("chrome_profile")
        chrome_binary = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        
        whatsapp_service = WhatsAppService(
            contacts_file=contacts_file,
            profile_path=profile_path,
            chrome_binary=chrome_binary
        )
        logger.info("WhatsApp service initialized")
    
    return whatsapp_service

@whatsapp_bp.route('/whatsapp/alert', methods=['GET'])
def send_alert():
    """Send WhatsApp alert"""
    try:
        cctv_id = request.args.get('id')
        if not cctv_id:
            return jsonify({"status": "error", "message": "Missing cctv_id parameter"}), 400

        service = get_whatsapp_service()
        result = service.send_alert(cctv_id)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error sending WhatsApp alert: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@whatsapp_bp.route('/whatsapp/status', methods=['GET'])
def get_whatsapp_status():
    """Get WhatsApp service status"""
    try:
        service = get_whatsapp_service()
        status = service.get_status()
        
        return jsonify({
            "status": "success",
            "data": status
        })
    except Exception as e:
        logger.error(f"Error getting WhatsApp status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@whatsapp_bp.route('/whatsapp/test', methods=['POST'])
def test_whatsapp():
    """Test WhatsApp service without sending actual message"""
    try:
        service = get_whatsapp_service()
        test_result = service.test_setup()
        
        return jsonify({
            "status": "success",
            "data": test_result
        })
    except Exception as e:
        logger.error(f"Error testing WhatsApp service: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@whatsapp_bp.route('/whatsapp/contacts', methods=['GET'])
def get_contacts():
    """Get loaded contacts/groups"""
    try:
        service = get_whatsapp_service()
        contacts = service.get_contacts()
        
        return jsonify({
            "status": "success",
            "data": contacts,
            "count": len(contacts)
        })
    except Exception as e:
        logger.error(f"Error getting contacts: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@whatsapp_bp.route('/whatsapp/session/save', methods=['POST'])
def save_session():
    """Manually save WhatsApp session"""
    try:
        service = get_whatsapp_service()
        result = service.save_session()
        
        return jsonify({
            "status": "success",
            "data": result
        })
    except Exception as e:
        logger.error(f"Error saving session: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@whatsapp_bp.route('/whatsapp/driver/close', methods=['POST'])
def close_driver():
    """Close WhatsApp browser driver"""
    try:
        service = get_whatsapp_service()
        service.close_driver()
        
        return jsonify({
            "status": "success",
            "message": "WhatsApp driver closed"
        })
    except Exception as e:
        logger.error(f"Error closing driver: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
