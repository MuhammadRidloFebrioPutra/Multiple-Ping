import threading
import time
import logging
import pymysql
from datetime import datetime
from typing import List, Dict, Optional
from config import Config
from app.models.inventaris import Inventaris
from app.utils.database_monitor import DatabaseMonitor
from app.utils.csv_manager import CSVManager
from app.utils.ping_executor import PingExecutor

# Enable PyMySQL compatibility with MySQLdb
pymysql.install_as_MySQLdb()

logger = logging.getLogger(__name__)

class MultiPingService:
    """
    Main orchestrator service untuk multi-device ping monitoring
    Menggunakan modular components untuk database monitoring, CSV management, dan ping execution
    """
    
    def __init__(self, config: Config):
        self.config = config
        self.running = False
        self.thread = None
        
        # Initialize modular components
        self.database_monitor = DatabaseMonitor(config)
        self.csv_manager = CSVManager(config)
        self.ping_executor = PingExecutor(config)
        
        logger.info("Multi-ping service initialized with modular components")
        logger.info(f"Database monitoring: Every {self.database_monitor.device_check_interval}s")
        logger.info(f"Ping execution: {self.ping_executor.max_workers} workers, {self.ping_executor.ping_timeout}s timeout")
        logger.info(f"CSV output: {self.csv_manager.csv_dir}")
    
    def ping_single_device(self, device: Inventaris) -> Dict:
        """
        Ping a single device (delegate to ping executor)
        """
        return self.ping_executor.ping_single_device(device)
    
    def perform_ping_cycle(self):
        """
        Perform one complete ping cycle for all devices using concurrent execution
        """
        try:
            # Get devices from database
            devices = self.database_monitor.get_devices_from_database()
            
            if not devices:
                logger.warning("No active devices found in database")
                return
            
            logger.info(f"Starting ping cycle for {len(devices)} devices")
            cycle_start = time.time()
            
            # Execute concurrent pings
            results = self.ping_executor.ping_devices_concurrent(devices)
            active_ips = [d.ip for d in devices if d.ip]
            
            if results:
                # Calculate and log statistics
                stats = self.ping_executor.get_ping_statistics(results)
                logger.info(f"Ping cycle completed - Success: {stats['successful_pings']}/{stats['total_devices']} "
                           f"({stats['success_rate']}%), "
                           f"Avg response: {stats['average_response_time_ms']}ms")
                
                # Write results to CSV with pruning using current active IPs
                self.csv_manager.write_ping_results_to_csv(results, active_ips=active_ips)
                
                cycle_duration = time.time() - cycle_start
                logger.debug(f"Complete ping cycle duration: {cycle_duration:.2f}s")
            else:
                logger.error("No ping results obtained")
                
        except Exception as e:
            logger.error(f"Error in ping cycle: {e}")
    
    def _monitoring_loop(self):
        """
        Main monitoring loop that runs in background thread
        """
        logger.info(f"Starting multi-ping monitoring service with {self.config.PING_INTERVAL}s interval")
        logger.info(f"Configuration: {self.ping_executor.max_workers} max workers, {self.ping_executor.ping_timeout}s timeout")
        logger.info(f"Database change monitoring: Check every {self.database_monitor.device_check_interval}s")
        
        # Initialize device cache pada startup
        self.database_monitor.initialize_cache()
        
        while self.running:
            try:
                start_time = time.time()
                
                # Check untuk database changes
                if self.database_monitor.check_database_changes():
                    logger.info("Database changes detected, reloading device list...")
                    device_count = self.database_monitor.reload_device_list()
                    logger.info(f"Successfully reloaded {device_count} devices from database")
                
                # Perform ping cycle
                self.perform_ping_cycle()
                
                # Calculate how long the cycle took
                cycle_duration = time.time() - start_time
                
                # Sleep for the remaining time to maintain interval
                sleep_time = max(0, self.config.PING_INTERVAL - cycle_duration)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    logger.warning(f"Ping cycle took {cycle_duration:.2f}s, longer than interval {self.config.PING_INTERVAL}s")
                    logger.warning("Consider increasing PING_INTERVAL or reducing MAX_PING_WORKERS")
                    
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(self.config.PING_INTERVAL)
    
    def start(self):
        """
        Start the ping monitoring service in background thread
        """
        if self.running:
            logger.warning("Multi-ping monitoring service is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        logger.info("Multi-ping monitoring service started")
    
    def stop(self):
        """
        Stop the ping monitoring service
        """
        if not self.running:
            logger.warning("Multi-ping monitoring service is not running")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=10)
        
        logger.info("Multi-ping monitoring service stopped")
    
    # Delegate methods to appropriate components
    
    def get_device_count(self) -> int:
        """
        Get total number of active devices (delegate to database monitor)
        """
        return self.database_monitor.get_device_count()
    
    def get_latest_ping_results_from_csv(self, limit: int = None) -> List[Dict]:
        """
        Get latest ping results from CSV (delegate to CSV manager)
        """
        return self.csv_manager.get_latest_ping_results_from_csv(limit)
    
    def get_available_csv_files(self) -> List[Dict]:
        """
        Get available CSV files (delegate to CSV manager)
        """
        return self.csv_manager.get_available_csv_files()
    
    def get_database_monitoring_status(self) -> Dict:
        """
        Get database monitoring status (delegate to database monitor)
        """
        return self.database_monitor.get_monitoring_status()
    
    def force_device_reload(self) -> Dict:
        """
        Force device reload (delegate to database monitor)
        """
        return self.database_monitor.force_device_reload()
    
    def get_ping_statistics(self, results: List[Dict]) -> Dict:
        """
        Get ping statistics (delegate to ping executor)
        """
        return self.ping_executor.get_ping_statistics(results)
    
    def get_service_status(self) -> Dict:
        """
        Get comprehensive service status
        """
        try:
            return {
                'service_running': self.running,
                'service_type': 'Multi-Ping Service (Modular)',
                'ping_interval_seconds': self.config.PING_INTERVAL,
                'components': {
                    'database_monitor': self.database_monitor.get_monitoring_status(),
                    'csv_manager': self.csv_manager.get_csv_statistics(),
                    'ping_executor': self.ping_executor.get_executor_status()
                },
                'device_count': self.get_device_count(),
                'csv_output_directory': self.csv_manager.csv_dir
            }
        except Exception as e:
            logger.error(f"Error getting service status: {e}")
            return {
                'service_running': self.running,
                'error': str(e)
            }
    
    def cleanup_resources(self):
        """
        Cleanup all resources
        """
        try:
            # Stop service if running
            if self.running:
                self.stop()
            
            # Cleanup CSV files if needed
            self.csv_manager.cleanup_old_csv_files()
            
            logger.info("Multi-ping service resources cleaned up")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def __del__(self):
        """
        Destructor - cleanup resources
        """
        self.cleanup_resources()

# Global instance
multi_ping_service = None

def get_multi_ping_service(config: Config = None) -> MultiPingService:
    """
    Get singleton instance of multi-ping service
    """
    global multi_ping_service
    if multi_ping_service is None and config:
        multi_ping_service = MultiPingService(config)
    return multi_ping_service