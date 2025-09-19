import os
import csv
import logging
from datetime import datetime
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
        
        # Ensure directory exists
        os.makedirs(self.timeout_dir, exist_ok=True)
        
        # CSV headers for timeout tracking
        self.timeout_headers = [
            'ip_address', 'hostname', 'device_id', 'merk', 'os', 'kondisi',
            'consecutive_timeouts', 'first_timeout', 'last_timeout', 'last_updated'
        ]
        
        # Initialize CSV file if not exists
        self._initialize_timeout_csv()
        
        logger.info(f"TimeoutTracker initialized - CSV: {self.timeout_csv_path}")
    
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
    
    def update_timeout_tracking(self, ping_results: List[Dict]):
        """
        Update timeout tracking based on ping results
        Args:
            ping_results: List of ping results from current cycle
        """
        try:
            # Read existing timeout data
            timeout_data = self._read_timeout_data()
            current_time = datetime.now().isoformat()
            
            processed_ips = set()
            
            for result in ping_results:
                ip_address = result.get('ip_address')
                ping_success = result.get('ping_success', False)
                
                if not ip_address:
                    continue
                
                processed_ips.add(ip_address)
                
                if ping_success:
                    # Ping successful - remove from timeout tracking if exists
                    if ip_address in timeout_data:
                        del timeout_data[ip_address]
                        logger.debug(f"Removed {ip_address} from timeout tracking (ping successful)")
                else:
                    # Ping failed - add or update timeout tracking
                    if ip_address in timeout_data:
                        # Update existing entry
                        current_count = int(timeout_data[ip_address].get('consecutive_timeouts', 0))
                        timeout_data[ip_address]['consecutive_timeouts'] = str(current_count + 1)
                        timeout_data[ip_address]['last_timeout'] = current_time
                        timeout_data[ip_address]['last_updated'] = current_time
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
                            'last_updated': current_time
                        }
                        logger.debug(f"Added {ip_address} to timeout tracking (first timeout)")
            
            # Remove entries for IPs that are no longer being monitored
            # (This handles cases where devices are removed from inventory)
            stale_ips = set(timeout_data.keys()) - processed_ips
            for stale_ip in stale_ips:
                del timeout_data[stale_ip]
                logger.debug(f"Removed stale IP {stale_ip} from timeout tracking")
            
            # Write updated data back to CSV
            self._write_timeout_data(timeout_data)
            
            # Log summary
            total_timeout_devices = len(timeout_data)
            if total_timeout_devices > 0:
                max_timeouts = max(int(entry['consecutive_timeouts']) for entry in timeout_data.values())
                logger.info(f"Timeout tracking updated: {total_timeout_devices} devices with timeouts, max consecutive: {max_timeouts}")
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
