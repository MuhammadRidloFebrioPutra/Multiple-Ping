import os
import csv
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

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

class TimeoutTracker:
    """
    Class untuk mengelola tracking timeout berturut-turut per IP address
    """
    
    def __init__(self, config, app=None):
        self.config = config
        self.app = app  # Store Flask app for database context
        self.timeout_dir = getattr(config, 'CSV_OUTPUT_DIR', 'ping_results')
        self.timeout_filename = 'timeout_tracking.csv'
        self.timeout_csv_path = os.path.join(self.timeout_dir, self.timeout_filename)
        self.alerted_list_filename = 'whatsapp_alerted_list.csv'
        self.alerted_list_csv_path = os.path.join(self.timeout_dir, self.alerted_list_filename)

        # WhatsApp Alert Configuration
        self.whatsapp_enabled = getattr(config, 'ENABLE_WHATSAPP_TIMEOUT_ALERTS', True)
        self.whatsapp_threshold = getattr(config, 'WHATSAPP_TIMEOUT_THRESHOLD', 20)
        self.whatsapp_cooldown_minutes = getattr(config, 'WHATSAPP_COOLDOWN_MINUTES', 60)
        
        # Incident Management Configuration
        self.incident_enabled = getattr(config, 'ENABLE_INCIDENT_CREATION', True)
        
        # Ensure directory exists
        os.makedirs(self.timeout_dir, exist_ok=True)
        
        # CSV headers for timeout tracking
        self.timeout_headers = [
            'ip_address', 'hostname', 'device_id', 'merk', 'os', 'kondisi',
            'consecutive_timeouts', 'first_timeout', 'last_timeout', 'last_updated',
        ]
        self.alerted_list_headers = ['ip_address', 'hostname', 'device_id',]
        
        # Initialize CSV file if not exists
        self._initialize_timeout_csv()
        self._initialize_alerted_list_csv()
        
        # Initialize timeout analytics
        from app.utils.timeout_analytics import TimeoutAnalytics
        self.analytics = TimeoutAnalytics(config)
        
        # Initialize incident manager
        if self.incident_enabled:
            from app.utils.incident_manager import IncidentManager
            self.incident_manager = IncidentManager(config, app=self.app)
            logger.info(f"Incident Manager enabled (threshold: {self.incident_manager.incident_threshold_minutes} minutes)")
        else:
            self.incident_manager = None
            logger.info("Incident Manager disabled")
        
        # Track previous timeout IPs for analytics
        self.previous_timeout_ips = set()
        
        logger.info(f"TimeoutTracker initialized - CSV: {self.timeout_csv_path}")
        logger.info(f"Alerted List initialized - CSV: {self.alerted_list_csv_path}")
        logger.info(f"WhatsApp alerts: {'enabled' if self.whatsapp_enabled else 'disabled'} (threshold: {self.whatsapp_threshold})")
    
    def _initialize_timeout_csv(self):
        """Initialize timeout CSV file with headers if not exists"""
        if not os.path.exists(self.timeout_csv_path):
            try:
                with open(self.timeout_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.timeout_headers)
                    writer.writeheader()
                logger.info(f"Created new timeout tracking CSV: {self.timeout_filename}")
            except Exception as e:
                logger.error(f"Error creating timeout CSV: {e}")

    def _initialize_alerted_list_csv(self):
        """Initialize timeout CSV file with headers if not exists"""
        if not os.path.exists(self.alerted_list_csv_path):
            try:
                with open(self.alerted_list_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.alerted_list_headers)
                    writer.writeheader()
                logger.info(f"Created new timeout tracking CSV: {self.alerted_list_filename}")
            except Exception as e:
                logger.error(f"Error creating timeout CSV: {e}")
    
    def _read_timeout_data(self) -> Dict[str, Dict]:
        """Read existing timeout data from CSV"""
        timeout_data = {}
        
        if not os.path.exists(self.timeout_csv_path):
            return timeout_data
        
        try:
            with open(self.timeout_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    ip_address = row['ip_address']
                    timeout_data[ip_address] = dict(row)
            
            logger.debug(f"Read {len(timeout_data)} timeout entries from CSV")
            return timeout_data
            
        except Exception as e:
            logger.error(f"Error reading timeout CSV: {e}")
            return {}
    
    def _write_timeout_data(self, timeout_data: Dict[str, Dict]):
        """Write timeout data to CSV"""
        try:
            with open(self.timeout_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.timeout_headers)
                writer.writeheader()
                
                # Sort by consecutive_timeouts (descending) for easier monitoring
                sorted_data = sorted(
                    timeout_data.values(), 
                    key=lambda x: int(x.get('consecutive_timeouts', 0)), 
                    reverse=True
                )
                
                for row_data in sorted_data:
                    writer.writerow(row_data)
                    
            logger.debug(f"Written {len(timeout_data)} timeout entries to CSV")
            
        except Exception as e:
            logger.error(f"Error writing timeout CSV: {e}")

    def _read_alerted_list(self) -> Dict[str, datetime]:
        """Read last WhatsApp alert times from internal tracking"""
        alerted_data = {}
        if not os.path.exists(self.alerted_list_csv_path):
            return alerted_data
        
        try:
            with open(self.alerted_list_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    ip_address = row['ip_address']
                    alerted_data[ip_address] = dict(row)
            
            logger.debug(f"Read {len(alerted_data)} timeout entries from CSV")
            return alerted_data
            
        except Exception as e:
            logger.error(f"Error reading timeout CSV: {e}")
            return {}
    
    def _write_alerted_list(self, alerted_data: Dict[str, Dict]):
        """Write last WhatsApp alert times to internal tracking"""
        try:
            with open(self.alerted_list_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.alerted_list_headers)
                writer.writeheader()
                
                # Write all alerted devices
                for row_data in alerted_data.values():
                    writer.writerow(row_data)
                    
            logger.debug(f"Written {len(alerted_data)} alerted entries to CSV")
            
        except Exception as e:
            logger.error(f"Error writing alerted list CSV: {e}")

    def _should_send_whatsapp_alert(self, ip_address: str, consecutive_timeouts: int, alerted_data: Dict = None) -> bool:
        """
        Check if WhatsApp alert should be sent for this device
        
        Args:
            ip_address: IP address of device
            consecutive_timeouts: Number of consecutive timeouts
            alerted_data: Optional dict of already alerted devices (to avoid re-reading file)
        """
        if not self.whatsapp_enabled:
            logger.debug(f"WhatsApp alerts disabled - no alert for {ip_address}")
            return False

        # Only send alert when reaching threshold for the first time
        # Device must be at or above threshold
        if consecutive_timeouts < self.whatsapp_threshold:
            logger.debug(f"Device {ip_address} has {consecutive_timeouts}x timeouts (threshold: {self.whatsapp_threshold}) - no alert yet")
            return False

        # Cek apakah sudah pernah di-alert sebelumnya
        # Use provided alerted_data to avoid re-reading file
        if alerted_data is None:
            alerted_data = self._read_alerted_list()
        
        if ip_address in alerted_data:
            logger.info(f"🚫 Device {ip_address} ALREADY ALERTED - skipping (timeouts: {consecutive_timeouts}x, threshold: {self.whatsapp_threshold})")
            print(f"      🚫 Device {ip_address} sudah pernah di-alert sebelumnya - TIDAK mengirim lagi")
            return False

        logger.info(f"✅ Device {ip_address} ready for alert (consecutive_timeouts: {consecutive_timeouts}, threshold: {self.whatsapp_threshold})")
        return True
    
    def _send_whatsapp_timeout_alert(self, device_data: Dict) -> bool:
        """
        Send WhatsApp alert for timeout device using Watzap API
        """
        try:
            from app.routes.watzap_routes import get_watzap_service

            watzap_service = get_watzap_service()
            if not watzap_service:
                logger.error("❌ Watzap service not available for timeout alert")
                return False

            ip_address = device_data.get('ip_address', 'Unknown')
            hostname = device_data.get('hostname', 'Unknown')
            device_id = device_data.get('device_id', 'Unknown')
            merk = device_data.get('merk', 'Unknown')
            consecutive_timeouts = device_data.get('consecutive_timeouts', 0)
            first_timeout = device_data.get('first_timeout', 'Unknown')

            try:
                if first_timeout != 'Unknown':
                    first_timeout_dt = datetime.fromisoformat(first_timeout)
                    first_timeout_formatted = first_timeout_dt.strftime('%d-%m-%Y %H:%M:%S')
                else:
                    first_timeout_formatted = first_timeout
            except:
                first_timeout_formatted = first_timeout

            logger.info(f"🔔 Attempting to send Watzap timeout alert for {hostname} ({ip_address})")
            logger.info(f"   Device: {device_id}, Merk: {merk}, Consecutive timeouts: {consecutive_timeouts}")
            
            # Kirim alert menggunakan Watzap
            result = watzap_service.send_timeout_alert(device_data)

            if result.get('status') == 'success':
                logger.info(f"✅ Watzap timeout alert sent successfully for {hostname} ({ip_address})")
                logger.info(f"   Response: {result.get('message', 'No message')}")
                # Tambahkan ke alerted_list.csv
                self._add_to_alerted_list(device_data)
                return True
            else:
                logger.error(f"❌ Failed to send Watzap timeout alert: {result.get('message', 'Unknown error')}")
                logger.error(f"   Full result: {result}")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending Watzap timeout alert: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return False

    def _add_to_alerted_list(self, device_data: Dict):
        """Add device to alerted_list.csv"""
        try:
            alerted_data = self._read_alerted_list()
            ip_address = device_data.get('ip_address')
            if ip_address and ip_address not in alerted_data:
                alerted_data[ip_address] = {
                    'ip_address': ip_address,
                    'hostname': device_data.get('hostname', ''),
                    'device_id': device_data.get('device_id', ''),
                }
                # Write back to CSV
                with open(self.alerted_list_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=self.alerted_list_headers)
                    writer.writeheader()
                    for row in alerted_data.values():
                        writer.writerow(row)
                logger.info(f"Added {ip_address} to alerted_list.csv")
        except Exception as e:
            logger.error(f"Error adding to alerted_list.csv: {e}")
    
    def _send_recovery_notification(self, device_data: Dict) -> bool:
        """
        Send WhatsApp recovery notification when device comes back online
        """
        try:
            from app.routes.watzap_routes import get_watzap_service

            watzap_service = get_watzap_service()
            if not watzap_service:
                logger.error("❌ Watzap service not available for recovery notification")
                return False

            ip_address = device_data.get('ip_address', 'Unknown')
            hostname = device_data.get('hostname', 'Unknown')
            device_id = device_data.get('device_id', 'Unknown')
            consecutive_timeouts = device_data.get('consecutive_timeouts', 0)
            first_timeout = device_data.get('first_timeout', 'Unknown')

            try:
                if first_timeout != 'Unknown':
                    first_timeout_dt = datetime.fromisoformat(first_timeout)
                    first_timeout_formatted = format_indonesian_date(first_timeout_dt)
                else:
                    first_timeout_formatted = first_timeout
            except:
                first_timeout_formatted = first_timeout

            logger.info(f"🔔 Sending recovery notification for {hostname} ({ip_address})")
            logger.info(f"   Device recovered after {consecutive_timeouts}x consecutive timeouts")
            print(f"      📤 Mengirim recovery notification untuk {hostname} ({ip_address})...")
            
            # Format recovery message
            recovery_message = f"""✅ PERANGKAT PULIH KEMBALI ✅

📋 Informasi Perangkat:
• Hostname: {hostname}
• IP Address: {ip_address}

📊 Status:
• Jumlah Timeout: {consecutive_timeouts}x berturut-turut
• Pertama Timeout: {first_timeout_formatted}

Waktu Notifikasi: {format_indonesian_date(datetime.now())} WIB

Pesan ini dikirim otomatis oleh Sistematis Sub Reg Jawa."""

            # Kirim recovery notification
            from app.utils.watzap import WatzapAPI
            watzap = WatzapAPI()
            
            result = watzap.send_message_to_group(watzap.default_group_id, recovery_message)

            if result.get('status') == 'success':
                logger.info(f"✅ Recovery notification sent successfully for {hostname} ({ip_address})")
                print(f"      ✅ Recovery notification berhasil dikirim!")
                return True
            else:
                logger.error(f"❌ Failed to send recovery notification: {result.get('message', 'Unknown error')}")
                print(f"      ❌ Recovery notification GAGAL dikirim!")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending recovery notification: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return False

    def update_timeout_tracking(self, ping_results: List[Dict]):
        """
        Update timeout tracking based on ping results
        Args:
            ping_results: List of ping results from current cycle
        """
        try:
            # Read existing timeout data
            timeout_data = self._read_timeout_data()
            alerted_data = self._read_alerted_list()
            current_time = datetime.now().isoformat()
            
            # Print summary at start
            print(f"\n⏱️  Timeout Tracking Cycle - {datetime.now().strftime('%H:%M:%S')}")
            print(f"   📊 Status: {len(timeout_data)} device timeout, {len(alerted_data)} sudah di-alert")
            
            # Store current timeout IPs for analytics
            current_timeout_ips = set(timeout_data.keys())
            
            processed_ips = set()
            devices_to_alert = []  # Collect devices that need alerts
            recovered_ips = []  # Track recovered devices for incident cleanup
            
            for result in ping_results:
                ip_address = result.get('ip_address')
                ping_success = result.get('ping_success', False)
                
                if not ip_address:
                    continue
                
                # Skip if this IP was already processed in this cycle (prevent duplicates)
                if ip_address in processed_ips:
                    logger.warning(f"⚠️ Duplicate IP {ip_address} in ping_results - skipping to prevent duplicate notifications")
                    continue
                
                processed_ips.add(ip_address)
                
                if ping_success:
                    # Ping successful - remove from timeout tracking if exists
                    if ip_address in timeout_data:
                        # Log recovery
                        consecutive_timeouts = int(timeout_data[ip_address].get('consecutive_timeouts', 0))
                        hostname = timeout_data[ip_address].get('hostname', ip_address)
                        was_alerted = ip_address in alerted_data
                        
                        print(f"   ✅ {hostname} ({ip_address}) pulih setelah {consecutive_timeouts}x timeout")
                        print(f"      🔍 Debug: was_alerted={was_alerted}, threshold={self.whatsapp_threshold}")
                        logger.info(f"Device {hostname} ({ip_address}) recovered after {consecutive_timeouts} consecutive timeouts")
                        logger.info(f"   Recovery check: was_alerted={was_alerted}, timeouts={consecutive_timeouts}, threshold={self.whatsapp_threshold}")
                        
                        # Kirim notifikasi WhatsApp HANYA jika device pernah di-alert DAN mencapai threshold
                        if was_alerted and consecutive_timeouts >= self.whatsapp_threshold:
                            print(f"      📤 Device pernah di-alert DAN ≥{self.whatsapp_threshold}x timeout, mengirim notifikasi recovery...")
                            self._send_recovery_notification(timeout_data[ip_address])
                            
                            # Hapus dari alerted_data setelah kirim recovery notification
                            del alerted_data[ip_address]
                            print(f"      🔄 Device dihapus dari alerted list - BISA mendapat alert lagi jika timeout")
                            logger.info(f"Removed {ip_address} from whatsapp_alerted_list.csv (recovery notification sent)")
                        elif was_alerted and consecutive_timeouts < self.whatsapp_threshold:
                            # Device di alerted list tapi timeout saat ini belum sampai threshold
                            # INI SEHARUSNYA TIDAK TERJADI! Device tidak boleh ada di alerted_list jika belum 20x
                            print(f"      ⚠️ WARNING: Device di alerted_list tapi hanya {consecutive_timeouts}x timeout (threshold={self.whatsapp_threshold})")
                            print(f"      🔄 Menghapus dari alerted list (data inconsistent)")
                            logger.warning(f"INCONSISTENT STATE: {ip_address} in alerted_list with only {consecutive_timeouts}x timeouts (threshold={self.whatsapp_threshold})")
                            del alerted_data[ip_address]
                        elif was_alerted:
                            # Fallback - should not reach here
                            del alerted_data[ip_address]
                            print(f"      🔄 Device dihapus dari alerted list (unknown reason)")
                            logger.info(f"Removed {ip_address} from alerted list (fallback)")
                        else:
                            print(f"      ℹ️ Device pulih tanpa recovery notification (belum pernah di-alert)")
                        
                        # Track recovered IP for incident cleanup
                        recovered_ips.append(ip_address)
                        
                        # Hapus dari timeout_data
                        del timeout_data[ip_address]
                        logger.debug(f"Removed {ip_address} from timeout tracking (ping successful)")
                else:
                    # Ping failed - add or update timeout tracking
                    if ip_address in timeout_data:
                        # Update existing entry
                        current_count = int(timeout_data[ip_address].get('consecutive_timeouts', 0))
                        new_count = current_count + 1
                        hostname = timeout_data[ip_address].get('hostname', ip_address)
                        
                        timeout_data[ip_address]['consecutive_timeouts'] = str(new_count)
                        timeout_data[ip_address]['last_timeout'] = current_time
                        timeout_data[ip_address]['last_updated'] = current_time
                        
                        # Log timeout progression
                        is_alerted = ip_address in alerted_data
                        logger.debug(f"Device {hostname} ({ip_address}) timeout count: {new_count}x (alerted: {is_alerted})")
                        
                        # Check if WhatsApp alert should be sent (pass alerted_data to avoid re-reading file)
                        if self._should_send_whatsapp_alert(ip_address, new_count, alerted_data):
                            logger.warning(f"🔔 Adding {hostname} ({ip_address}) to alert queue (timeouts: {new_count}x)")
                            devices_to_alert.append(timeout_data[ip_address])
                    else:
                        # Add new entry
                        timeout_data[ip_address] = {
                            'ip_address': ip_address,
                            'hostname': result.get('hostname', ''),
                            'device_id': str(result.get('device_id', '')),
                            'merk': result.get('merk', ''),
                            'os': result.get('os', ''),
                            'kondisi': result.get('kondisi', ''),
                            'consecutive_timeouts': '1',
                            'first_timeout': current_time,
                            'last_timeout': current_time,
                            'last_updated': current_time,
                        }
                        logger.debug(f"Added {ip_address} to timeout tracking (first timeout)")
            
            # Always send alerts in BATCH mode (even for single device)
            if devices_to_alert:
                print("\n" + "="*80)
                print(f"🚨 WHATSAPP ALERT TRIGGER! 🚨")
                print("="*80)
                print(f"📊 {len(devices_to_alert)} device(s) mencapai threshold {self.whatsapp_threshold}x timeout")
                print(f"📤 Mengirim pesan WhatsApp ke group dan admin...")
                print("")
                
                logger.warning(f"🚨 WHATSAPP ALERT: Sending BATCH alert for {len(devices_to_alert)} device(s)")
                
                # Log device list
                print("📋 Daftar device yang akan di-alert:")
                for idx, dev in enumerate(devices_to_alert, 1):
                    print(f"   {idx}. {dev.get('hostname')} ({dev.get('ip_address')}) - {dev.get('consecutive_timeouts')}x timeout")
                    logger.info(f"   Alert device {idx}: {dev.get('hostname')} ({dev.get('ip_address')}) - {dev.get('consecutive_timeouts')}x")
                
                print("")
                print("📲 Mengirim ke:")
                print("   • WhatsApp Group: 120363403677027364@g.us")
                print("")
                
                # Always use batch mode for consistent formatting
                if self._send_batch_timeout_alert(devices_to_alert):
                    # Add all devices to alerted list (update both file and in-memory data)
                    for device in devices_to_alert:
                        ip = device.get('ip_address')
                        if ip:
                            # Update in-memory alerted_data
                            alerted_data[ip] = {
                                'ip_address': ip,
                                'hostname': device.get('hostname', ''),
                                'device_id': device.get('device_id', ''),
                            }
                            logger.info(f"Added {ip} to in-memory alerted_data")
                    print("✅ WHATSAPP ALERT BERHASIL DIKIRIM!")
                    print("="*80 + "\n")
                    logger.warning(f"✅ BATCH WhatsApp TIMEOUT ALERT sent successfully for {len(devices_to_alert)} device(s)")
                else:
                    print("❌ WHATSAPP ALERT GAGAL DIKIRIM!")
                    print("="*80 + "\n")
                    logger.error(f"❌ Failed to send BATCH WhatsApp TIMEOUT ALERT")
            else:
                logger.debug(f"No devices reached alert threshold ({self.whatsapp_threshold}x) in this cycle")
            
            # Remove entries for IPs that are no longer being monitored
            stale_ips = set(timeout_data.keys()) - processed_ips
            for stale_ip in stale_ips:
                del timeout_data[stale_ip]
                logger.debug(f"Removed stale IP {stale_ip} from timeout tracking")
            
            # JANGAN hapus dari alerted_data di sini!
            # Device hanya dihapus dari alerted_data jika:
            # 1. Ping SUCCESS (recovery) - ditangani di baris 340-369
            # 2. Device tidak ada lagi di inventaris (handled by stale_ips)
            
            # Write updated alerted_data back to CSV (includes newly alerted devices)
            with open(self.alerted_list_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.alerted_list_headers)
                writer.writeheader()
                for row in alerted_data.values():
                    writer.writerow(row)
            logger.debug(f"Written {len(alerted_data)} alerted devices to CSV")
            
            # Write updated data back to CSV
            self._write_timeout_data(timeout_data)
            
            # Check and create incidents for devices that have been down for > 1 hour
            if self.incident_manager and timeout_data:
                created_incidents = self.incident_manager.check_and_create_incidents(timeout_data)
                if created_incidents:
                    logger.warning(f"📋 Created {len(created_incidents)} new incidents for prolonged timeouts")
            
            # Cleanup incident tracking for recovered devices
            if self.incident_manager and recovered_ips:
                self.incident_manager.cleanup_resolved_incidents(recovered_ips)
            
            # Record analytics snapshot
            updated_timeout_ips = set(timeout_data.keys())
            self.analytics.record_timeout_snapshot(
                timeout_data=timeout_data,
                previous_timeout_ips=self.previous_timeout_ips
            )
            
            # Update previous timeout IPs for next cycle
            self.previous_timeout_ips = updated_timeout_ips
            
            # Log summary
            total_timeout_devices = len(timeout_data)
            total_alerted = len(alerted_data)
            
            if total_timeout_devices > 0:
                max_timeouts = max(int(entry['consecutive_timeouts']) for entry in timeout_data.values())
                
                # Count devices near threshold
                near_threshold = sum(1 for entry in timeout_data.values() 
                                    if int(entry.get('consecutive_timeouts', 0)) >= (self.whatsapp_threshold - 5))
                at_threshold = sum(1 for entry in timeout_data.values() 
                                  if int(entry.get('consecutive_timeouts', 0)) >= self.whatsapp_threshold)
                
                print(f"   📊 Ringkasan: {total_timeout_devices} device timeout (max: {max_timeouts}x)")
                print(f"   📊 Mendekati threshold (≥{self.whatsapp_threshold-5}x): {near_threshold} devices")
                print(f"   📊 Mencapai threshold (≥{self.whatsapp_threshold}x): {at_threshold} devices")
                print(f"   📊 Sudah di-alert: {total_alerted} devices")
                
                logger.info(f"📊 Timeout Summary: {total_timeout_devices} devices timing out, max: {max_timeouts}x")
                logger.info(f"   • Near threshold (≥{self.whatsapp_threshold-5}x): {near_threshold} devices")
                logger.info(f"   • At/above threshold (≥{self.whatsapp_threshold}x): {at_threshold} devices")
                logger.info(f"   • Already alerted: {total_alerted} devices")
                
                if at_threshold > 0 and len(devices_to_alert) == 0:
                    print(f"   ℹ️  Catatan: {at_threshold} devices di threshold sudah pernah di-alert")
                    logger.warning(f"   ⚠️ Note: {at_threshold} devices at threshold already alerted before")
            else:
                print(f"   ✅ Semua device normal (tidak ada timeout)")
                logger.info("Timeout tracking updated: No devices currently timing out")
                
        except Exception as e:
            logger.error(f"Error updating timeout tracking: {e}")
    
    def _send_batch_timeout_alert(self, devices: List[Dict]) -> bool:
        """
        Send batch timeout alert for multiple devices in one message
        
        Args:
            devices: List of device data that need alerts
            
        Returns:
            bool: True if successful
        """
        try:
            from app.routes.watzap_routes import get_watzap_service

            watzap_service = get_watzap_service()
            if not watzap_service:
                logger.error("❌ Watzap service not available for batch timeout alert")
                return False

            print(f"   🔔 Memformat pesan batch untuk {len(devices)} devices...")
            logger.info(f"🔔 Preparing BATCH alert for {len(devices)} devices")
            
            # Format pesan batch - format sederhana
            alert_message = f"""🚨 PERINGATAN TIMEOUT {len(devices)} PERANGKAT🚨 

📋 Daftar Perangkat Bermasalah:
"""
            
            # Add each device to the message
            for idx, device in enumerate(devices, 1):
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
            
            print(f"   📝 Pesan batch dibuat ({len(alert_message)} karakter)")
            logger.info(f"📤 Sending batch alert message ({len(alert_message)} chars)")
            
            # Kirim ke group dan personal menggunakan helper function
            from app.utils.watzap import WatzapAPI
            watzap = WatzapAPI()
            
            print(f"   🌐 Mengirim ke WhatsApp Group...")
            # Kirim HANYA ke group (tidak ke personal untuk menghindari duplikasi)
            # Admin sudah menerima pesan dari group jika dia anggota group
            group_result = watzap.send_message_to_group(watzap.default_group_id, alert_message)
            
            if group_result.get('status') == 'success':
                print(f"   ✅ Terkirim ke WhatsApp Group")
                logger.info(f"✅ Batch alert sent to group successfully")
            else:
                print(f"   ❌ Gagal kirim ke WhatsApp Group: {group_result.get('message')}")
                logger.error(f"❌ Failed to send to group: {group_result}")
            
            # TIDAK mengirim ke personal admin untuk menghindari duplikasi pesan
            # (Admin sudah dapat notifikasi dari group message)
            
            success = group_result.get('status') == 'success'
            
            if success:
                print(f"   ✅ Batch alert berhasil dikirim")
                logger.info(f"✅ BATCH alert sent successfully for {len(devices)} devices")
                return True
            else:
                print(f"   ❌ Batch alert gagal dikirim ke semua tujuan")
                logger.error(f"❌ Failed to send batch alert to any recipient")
                return False

        except Exception as e:
            logger.error(f"❌ Error sending batch timeout alert: {e}")
            import traceback
            logger.error(f"   Traceback: {traceback.format_exc()}")
            return False
    
    def get_timeout_summary(self) -> Dict:
        """Get summary statistics of timeout tracking"""
        try:
            timeout_data = self._read_timeout_data()
            
            if not timeout_data:
                return {
                    'total_timeout_devices': 0,
                    'max_consecutive_timeouts': 0,
                    'average_consecutive_timeouts': 0,
                    'devices_with_high_timeouts': 0  # > 10 consecutive
                }
            
            consecutive_counts = [int(entry['consecutive_timeouts']) for entry in timeout_data.values()]
            high_timeout_devices = sum(1 for count in consecutive_counts if count > 10)
            
            return {
                'total_timeout_devices': len(timeout_data),
                'max_consecutive_timeouts': max(consecutive_counts),
                'average_consecutive_timeouts': round(sum(consecutive_counts) / len(consecutive_counts), 2),
                'devices_with_high_timeouts': high_timeout_devices,
                'timeout_csv_path': self.timeout_csv_path
            }
            
        except Exception as e:
            logger.error(f"Error getting timeout summary: {e}")
            return {}
    
    def get_timeout_devices(self, min_consecutive: int = 1) -> List[Dict]:
        """
        Get list of devices with timeout count >= min_consecutive
        Args:
            min_consecutive: Minimum consecutive timeouts to include
        """
        try:
            timeout_data = self._read_timeout_data()
            
            filtered_devices = []
            for entry in timeout_data.values():
                consecutive_count = int(entry.get('consecutive_timeouts', 0))
                if consecutive_count >= min_consecutive:
                    filtered_devices.append(entry)
            
            # Sort by consecutive timeouts (descending)
            filtered_devices.sort(key=lambda x: int(x['consecutive_timeouts']), reverse=True)
            
            return filtered_devices
            
        except Exception as e:
            logger.error(f"Error getting timeout devices: {e}")
            return []
    
    def cleanup_timeout_csv(self):
        """Remove timeout CSV file (for cleanup/reset)"""
        try:
            if os.path.exists(self.timeout_csv_path):
                os.remove(self.timeout_csv_path)
                logger.info("Timeout CSV file removed")
                self._initialize_timeout_csv()
        except Exception as e:
            logger.error(f"Error cleaning up timeout CSV: {e}")
    
    def get_critical_timeouts(self, threshold: int = 5) -> List[Dict]:
        """
        Get devices with consecutive timeouts >= threshold
        Args:
            threshold: Minimum consecutive timeouts to be considered critical
        """
        return self.get_timeout_devices(min_consecutive=threshold)
    
    def export_timeout_report(self) -> Dict:
        """Export comprehensive timeout report"""
        try:
            timeout_data = self._read_timeout_data()
            summary = self.get_timeout_summary()
            critical_devices = self.get_critical_timeouts(threshold=5)
            
            return {
                'summary': summary,
                'critical_devices': critical_devices,
                'all_timeout_devices': list(timeout_data.values()),
                'report_generated': datetime.now().isoformat(),
                'csv_file': self.timeout_csv_path
            }
            
        except Exception as e:
            logger.error(f"Error exporting timeout report: {e}")
            return {}
    
    def get_whatsapp_alert_summary(self) -> Dict:
        """Get summary of WhatsApp alerts sent"""
        try:
            timeout_data = self._read_timeout_data()
            alerted_data = self._read_alerted_list()
            
            total_alerts_sent = 0
            devices_with_alerts = []
            
            for entry in alerted_data.values():
                if entry.get('ip_address') == 'True':
                    total_alerts_sent += 1
                    devices_with_alerts.append({
                        'ip_address': entry['ip_address'],
                        'hostname': entry['hostname'],
                        'consecutive_timeouts': entry['consecutive_timeouts'],
                        'last_whatsapp_alert': entry.get('last_whatsapp_alert', '')
                    })
            
            return {
                'whatsapp_alerts_enabled': self.whatsapp_enabled,
                'whatsapp_threshold': self.whatsapp_threshold,
                'cooldown_minutes': self.whatsapp_cooldown_minutes,
                'total_alerts_sent': total_alerts_sent,
                'devices_with_alerts': devices_with_alerts
            }
            
        except Exception as e:
            logger.error(f"Error getting WhatsApp alert summary: {e}")
            return {}
