import os
import csv
import logging
import threading
from datetime import datetime, timedelta
from typing import List, Dict, Optional

try:
    import fcntl  # Unix-based file locking (Linux/CentOS)
    HAS_FCNTL = True
except ImportError:
    HAS_FCNTL = False  # Windows doesn't have fcntl

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
        
        # Thread locks for file operations (prevent race conditions)
        self._timeout_file_lock = threading.Lock()
        self._alerted_file_lock = threading.Lock()
        self._update_tracking_lock = threading.Lock()  # CRITICAL: Prevent concurrent updates

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
    
    def _lock_file(self, file_obj):
        """Lock file for exclusive access (Unix only)"""
        if HAS_FCNTL:
            try:
                fcntl.flock(file_obj.fileno(), fcntl.LOCK_EX)
            except Exception as e:
                logger.warning(f"Could not acquire file lock: {e}")
    
    def _unlock_file(self, file_obj):
        """Unlock file (Unix only)"""
        if HAS_FCNTL:
            try:
                fcntl.flock(file_obj.fileno(), fcntl.LOCK_UN)
            except Exception as e:
                logger.warning(f"Could not release file lock: {e}")
    
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
        """Read existing timeout data from CSV with file locking"""
        timeout_data = {}
        
        if not os.path.exists(self.timeout_csv_path):
            return timeout_data
        
        with self._timeout_file_lock:  # Thread lock
            try:
                # Check file size before reading - if too small, might be mid-write
                file_size = os.path.getsize(self.timeout_csv_path)
                if file_size < 100:  # Less than header size
                    logger.warning(f"⚠️  CSV file too small ({file_size} bytes) - might be corrupted or mid-write")
                    # Try to wait a moment and retry
                    import time
                    time.sleep(0.05)  # 50ms
                    file_size = os.path.getsize(self.timeout_csv_path)
                    if file_size < 100:
                        logger.error(f"❌ CSV still too small after retry - returning empty")
                        return {}
                
                with open(self.timeout_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                    self._lock_file(csvfile)  # File lock (Unix)
                    try:
                        reader = csv.DictReader(csvfile)
                        row_count = 0
                        for row in reader:
                            ip_address = row.get('ip_address')
                            if ip_address:  # Validate row has IP
                                timeout_data[ip_address] = dict(row)
                                row_count += 1
                        
                        # Validation: If file is large but we read 0 rows, something is wrong
                        if file_size > 200 and row_count == 0:
                            logger.error(f"❌ File size {file_size} bytes but read 0 rows - CSV might be corrupted!")
                            
                    finally:
                        self._unlock_file(csvfile)
                
                logger.debug(f"Read {len(timeout_data)} timeout entries from CSV (file size: {file_size} bytes)")
                return timeout_data
                
            except Exception as e:
                logger.error(f"Error reading timeout CSV: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return {}
    
    def _write_timeout_data(self, timeout_data: Dict[str, Dict]):
        """Write timeout data to CSV with file locking and atomic write"""
        with self._timeout_file_lock:  # Thread lock
            # CRITICAL: Also lock the ACTUAL CSV file during entire operation
            # This prevents other processes from reading while we're updating
            lock_file = None
            try:
                # CRITICAL SAFETY CHECK: Don't clear non-empty CSV!
                # This prevents race condition where empty data overwrites valid data
                if not timeout_data and os.path.exists(self.timeout_csv_path):
                    try:
                        current_size = os.path.getsize(self.timeout_csv_path)
                        # If CSV has content (> 200 bytes = header + at least 1 row)
                        if current_size > 200:
                            logger.error("🚨🚨🚨 PREVENTED DATA LOSS! 🚨🚨🚨")
                            logger.error(f"   Refusing to clear non-empty CSV (size: {current_size} bytes)")
                            logger.error(f"   timeout_data is EMPTY but CSV has content!")
                            logger.error(f"   This is likely a RACE CONDITION or BUG!")
                            logger.error(f"   CSV NOT MODIFIED - preserving existing data")
                            return  # ABORT write - preserve existing data!
                    except Exception as check_err:
                        logger.error(f"Error checking CSV size: {check_err}")
                
                # CRITICAL FIX: Lock the actual CSV file BEFORE starting write operation
                # This prevents other processes from reading stale data during update
                if os.path.exists(self.timeout_csv_path):
                    lock_file = open(self.timeout_csv_path, 'r+')
                    self._lock_file(lock_file)
                    logger.debug("🔒 Locked actual CSV file for write operation")
                
                # Atomic write: write to temp file first, then rename
                temp_path = self.timeout_csv_path + '.tmp'
                
                # Log warning if writing empty data
                if not timeout_data:
                    logger.warning(f"⚠️  Writing EMPTY timeout_data to CSV - CSV will be cleared!")
                    logger.warning(f"   If this happens frequently, it indicates a BUG!")
                
                with open(temp_path, 'w', newline='', encoding='utf-8') as csvfile:
                    self._lock_file(csvfile)  # File lock (Unix)
                    try:
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
                        
                        # Force flush to disk
                        csvfile.flush()
                        os.fsync(csvfile.fileno())
                    finally:
                        self._unlock_file(csvfile)
                
                # File is closed here (exited 'with' block)
                # Now it's safe to do atomic rename
                
                # Atomic rename (atomic operation on Unix/Linux)
                os.replace(temp_path, self.timeout_csv_path)
                
                # CRITICAL: Ensure file system sync (especially important on CentOS)
                try:
                    import time
                    time.sleep(0.01)  # 10ms delay for FS sync
                except:
                    pass
                
                logger.debug(f"Written {len(timeout_data)} timeout entries to CSV (atomic)")
                
                # VALIDATION: Verify write succeeded
                if os.path.exists(self.timeout_csv_path):
                    actual_size = os.path.getsize(self.timeout_csv_path)
                    expected_min_size = 150 + (len(timeout_data) * 50)  # header + data rows
                    if len(timeout_data) > 0 and actual_size < expected_min_size:
                        logger.error(f"⚠️  Write validation failed! File size {actual_size} < expected {expected_min_size}")
                    else:
                        logger.debug(f"✅ Write validated: {actual_size} bytes for {len(timeout_data)} entries")
                
            except Exception as e:
                logger.error(f"Error writing timeout CSV: {e}")
                # Cleanup temp file if exists
                temp_path = self.timeout_csv_path + '.tmp'
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass
            finally:
                # CRITICAL: Release lock on actual CSV file
                if lock_file:
                    try:
                        self._unlock_file(lock_file)
                        lock_file.close()
                        logger.debug("🔓 Released lock on actual CSV file")
                    except:
                        pass

    def _read_alerted_list(self) -> Dict[str, datetime]:
        """Read last WhatsApp alert times from internal tracking with file locking"""
        alerted_data = {}
        if not os.path.exists(self.alerted_list_csv_path):
            return alerted_data
        
        with self._alerted_file_lock:  # Thread lock
            try:
                with open(self.alerted_list_csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                    self._lock_file(csvfile)  # File lock (Unix)
                    try:
                        reader = csv.DictReader(csvfile)
                        for row in reader:
                            ip_address = row['ip_address']
                            alerted_data[ip_address] = dict(row)
                    finally:
                        self._unlock_file(csvfile)
                
                logger.debug(f"Read {len(alerted_data)} timeout entries from CSV")
                return alerted_data
                
            except Exception as e:
                logger.error(f"Error reading timeout CSV: {e}")
                return {}
    
    def _write_alerted_list(self, alerted_data: Dict[str, Dict]):
        """Write last WhatsApp alert times to internal tracking with file locking"""
        with self._alerted_file_lock:  # Thread lock
            try:
                # Atomic write: write to temp file first, then rename
                temp_path = self.alerted_list_csv_path + '.tmp'
                
                with open(temp_path, 'w', newline='', encoding='utf-8') as csvfile:
                    self._lock_file(csvfile)  # File lock (Unix)
                    try:
                        writer = csv.DictWriter(csvfile, fieldnames=self.alerted_list_headers)
                        writer.writeheader()
                        
                        # Write all alerted devices
                        for row_data in alerted_data.values():
                            writer.writerow(row_data)
                    finally:
                        self._unlock_file(csvfile)
                
                # Atomic rename
                os.replace(temp_path, self.alerted_list_csv_path)
                logger.debug(f"Written {len(alerted_data)} alerted entries to CSV (atomic)")
                
            except Exception as e:
                logger.error(f"Error writing alerted list CSV: {e}")
                # Cleanup temp file if exists
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass

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
        """Add device to alerted_list.csv with file locking"""
        try:
            alerted_data = self._read_alerted_list()
            ip_address = device_data.get('ip_address')
            if ip_address and ip_address not in alerted_data:
                alerted_data[ip_address] = {
                    'ip_address': ip_address,
                    'hostname': device_data.get('hostname', ''),
                    'device_id': device_data.get('device_id', ''),
                }
                # Write back to CSV using atomic write method
                self._write_alerted_list(alerted_data)
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
        # CRITICAL: Acquire lock to prevent concurrent execution
        # This prevents race condition where multiple threads modify CSV simultaneously
        with self._update_tracking_lock:
            logger.info(f"🔒 Acquired update_tracking lock - processing {len(ping_results)} ping results")
            try:
                # Read existing timeout data
                timeout_data = self._read_timeout_data()
                alerted_data = self._read_alerted_list()
                current_time = datetime.now().isoformat()
                
                # CHECKPOINT: Store initial count for validation later
                initial_timeout_count = len(timeout_data)
                
                # Check if CSV file exists and has content but read returned empty
                if os.path.exists(self.timeout_csv_path):
                    actual_file_size = os.path.getsize(self.timeout_csv_path)
                    if actual_file_size > 200 and len(timeout_data) == 0:
                        logger.error(f"🚨 CSV FILE CORRUPTION DETECTED!")
                        logger.error(f"   File exists: {self.timeout_csv_path}")
                        logger.error(f"   File size: {actual_file_size} bytes (should have data)")
                        logger.error(f"   But _read_timeout_data() returned: {len(timeout_data)} entries")
                        logger.error(f"   This will cause ALL counters to reset to 1!")
            
                # DEBUG: Log what was read from CSV
                logger.warning(f"📖 READ FROM CSV: {len(timeout_data)} timeout entries, {len(alerted_data)} alerted")
                if timeout_data:
                    logger.warning(f"📋 Devices currently in timeout tracking:")
                    for ip, dev in timeout_data.items():
                        logger.warning(f"   • {dev.get('hostname')} ({ip}): {dev.get('consecutive_timeouts')}x")
                else:
                    logger.warning(f"   ℹ️  CSV is EMPTY - no timeout devices yet")
            
                # Print summary at start
                print(f"\n⏱️  Timeout Tracking Cycle - {datetime.now().strftime('%H:%M:%S')}")
                print(f"   📊 Status: {len(timeout_data)} device timeout, {len(alerted_data)} sudah di-alert")
                print(f"   📊 ping_results contains: {len(ping_results)} devices")
            
                # Store current timeout IPs for analytics
                current_timeout_ips = set(timeout_data.keys())
            
                processed_ips = set()
                devices_to_alert = []  # Collect devices that need alerts
                recovered_ips = []  # Track recovered devices for incident cleanup
            
                # CRITICAL FIX: Track which IPs are in current ping_results
                # Devices NOT in ping_results should stay in timeout_data (don't remove them!)
                current_ping_ips = set()
            
                # First pass: collect all IPs in this ping cycle
                for result in ping_results:
                    ip = result.get('ip_address')
                    if ip:
                        current_ping_ips.add(ip)
            
                logger.info(f"🎯 Current ping cycle contains {len(current_ping_ips)} IPs")
                if current_ping_ips and len(current_ping_ips) <= 20:
                    logger.info(f"   IPs being pinged this cycle: {', '.join(sorted(current_ping_ips))}")
                elif current_ping_ips:
                    logger.info(f"   IPs being pinged this cycle: {', '.join(sorted(list(current_ping_ips)[:20]))}... (showing first 20)")
            
                # Second pass: process ping results
                for result in ping_results:
                    ip_address = result.get('ip_address')
                    ping_success = result.get('ping_success', False)
                
                    if not ip_address:
                        continue
                
                    # Skip if this IP was already processed in this cycle (prevent duplicates)
                    if ip_address in processed_ips:
                        logger.error(f"🚨 DUPLICATE IP DETECTED: {ip_address} already processed in this cycle!")
                        logger.error(f"   Previous status: {'SUCCESS' if ip_address not in timeout_data else 'TIMEOUT'}")
                        logger.error(f"   Current status: {'SUCCESS' if ping_success else 'TIMEOUT'}")
                        logger.error(f"   This could cause counter reset! Skipping duplicate.")
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
                            logger.warning(f"🗑️  DELETED: {hostname} ({ip_address}) removed from timeout_data (ping successful)")
                            logger.warning(f"   Reason: Ping SUCCESS - device recovered")
                    else:
                        # Ping failed - add or update timeout tracking
                        if ip_address in timeout_data:
                            # Update existing entry
                            current_count = int(timeout_data[ip_address].get('consecutive_timeouts', 0))
                            new_count = current_count + 1
                            hostname = timeout_data[ip_address].get('hostname', ip_address)
                        
                            # DEBUG: Log before update
                            logger.warning(f"📈 INCREMENT: {hostname} ({ip_address}) {current_count}x → {new_count}x")
                            logger.warning(f"   Device WAS in timeout_data, incrementing counter")
                        
                            timeout_data[ip_address]['consecutive_timeouts'] = str(new_count)
                            timeout_data[ip_address]['last_timeout'] = current_time
                            timeout_data[ip_address]['last_updated'] = current_time
                        
                            # Log timeout progression
                            is_alerted = ip_address in alerted_data
                            logger.info(f"Device {hostname} ({ip_address}) timeout count: {new_count}x (alerted: {is_alerted})")
                        
                            # Check if WhatsApp alert should be sent (pass alerted_data to avoid re-reading file)
                            if self._should_send_whatsapp_alert(ip_address, new_count, alerted_data):
                                logger.warning(f"🔔 Adding {hostname} ({ip_address}) to alert queue (timeouts: {new_count}x)")
                                devices_to_alert.append(timeout_data[ip_address])
                        else:
                            # Add new entry
                            hostname = result.get('hostname', ip_address)
                            logger.warning(f"🆕 NEW DEVICE: {hostname} ({ip_address}) - starting at 1x")
                            logger.warning(f"   Device NOT in timeout_data, adding as new")
                            logger.warning(f"   timeout_data keys: {list(timeout_data.keys())[:10]}")
                        
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
                            logger.info(f"Added {ip_address} to timeout tracking (first timeout)")
            
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
            
                # CHECKPOINT: Verify data integrity before preservation logic
                logger.info(f"🔍 CHECKPOINT: Before preservation - {len(timeout_data)} devices in timeout_data")
            
                # CRITICAL: Keep devices that were NOT in this ping cycle
                # These devices are still in timeout state but weren't pinged in this cycle
                # DO NOT remove them - they must stay until they recover (ping success)
                devices_not_in_current_ping = set(timeout_data.keys()) - current_ping_ips
            
                if devices_not_in_current_ping:
                    logger.warning(f"🔄 PRESERVING {len(devices_not_in_current_ping)} devices NOT in current ping cycle:")
                    for ip in devices_not_in_current_ping:
                        dev = timeout_data.get(ip, {})
                        hostname = dev.get('hostname', ip)
                        count = dev.get('consecutive_timeouts', '0')
                        logger.warning(f"   • PRESERVE: {hostname} ({ip}): {count}x - NOT pinged this cycle, KEEPING in tracking")
                else:
                    logger.info(f"ℹ️  All timeout devices were included in this ping cycle")
            
                # CHECKPOINT: Verify no data loss after preservation
                logger.info(f"🔍 CHECKPOINT: After preservation - {len(timeout_data)} devices in timeout_data")
                if initial_timeout_count > 0 and len(timeout_data) < initial_timeout_count:
                    lost_count = initial_timeout_count - len(timeout_data)
                    logger.warning(f"⚠️  Lost {lost_count} devices during processing!")
                    logger.warning(f"   Started: {initial_timeout_count}, Ended: {len(timeout_data)}")
                    logger.warning(f"   Recovered: {len(recovered_ips)} devices")
                    expected_remaining = initial_timeout_count - len(recovered_ips)
                    if len(timeout_data) != expected_remaining:
                        logger.error(f"❌ Data loss detected! Expected {expected_remaining} but got {len(timeout_data)}")
            
                # VALIDATION: Ensure devices not in current ping are NOT removed
                # This is the MOST CRITICAL part - devices should stay until ping SUCCESS
                for ip in devices_not_in_current_ping:
                    if ip not in timeout_data:
                        logger.error(f"❌ BUG DETECTED! Device {ip} was removed but should be preserved!")
                        logger.error(f"   This is the root cause of counter reset issue!")
            
                # Only remove devices when:
                # 1. Device recovers (ping success) - handled above in the loop
                # 2. Device permanently removed from inventory (not handled here)
            
                # JANGAN hapus dari alerted_data di sini!
                # Device hanya dihapus dari alerted_data jika:
                # 1. Ping SUCCESS (recovery) - ditangani di baris 340-369
                # 2. Device tidak ada lagi di inventaris (handled by stale_ips)
            
                # Write updated alerted_data back to CSV (includes newly alerted devices)
                self._write_alerted_list(alerted_data)
                logger.debug(f"Updated {len(alerted_data)} alerted devices in CSV")
            
                # DEBUG: Log COMPLETE data before writing to CSV
                logger.info(f"💾 Preparing to write {len(timeout_data)} timeout entries to CSV")
            
                # CRITICAL VALIDATION CHECKPOINT
                # If we read data earlier but now it's empty, something is WRONG!
                if initial_timeout_count > 0 and len(timeout_data) == 0:
                    logger.error(f"🚨🚨🚨 CRITICAL BUG DETECTED! 🚨🚨🚨")
                    logger.error(f"   Started with {initial_timeout_count} timeout entries")
                    logger.error(f"   Now have {len(timeout_data)} entries (EMPTY!)")
                    logger.error(f"   All timeout data was LOST during processing!")
                    logger.error(f"   Ping results count: {len(ping_results)}")
                    logger.error(f"   This will cause counter reset bug!")
                    logger.error(f"   Stack trace point: Before _write_timeout_data()")
            
                if timeout_data:
                    logger.info(f"📋 Complete list of {len(timeout_data)} devices to be written:")
                    for ip, dev in timeout_data.items():
                        logger.info(f"   • {dev.get('hostname')} ({ip}): {dev.get('consecutive_timeouts')}x")
                else:
                    logger.warning(f"⚠️  timeout_data is EMPTY - CSV will be cleared!")
                    logger.warning(f"   If this happens repeatedly, it's the BUG causing counter resets!")
            
                # Write updated data back to CSV
                self._write_timeout_data(timeout_data)
                logger.info(f"✅ CSV write completed - {len(timeout_data)} entries written")
            
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
            finally:
                logger.info(f"🔓 Released update_tracking lock")
    
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
