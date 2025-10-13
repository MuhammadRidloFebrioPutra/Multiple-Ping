import os
import csv
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class TimeoutTracker:
    """
    Class untuk mengelola tracking timeout berturut-turut per IP address
    """
    
    def __init__(self, config):
        self.config = config
        self.timeout_dir = getattr(config, 'CSV_OUTPUT_DIR', 'ping_results')
        self.timeout_filename = 'timeout_tracking.csv'
        self.timeout_csv_path = os.path.join(self.timeout_dir, self.timeout_filename)
        self.alerted_list_filename = 'whatsapp_alerted_list.csv'
        self.alerted_list_csv_path = os.path.join(self.timeout_dir, self.alerted_list_filename)

        # WhatsApp Alert Configuration
        self.whatsapp_enabled = getattr(config, 'ENABLE_WHATSAPP_TIMEOUT_ALERTS', True)
        self.whatsapp_threshold = getattr(config, 'WHATSAPP_TIMEOUT_THRESHOLD', 20)
        self.whatsapp_cooldown_minutes = getattr(config, 'WHATSAPP_COOLDOWN_MINUTES', 60)
        
        
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
                writer = csv.DictWriter(csvfile, fieldnames=self.timeout_headers)
                writer.writeheader()
                
                # Sort by consecutive_timeouts (descending) for easier monitoring
                sorted_data = sorted(
                    alerted_data.values(), 
                    key=lambda x: int(x.get('consecutive_timeouts', 0)), 
                    reverse=True
                )
                
                for row_data in sorted_data:
                    writer.writerow(row_data)
                    
            logger.debug(f"Written {len(alerted_data)} timeout entries to CSV")
            
        except Exception as e:
            logger.error(f"Error writing timeout CSV: {e}")

    def _should_send_whatsapp_alert(self, ip_address: str, consecutive_timeouts: int) -> bool:
        """
        Check if WhatsApp alert should be sent for this device
        """
        if not self.whatsapp_enabled:
            return False

        # Only send alert at exact threshold (20th timeout)
        if consecutive_timeouts != self.whatsapp_threshold:
            return False

        # Cek apakah sudah pernah di-alert sebelumnya
        alerted_data = self._read_alerted_list()
        if ip_address in alerted_data:
            logger.info(f"WhatsApp alert for {ip_address} already sent before (in alerted_list.csv)")
            return False

        return True
    
    def _send_whatsapp_timeout_alert(self, device_data: Dict) -> bool:
        """
        Send WhatsApp alert for timeout device
        """
        try:
            from app.routes.whatsapp_routes import get_whatsapp_service

            whatsapp_service = get_whatsapp_service()
            if not whatsapp_service:
                logger.error("WhatsApp service not available for timeout alert")
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

            alert_id = f"TIMEOUT-{device_id}-{ip_address}"

            result = whatsapp_service.send_alert(alert_id)

            if result.get('status') == 'success':
                logger.info(f"WhatsApp timeout alert sent successfully for {hostname} ({ip_address})")
                # Tambahkan ke alerted_list.csv
                self._add_to_alerted_list(device_data)
                return True
            else:
                logger.error(f"Failed to send WhatsApp timeout alert: {result.get('message', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"Error sending WhatsApp timeout alert: {e}")
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
            
            # Store current timeout IPs for analytics
            current_timeout_ips = set(timeout_data.keys())
            
            processed_ips = set()
            whatsapp_alerts_sent = []
            
            for result in ping_results:
                ip_address = result.get('ip_address')
                ping_success = result.get('ping_success', False)
                
                if not ip_address:
                    continue
                
                processed_ips.add(ip_address)
                
                if ping_success:
                    # Ping successful - remove from timeout tracking if exists

                    if ip_address in timeout_data:
                        # Log recovery
                        consecutive_timeouts = int(timeout_data[ip_address].get('consecutive_timeouts', 0))
                        hostname = timeout_data[ip_address].get('hostname', ip_address)
                        logger.info(f"Device {hostname} ({ip_address}) recovered after {consecutive_timeouts} consecutive timeouts")
                        
                        del timeout_data[ip_address]

                        if ip_address in alerted_data:
                            del alerted_data[ip_address]
                            logger.info(f"Removed {ip_address} from whatsapp_alerted_list.csv (device recovered)")
                        
                        logger.debug(f"Removed {ip_address} from timeout tracking (ping successful)")
                else:
                    # Ping failed - add or update timeout tracking
                    if ip_address in timeout_data:
                        # Update existing entry
                        current_count = int(timeout_data[ip_address].get('consecutive_timeouts', 0))
                        new_count = current_count + 1
                        
                        timeout_data[ip_address]['consecutive_timeouts'] = str(new_count)
                        timeout_data[ip_address]['last_timeout'] = current_time
                        timeout_data[ip_address]['last_updated'] = current_time
                        
                        # Check if WhatsApp alert should be sent
                        if self._should_send_whatsapp_alert(ip_address, new_count):
                            if self._send_whatsapp_timeout_alert(timeout_data[ip_address]):
                                whatsapp_alerts_sent.append({
                                    'ip_address': ip_address,
                                    'hostname': timeout_data[ip_address].get('hostname', ''),
                                    'consecutive_timeouts': new_count
                                })
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
            
            # Remove entries for IPs that are no longer being monitored
            stale_ips = set(timeout_data.keys()) - processed_ips
            for stale_ip in stale_ips:
                del timeout_data[stale_ip]
                logger.debug(f"Removed stale IP {stale_ip} from timeout tracking")
            
            # --- START: Remove devices from alerted_list if not in timeout_data ---
            timeout_ips_set = set(timeout_data.keys())
            alerted_ips_to_remove = [ip for ip in alerted_data if ip not in timeout_ips_set]
            for ip in alerted_ips_to_remove:
                del alerted_data[ip]
                logger.info(f"Removed {ip} from whatsapp_alerted_list.csv (no longer timeout)")
            # Write updated alerted_data back to CSV
            with open(self.alerted_list_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=self.alerted_list_headers)
                writer.writeheader()
                for row in alerted_data.values():
                    writer.writerow(row)
            # --- END: Remove devices from alerted_list if not in timeout_data ---
            
            # Write updated data back to CSV
            self._write_timeout_data(timeout_data)
            
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
            if total_timeout_devices > 0:
                max_timeouts = max(int(entry['consecutive_timeouts']) for entry in timeout_data.values())
                logger.info(f"Timeout tracking updated: {total_timeout_devices} devices with timeouts, max consecutive: {max_timeouts}")
                
                # Log WhatsApp alerts sent
                if whatsapp_alerts_sent:
                    for alert in whatsapp_alerts_sent:
                        logger.warning(f"🚨 WhatsApp TIMEOUT ALERT sent: {alert['hostname']} ({alert['ip_address']}) - {alert['consecutive_timeouts']} consecutive timeouts")
            else:
                logger.info("Timeout tracking updated: No devices currently timing out")
                
        except Exception as e:
            logger.error(f"Error updating timeout tracking: {e}")
    
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
