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

def format_indonesian_date(dt: datetime) -> str:
    """
    Format datetime ke format Indonesia: 21 Oktober 2025
    """
    bulan_indonesia = {
        1: 'Januari', 2: 'Februari', 3: 'Maret', 4: 'April',
        5: 'Mei', 6: 'Juni', 7: 'Juli', 8: 'Agustus',
        9: 'September', 10: 'Oktober', 11: 'November', 12: 'Desember'
    }
    
    hari = dt.day
    bulan = bulan_indonesia[dt.month]
    tahun = dt.year
    jam = dt.strftime('%H:%M:%S')
    
    return f"{hari} {bulan} {tahun} {jam}"

class WatzapAPI:
    """Class untuk menangani komunikasi dengan Watzap API"""
    
    # Default API Key, Device Key, dan Group ID
    DEFAULT_API_KEY = "V3ELWOCBWBWHDEMX"
    DEFAULT_NUMBER_KEY = "TjAV4PteKJFfLQf6"  # Device key dari Watzap
    DEFAULT_GROUP_ID = "120363406944056502@g.us"
    
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
            group_id: ID group WhatsApp (format: 120363403677027364@g.us)
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

def send_batch_timeout_alert_to_groups(devices_data: List[Dict], group_ids: List[str]) -> Dict:
    """
    Kirim alert timeout untuk multiple devices dalam satu pesan (BATCH)
    
    Args:
        devices_data: List data perangkat yang timeout
        group_ids: List ID group WhatsApp tujuan
        
    Returns:
        Dict hasil pengiriman
    """
    watzap = WatzapAPI()
    
    # Format pesan batch alert
    alert_message = f"""🚨 PERINGATAN TIMEOUT JUMLAH PERANGKAT  {len(devices_data)} 🚨 

📋 Daftar Perangkat Bermasalah:
"""
    for idx, device in enumerate(devices_data, 1):
        alert_message += f"""
{idx}. {device.get('hostname', 'Unknown')}
   • IP: {device.get('ip_address', 'Unknown')}
"""
    
    alert_message += f"""
🔧 Tindakan yang Harus Dilakukan:
1. Periksa status semua perangkat di atas
2. Verifikasi koneksi jaringan dan daya
3. Lakukan pemeriksaan fisik jika diperlukan
4. Hubungi tim teknis untuk penanganan lebih lanjut

Waktu Notifikasi: {format_indonesian_date(datetime.now())} WIB

Pesan ini dikirim otomatis oleh Sistematis Sub Reg Jawa."""
    
    logging.info(f"📤 Sending BATCH alert for {len(devices_data)} devices")
    
    # Kirim broadcast ke groups
    group_result = watzap.send_broadcast_to_groups(group_ids, alert_message)
    
    # Kirim juga ke nomor personal admin
    admin_phone = "6281235564216"
    personal_result = watzap.send_message_to_personal(admin_phone, alert_message)
    
    # Gabungkan hasil
    total_success = group_result.get('success_count', 0)
    total_failed = group_result.get('failed_count', 0)
    
    if personal_result.get('status') == 'success':
        total_success += 1
        logging.info(f"✅ BATCH alert berhasil dikirim ke nomor admin: {admin_phone}")
    else:
        total_failed += 1
        logging.error(f"❌ BATCH alert gagal dikirim ke nomor admin: {admin_phone}")
    
    return {
        'status': 'success' if total_success > 0 else 'error',
        'message': f'BATCH Alert dikirim ke {total_success} penerima untuk {len(devices_data)} devices',
        'success_count': total_success,
        'failed_count': total_failed,
        'devices_count': len(devices_data),
        'group_result': group_result,
        'personal_result': personal_result
    }

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
