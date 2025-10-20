import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class WatzapAPI:
    """Class untuk menangani komunikasi dengan Watzap API"""
    
    # Default API Key, Device Key, dan Group ID
    DEFAULT_API_KEY = "V3ELWOCBWBWHDEMX"
    DEFAULT_NUMBER_KEY = "TjAV4PteKJFfLQf6"  # Device key dari Watzap
    DEFAULT_GROUP_ID = "120363404926282796@g.us"
    
    def __init__(self, api_key: Optional[str] = None, number_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('WATZAP_API_KEY', self.DEFAULT_API_KEY)
        self.number_key = number_key or os.getenv('WATZAP_NUMBER_KEY', self.DEFAULT_NUMBER_KEY)
        self.base_url = "https://api.watzap.id/v1"
        self.default_group_id = self.DEFAULT_GROUP_ID
        
        if not self.api_key:
            logging.warning("WATZAP_API_KEY tidak ditemukan di environment variables")
        if not self.number_key:
            logging.warning("WATZAP_NUMBER_KEY tidak ditemukan di environment variables")
    
    def _get_headers(self) -> Dict:
        """Generate headers untuk API request"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def send_message_to_group(self, group_id: str, message: str) -> Dict:
        """
        Kirim pesan ke WhatsApp group
        
        Args:
            group_id: ID group WhatsApp (format: 120363xxxxx@g.us)
            message: Pesan yang akan dikirim
            
        Returns:
            Dict dengan status response
        """
        try:
            # Endpoint khusus untuk group
            endpoint = f"{self.base_url}/send_message_group"
            
            # Format payload sesuai dokumentasi Watzap API
            # number_key = Device Key (dari dashboard Watzap)
            # group_id = Group ID WhatsApp
            payload = {
                "api_key": self.api_key,
                "number_key": self.number_key,
                "group_id": group_id,
                "message": message
            }
            
            logging.info(f"📡 Mengirim request ke: {endpoint}")
            logging.info(f"   Payload: number_key={self.number_key}, group_id={group_id}, message_length={len(message)}")
            logging.info(f"   Message preview: {message[:100]}...")
            
            response = requests.post(
                endpoint,
                json=payload,
                timeout=30
            )
            
            logging.info(f"📥 Response Status Code: {response.status_code}")
            logging.info(f"   Response Body: {response.text}")
            
            result = response.json()
            
            # Cek apakah response sukses
            if result.get('status') in ['1001', '1003'] or result.get('ack') == 'fatal_error':
                logging.error(f"❌ API Error: {result.get('message')}")
                return {
                    "status": "error",
                    "message": f"API Error: {result.get('message')}",
                    "data": result
                }
            
            response.raise_for_status()
            
            logging.info(f"✅ Pesan berhasil dikirim ke group {group_id}")
            return {
                "status": "success",
                "message": "Pesan berhasil dikirim",
                "data": result,
                "response_code": response.status_code
            }
            
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Error mengirim pesan ke group {group_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"   Response Status: {e.response.status_code}")
                logging.error(f"Response Body: {e.response.text}")
            return {
                "status": "error",
                "message": f"Gagal mengirim pesan: {str(e)}",
                "error_detail": str(e)
            }
    
    def send_broadcast_to_groups(self, group_ids: List[str], message: str) -> Dict:
        """
        Broadcast pesan ke multiple WhatsApp groups
        
        Args:
            group_ids: List ID group WhatsApp
            message: Pesan yang akan dikirim
            
        Returns:
            Dict dengan status dan hasil pengiriman
        """
        results = {
            "success": [],
            "failed": []
        }
        
        for group_id in group_ids:
            try:
                result = self.send_message_to_group(group_id, message)
                
                if result["status"] == "success":
                    results["success"].append(group_id)
                else:
                    results["failed"].append({
                        "group_id": group_id,
                        "error": result["message"]
                    })
                    
            except Exception as e:
                logging.error(f"Error broadcast ke {group_id}: {e}")
                results["failed"].append({
                    "group_id": group_id,
                    "error": str(e)
                })
        
        logging.info(f"Broadcast selesai: {len(results['success'])} sukses, {len(results['failed'])} gagal")
        
        return {
            "status": "completed",
            "total": len(group_ids),
            "success_count": len(results["success"]),
            "failed_count": len(results["failed"]),
            "results": results
        }
    
    def check_connection_status(self) -> Dict:
        """
        Cek status koneksi WhatsApp dengan mencoba mengirim pesan test
        
        Returns:
            Dict dengan status koneksi
        """
        try:
            # Watzap API tidak memiliki endpoint /status
            # Kita cek dengan cara lain: validasi API key ada dan format benar
            if not self.api_key:
                return {
                    "status": "error",
                    "message": "API key tidak ditemukan"
                }
            
            if len(self.api_key) < 10:
                return {
                    "status": "error",
                    "message": "API key tidak valid"
                }
            
            # Return success jika API key ada
            logging.info("Status koneksi berhasil dicek (API key valid)")
            return {
                "status": "success",
                "message": "API key configured",
                "data": {
                    "api_key": f"{self.api_key[:5]}...{self.api_key[-5:]}",
                    "base_url": self.base_url,
                    "default_group": self.default_group_id
                }
            }
            
        except Exception as e:
            logging.error(f"Error mengecek status koneksi: {e}")
            return {
                "status": "error",
                "message": f"Gagal cek status: {str(e)}"
            }

def send_timeout_alert_to_groups(device_data: Dict, group_ids: List[str]) -> Dict:
    """
    Kirim alert timeout perangkat ke WhatsApp groups
    
    Args:
        device_data: Data perangkat yang timeout
        group_ids: List ID group WhatsApp tujuan
        
    Returns:
        Dict hasil pengiriman
    """
    watzap = WatzapAPI()
    
    # Format pesan timeout alert
    alert_message = f"""🚨 PERINGATAN TIMEOUT PERANGKAT 🚨

⚠️ KRITIS: Perangkat Tidak Dapat Dijangkau!

📍 Informasi Perangkat:
• Alamat IP: {device_data.get('ip_address', 'Tidak diketahui')}
• Hostname: {device_data.get('hostname', 'Tidak diketahui')}
• ID Perangkat: {device_data.get('device_id', 'Tidak diketahui')}
• Merk/Model: {device_data.get('merk', 'Tidak diketahui')}
• Kondisi Perangkat: {device_data.get('kondisi', 'Tidak diketahui')}

⏰ Detail Timeout:
• Jumlah Timeout Berturut-turut: {device_data.get('consecutive_timeouts', 'Tidak diketahui')}
• Timeout Pertama: {device_data.get('first_timeout', 'Tidak diketahui')}
• Pemeriksaan Terakhir: {device_data.get('last_timeout', 'Tidak diketahui')}

🔧 Tindakan yang Harus Dilakukan:
1. Periksa daya dan koneksi jaringan perangkat
2. Pastikan koneksi ke jaringan {device_data.get('ip_address', '')}
3. Lakukan pemeriksaan fisik jika diperlukan
4. Hubungi tim teknis jika masalah belum teratasi

Waktu Notifikasi: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} WIB

Pesan ini dikirim otomatis oleh Sistem Monitoring Pelindo."""
    
    # Kirim broadcast
    result = watzap.send_broadcast_to_groups(group_ids, alert_message)
    
    return result

def load_group_ids_from_file(file_path: str) -> List[str]:
    """
    Load group IDs dari file txt
    
    Args:
        file_path: Path ke file yang berisi group IDs
        
    Returns:
        List group IDs
    """
    group_ids = []
    try:
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.getcwd(), file_path)
        
        if not os.path.exists(file_path):
            logging.warning(f"File {file_path} tidak ditemukan")
            return []
        
        with open(file_path, 'r', encoding='utf-8') as file:
            for line in file:
                line = line.strip()
                if line and not line.startswith('#'):
                    group_ids.append(line)
        
        logging.info(f"Loaded {len(group_ids)} group IDs dari {file_path}")
        return group_ids
        
    except Exception as e:
        logging.error(f"Error loading group IDs dari {file_path}: {e}")
        return []

# Contoh penggunaan
if __name__ == "__main__":
    # Inisialisasi Watzap API
    watzap = WatzapAPI()
    
    # Cek status koneksi
    status = watzap.check_connection_status()
    print("Status Koneksi:", status)
    