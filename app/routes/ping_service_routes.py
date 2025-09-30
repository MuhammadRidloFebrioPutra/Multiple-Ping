from flask import Blueprint, jsonify, request
from app.utils.multi_ping_service import get_multi_ping_service
from config import Config
from flask_cors import cross_origin

ping_service_bp = Blueprint('ping_service', __name__)

@ping_service_bp.route('/ping/service/status', methods=['GET'])
@cross_origin()
def get_service_status():
    """
    Get ping monitoring service status
    """
    try:
        config = Config()
        service = get_multi_ping_service()
        
        device_count = service.get_device_count() if service else 0
        db_monitoring = service.get_database_monitoring_status() if service else {'monitoring_enabled': False}
        
        return jsonify({
            'success': True,
            'service_type': "Multi-Ping Service",
            'service_running': service.running if service else False,
            'ping_interval_seconds': config.PING_INTERVAL,
            'csv_output_directory': config.CSV_OUTPUT_DIR,
            'active_devices_count': device_count,
            'max_workers': config.MAX_PING_WORKERS,
            'ping_timeout_seconds': config.PING_TIMEOUT,
            'database_monitoring': db_monitoring
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_service_bp.route('/ping/service/start', methods=['POST'])
@cross_origin()
def start_ping_service():
    """
    Start the ping monitoring service
    """
    try:
        config = Config()
        service = get_multi_ping_service(config)
        
        if service:
            service.start()
            return jsonify({
                'success': True,
                'message': 'Multi-Ping Service started',
                'service_type': "Multi-Ping Service"
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to initialize ping service'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_service_bp.route('/ping/service/stop', methods=['POST'])
@cross_origin()
def stop_ping_service():
    """
    Stop the ping monitoring service
    """
    try:
        service = get_multi_ping_service()
        
        if service:
            service.stop()
            return jsonify({
                'success': True,
                'message': 'Multi-Ping Service stopped',
                'service_type': "Multi-Ping Service"
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Ping service not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_service_bp.route('/ping/csv/files', methods=['GET'])
@cross_origin()
def get_csv_files():
    """
    Get list of available CSV files
    """
    try:
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
            
        csv_files = service.get_available_csv_files()
        
        return jsonify({
            'success': True,
            'data': csv_files,
            'count': len(csv_files)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_service_bp.route('/ping/csv/rebuild', methods=['POST'])
@cross_origin()
def rebuild_today_csv():
    """
    Rebuild today's CSV file from current active devices (reuse existing cache to prevent double ping)
    """
    try:
        service = get_multi_ping_service()
        if not service:
            return jsonify({'success': False, 'error': 'Multi-ping service not available'}), 503

        # Check if service is already running to avoid conflicts
        if service._ping_in_progress:
            return jsonify({
                'success': False, 
                'error': 'Ping cycle already in progress, please wait and try again'
            }), 409

        # Use existing cached devices first, then reload if needed
        devices = service.database_monitor.get_devices_from_database()
        if not devices:
            # Force reload if no devices cached
            service.database_monitor.reload_device_list()
            devices = service.database_monitor.get_devices_from_database()
            
        if not devices:
            return jsonify({'success': False, 'error': 'No active devices found'}), 404

        # Force one ping cycle (this will check for duplicates internally)
        service.perform_ping_cycle(force=True)

        return jsonify({
            'success': True,
            'message': 'CSV rebuild initiated successfully from cached database state',
            'device_count': len(devices),
            'note': 'Duplicate ping prevention active'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@ping_service_bp.route('/ping/database/monitoring', methods=['GET'])
@cross_origin()
def get_database_monitoring_status():
    """
    Get database monitoring status and statistics
    """
    try:
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
            
        status = service.get_database_monitoring_status()
        
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_service_bp.route('/ping/database/reload', methods=['POST'])
@cross_origin()
def force_database_reload():
    """
    Force reload device list from database
    """
    try:
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
            
        result = service.force_device_reload()
        
        return jsonify({
            'success': result['success'],
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
