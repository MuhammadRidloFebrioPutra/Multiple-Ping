import time
import ping3  # type: ignore
import logging
import subprocess
import platform
from datetime import datetime
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.models.inventaris import Inventaris

logger = logging.getLogger(__name__)

class PingExecutor:
    """
    Class untuk menangani operasi ping dan statistik
    """
    
    def __init__(self, config):
        self.config = config
        
        # Threading configuration
        self.max_workers = getattr(config, 'MAX_PING_WORKERS', 20)  # Max concurrent pings
        self.ping_timeout = getattr(config, 'PING_TIMEOUT', 3)  # Ping timeout in seconds
        
        # Platform detection for fallback mechanism
        self.is_linux = platform.system().lower() == 'linux'
        self.use_fallback = getattr(config, 'USE_SYSTEM_PING_FALLBACK', True)
        
        if self.is_linux:
            logger.info("Running on Linux - system ping fallback enabled for reliability")
    
    def _ping_via_system(self, ip: str) -> Dict:
        """
        Fallback: Use system ping command (reliable on Linux/CentOS)
        """
        try:
            # Linux ping command: -c 1 (count), -W timeout (wait)
            cmd = ['ping', '-c', '1', '-W', str(int(self.ping_timeout)), ip]
            
            start = time.time()
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.ping_timeout + 1,
                universal_newlines=True
            )
            elapsed = time.time() - start
            
            if result.returncode == 0:
                # Parse time from output: "time=X.XX ms"
                output = result.stdout
                try:
                    for line in output.split('\n'):
                        if 'time=' in line:
                            time_str = line.split('time=')[1].split()[0]
                            response_ms = float(time_str)
                            return {
                                'success': True,
                                'response_time_ms': round(response_ms, 2),
                                'latency_ms': round(response_ms, 2),
                                'error_message': None,
                                'method': 'system_ping'
                            }
                except:
                    pass
                # Fallback jika parsing gagal tapi ping sukses
                return {
                    'success': True,
                    'response_time_ms': round(elapsed * 1000, 2),
                    'latency_ms': round(elapsed * 1000, 2),
                    'error_message': None,
                    'method': 'system_ping'
                }
            else:
                # Ping failed
                error = result.stderr or 'No response'
                return {
                    'success': False,
                    'response_time_ms': None,
                    'latency_ms': None,
                    'error_message': f'System ping failed: {error.strip()[:100]}',
                    'method': 'system_ping'
                }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'response_time_ms': None,
                'latency_ms': None,
                'error_message': 'System ping timeout',
                'method': 'system_ping'
            }
        except Exception as e:
            return {
                'success': False,
                'response_time_ms': None,
                'latency_ms': None,
                'error_message': f'System ping error: {str(e)}',
                'method': 'system_ping'
            }
    
    def ping_single_device(self, device: Inventaris) -> Dict:
        """
        Ping a single device and return comprehensive result
        """
        start_time = time.time()
        
        # Try ping3 first
        ping3_result = None
        try:
            # Using ping3 library for cross-platform ping
            response_time = ping3.ping(device.ip, timeout=self.ping_timeout)
            
            # CRITICAL FIX: ping3 returns False for "Destination host unreachable"
            # We MUST check if response_time is a number (float), not just "not None"
            if response_time is not None and response_time is not False and isinstance(response_time, (int, float)):
                ping3_result = {
                    'success': True,
                    'response_time_ms': round(response_time * 1000, 2),
                    'latency_ms': round(response_time * 1000, 2),
                    'error_message': None,
                    'method': 'ping3'
                }
            elif response_time is False:
                # False means "Destination host unreachable"
                ping3_result = {
                    'success': False,
                    'response_time_ms': None,
                    'latency_ms': None,
                    'error_message': 'Destination host unreachable (ping3)',
                    'method': 'ping3'
                }
            else:
                # None means timeout
                ping3_result = {
                    'success': False,
                    'response_time_ms': None,
                    'latency_ms': None,
                    'error_message': 'No response - timeout (ping3)',
                    'method': 'ping3'
                }
                
        except Exception as e:
            ping3_result = {
                'success': False,
                'response_time_ms': None,
                'latency_ms': None,
                'error_message': f"Ping3 error: {str(e)}",
                'method': 'ping3'
            }
        
        # FALLBACK: Jika ping3 gagal DI LINUX dan fallback diaktifkan, coba system ping
        result = ping3_result
        if self.is_linux and self.use_fallback and not ping3_result['success']:
            # Coba verifikasi dengan system ping
            system_result = self._ping_via_system(device.ip)
            
            # Jika system ping berhasil tapi ping3 gagal = false positive dari ping3
            if system_result['success']:
                logger.warning(f"⚠️ FALSE POSITIVE terdeteksi untuk {device.ip}: ping3 gagal tapi system ping sukses")
                logger.warning(f"   ping3: {ping3_result['error_message']}")
                logger.warning(f"   system: {system_result['response_time_ms']}ms")
                result = system_result  # Gunakan hasil system ping
            else:
                # Kedua method gagal - benar-benar timeout
                result = ping3_result
        
        # Calculate total processing time
        processing_time = time.time() - start_time
        
        # Create comprehensive result dictionary
        ping_result = {
            'timestamp': datetime.now().isoformat(),
            'device_id': device.id,
            'ip_address': device.ip,
            'hostname': device.hostname or device.ip,
            'ping_success': result['success'],
            'response_time_ms': result['response_time_ms'],
            'latency_ms': result['latency_ms'],
            'error_message': result['error_message'],
            'ping_method': result.get('method', 'ping3'),
            'merk': device.merk,
            'os': device.os,
            'kondisi': device.kondisi,
            'id_lokasi': device.id_lokasi,
            'processing_time_ms': round(processing_time * 1000, 2)
        }
        
        return ping_result
    
    def ping_devices_concurrent(self, devices: List[Inventaris]) -> List[Dict]:
        """
        Ping multiple devices concurrently using ThreadPoolExecutor
        """
        if not devices:
            logger.warning("No devices to ping")
            return []
        
        start_time = time.time()
        results = []
        
        logger.info(f"Starting concurrent ping for {len(devices)} devices with {self.max_workers} workers")
        
        try:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all ping tasks
                future_to_device = {
                    executor.submit(self.ping_single_device, device): device 
                    for device in devices
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_device):
                    device = future_to_device[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        # Create error result for failed ping
                        error_result = {
                            'timestamp': datetime.now().isoformat(),
                            'device_id': device.id,
                            'ip_address': device.ip,
                            'hostname': device.hostname or device.ip,
                            'ping_success': False,
                            'response_time_ms': None,
                            'latency_ms': None,
                            'error_message': f"Ping execution error: {str(e)}",
                            'merk': device.merk,
                            'os': device.os,
                            'kondisi': device.kondisi,
                            'id_lokasi': device.id_lokasi,
                            'processing_time_ms': 0
                        }
                        results.append(error_result)
                        logger.error(f"Error pinging device {device.ip}: {e}")
            
            total_time = time.time() - start_time
            logger.info(f"Completed concurrent ping in {total_time:.2f}s for {len(results)} devices")
            
            return results
            
        except Exception as e:
            logger.error(f"Error in concurrent ping execution: {e}")
            return []
    
    def get_ping_statistics(self, results: List[Dict]) -> Dict:
        """
        Calculate statistics for current ping cycle
        """
        if not results:
            return {}
        
        successful_pings = [r for r in results if r['ping_success']]
        failed_pings = [r for r in results if not r['ping_success']]
        response_times = [r['response_time_ms'] for r in successful_pings if r['response_time_ms'] is not None]
        processing_times = [r['processing_time_ms'] for r in results if r.get('processing_time_ms') is not None]
        
        stats = {
            'total_devices': len(results),
            'successful_pings': len(successful_pings),
            'failed_pings': len(failed_pings),
            'success_rate': round((len(successful_pings) / len(results)) * 100, 2),
            'average_response_time_ms': round(sum(response_times) / len(response_times), 2) if response_times else None,
            'min_response_time_ms': min(response_times) if response_times else None,
            'max_response_time_ms': max(response_times) if response_times else None,
            'average_processing_time_ms': round(sum(processing_times) / len(processing_times), 2) if processing_times else None,
            'cycle_duration_ms': max(processing_times) if processing_times else None
        }
        
        return stats
    
    def ping_single_ip(self, ip_address: str) -> Dict:
        """
        Ping a single IP address (for testing purposes)
        """
        start_time = time.time()
        
        try:
            response_time = ping3.ping(ip_address, timeout=self.ping_timeout)
            
            # CRITICAL FIX: ping3 returns False for "Destination host unreachable"
            # We MUST check if response_time is a number (float), not just "not None"
            if response_time is not None and response_time is not False and isinstance(response_time, (int, float)):
                result = {
                    'success': True,
                    'response_time_ms': round(response_time * 1000, 2),
                    'latency_ms': round(response_time * 1000, 2),
                    'error_message': None
                }
            elif response_time is False:
                # False means "Destination host unreachable"
                result = {
                    'success': False,
                    'response_time_ms': None,
                    'latency_ms': None,
                    'error_message': 'Destination host unreachable'
                }
            else:
                # None means timeout
                result = {
                    'success': False,
                    'response_time_ms': None,
                    'latency_ms': None,
                    'error_message': 'No response (timeout)'
                }
                
        except Exception as e:
            result = {
                'success': False,
                'response_time_ms': None,
                'latency_ms': None,
                'error_message': f"Ping error: {str(e)}"
            }
        
        processing_time = time.time() - start_time
        
        return {
            'timestamp': datetime.now().isoformat(),
            'ip_address': ip_address,
            'ping_success': result['success'],
            'response_time_ms': result['response_time_ms'],
            'latency_ms': result['latency_ms'],
            'error_message': result['error_message'],
            'processing_time_ms': round(processing_time * 1000, 2)
        }
    
    def validate_ping_configuration(self) -> Dict:
        """
        Validate current ping configuration
        """
        return {
            'max_workers': self.max_workers,
            'ping_timeout_seconds': self.ping_timeout,
            'configuration_valid': self.max_workers > 0 and self.ping_timeout > 0,
            'recommended_max_workers': min(50, max(10, self.max_workers)),
            'recommended_timeout': max(1, min(10, self.ping_timeout))
        }
    
    def get_executor_status(self) -> Dict:
        """
        Get current executor status and configuration
        """
        return {
            'max_workers': self.max_workers,
            'ping_timeout_seconds': self.ping_timeout,
            'ping_library': 'ping3',
            'concurrent_execution': True,
            'cross_platform': True
        }