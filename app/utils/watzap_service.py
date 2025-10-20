"""
Watzap Service - Service wrapper untuk Watzap API
Terpisah dari whatsapp_service.py (legacy Selenium)
"""
import logging
from typing import Dict, List, Optional
from app.utils.watzap import WatzapAPI, send_timeout_alert_to_groups, load_group_ids_from_file

logger = logging.getLogger(__name__)

class WatzapService:
    """
    Service wrapper untuk Watzap API
    Tidak menggunakan Selenium, hanya Watzap API
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Watzap Service
        
        Args:
            api_key: Optional API key, jika tidak diset akan menggunakan default
        """
        self.watzap = WatzapAPI(api_key)
        logger.info("Watzap Service initialized")
    
    def send_message(self, group_id: Optional[str] = None, message: str = "") -> Dict:
        """
        Kirim pesan ke WhatsApp group
        
        Args:
            group_id: ID group WhatsApp, jika None akan menggunakan default group
            message: Pesan yang akan dikirim
            
        Returns:
            Dict dengan status response
        """
        try:
            if not group_id:
                group_id = self.watzap.default_group_id
            
            result = self.watzap.send_message_to_group(group_id, message)
            logger.info(f"Message sent via Watzap to {group_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error sending message via Watzap: {e}")
            return {"status": "error", "message": str(e)}
    
    def send_timeout_alert(self, device_data: Dict, group_ids: Optional[List[str]] = None) -> Dict:
        """
        Kirim alert timeout perangkat
        
        Args:
            device_data: Data perangkat yang timeout
            group_ids: Optional list of group IDs, jika None akan menggunakan default group
            
        Returns:
            Dict hasil pengiriman
        """
        try:
            if not group_ids:
                group_ids = [self.watzap.default_group_id]
            
            logger.info(f"📤 Sending timeout alert via Watzap for {device_data.get('hostname', 'Unknown')} ({device_data.get('ip_address', 'Unknown')})")
            logger.info(f"   Target groups: {group_ids}")
            logger.info(f"   Device data: IP={device_data.get('ip_address')}, Device ID={device_data.get('device_id')}, Timeouts={device_data.get('consecutive_timeouts')}")
            
            result = send_timeout_alert_to_groups(device_data, group_ids)
            
            logger.info(f"📬 Watzap alert result: Status={result.get('status')}, Success={result.get('success_count', 0)}/{len(group_ids)}")
            if result.get('status') == 'success':
                logger.info(f"✅ Timeout alert sent successfully for device {device_data.get('ip_address', 'Unknown')}")
            else:
                logger.warning(f"⚠️ Timeout alert may have issues: {result}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error sending timeout alert: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return {"status": "error", "message": str(e)}
    
    def broadcast_message(self, message: str, group_ids: Optional[List[str]] = None) -> Dict:
        """
        Broadcast pesan ke multiple groups
        
        Args:
            message: Pesan yang akan di-broadcast
            group_ids: Optional list of group IDs, jika None akan menggunakan default group
            
        Returns:
            Dict hasil broadcast
        """
        try:
            if not group_ids:
                group_ids = [self.watzap.default_group_id]
            
            result = self.watzap.send_broadcast_to_groups(group_ids, message)
            logger.info(f"Broadcast completed: {result['success_count']} success, {result['failed_count']} failed")
            return result
            
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            return {"status": "error", "message": str(e)}
    
    def check_connection(self) -> Dict:
        """
        Cek status koneksi Watzap API
        
        Returns:
            Dict dengan status koneksi
        """
        try:
            status = self.watzap.check_connection_status()
            logger.info("Watzap connection status checked")
            return status
            
        except Exception as e:
            logger.error(f"Error checking connection: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_status(self) -> Dict:
        """
        Get status lengkap dari Watzap service
        
        Returns:
            Dict dengan informasi status
        """
        try:
            connection_status = self.check_connection()
            
            return {
                "service_name": "Watzap Service",
                "api_key": "configured" if self.watzap.api_key else "missing",
                "default_group": self.watzap.default_group_id,
                "base_url": self.watzap.base_url,
                "connection_status": connection_status,
                "overall_status": "ready" if connection_status.get('status') == 'success' else "error"
            }
            
        except Exception as e:
            logger.error(f"Error getting Watzap status: {e}")
            return {"error": str(e), "overall_status": "error"}
    
    def load_groups_from_file(self, file_path: str) -> List[str]:
        """
        Load group IDs dari file
        
        Args:
            file_path: Path ke file yang berisi group IDs
            
        Returns:
            List group IDs
        """
        try:
            group_ids = load_group_ids_from_file(file_path)
            logger.info(f"Loaded {len(group_ids)} group IDs from file")
            return group_ids
            
        except Exception as e:
            logger.error(f"Error loading groups from file: {e}")
            return []
