from flask import Blueprint, jsonify, request  # type: ignore
from app.utils.multi_ping_service import get_multi_ping_service
from config import Config

ping_bp = Blueprint('ping', __name__)

@ping_bp.route('/ping/latest', methods=['GET'])
def get_latest_ping_results():
    """
    Get latest ping results from CSV
    Query parameters:
    - limit: number of results to return (default: 100)
    """
    try:
        limit = request.args.get('limit', 100, type=int)
        limit = min(limit, 1000)  # Cap at 1000 for performance
        
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
            
        results = service.get_latest_ping_results_from_csv(limit=limit)
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_bp.route('/ping/device/<int:device_id>', methods=['GET'])
def get_device_ping_results(device_id):
    """
    Get ping results for a specific device from CSV
    Query parameters:
    - hours: time range in hours (default: 24) - Not applicable for CSV update method
    """
    try:
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
            
        # Get all results and filter by device_id
        all_results = service.get_latest_ping_results_from_csv()
        results = [r for r in all_results if str(r.get('device_id')) == str(device_id)]
        
        return jsonify({
            'success': True,
            'device_id': device_id,
            'data': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_bp.route('/ping/statistics', methods=['GET'])
def get_ping_statistics():
    """
    Get ping statistics from current CSV data
    Query parameters:
    - device_id: specific device ID (optional)
    """
    try:
        device_id = request.args.get('device_id', type=int)
        
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
            
        # Get all results from CSV
        all_results = service.get_latest_ping_results_from_csv()
        
        # Filter by device_id if specified
        if device_id:
            all_results = [r for r in all_results if str(r.get('device_id')) == str(device_id)]
        
        # Calculate basic statistics
        total_devices = len(all_results)
        successful_pings = sum(1 for r in all_results if r.get('ping_success') == 'True')
        failed_pings = total_devices - successful_pings
        success_rate = round((successful_pings / total_devices) * 100, 2) if total_devices > 0 else 0
        
        # Get response times for successful pings
        response_times = []
        for r in all_results:
            if r.get('ping_success') == 'True' and r.get('response_time_ms'):
                try:
                    response_times.append(float(r['response_time_ms']))
                except (ValueError, TypeError):
                    continue
        
        stats = {
            'total_devices': total_devices,
            'successful_pings': successful_pings,
            'failed_pings': failed_pings,
            'success_rate': success_rate,
            'average_response_time_ms': round(sum(response_times) / len(response_times), 2) if response_times else None,
            'min_response_time_ms': min(response_times) if response_times else None,
            'max_response_time_ms': max(response_times) if response_times else None
        }
        
        return jsonify({
            'success': True,
            'device_id': device_id,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_bp.route('/ping/status', methods=['GET'])
def get_device_status_summary():
    """
    Get current status summary for all devices from CSV
    """
    try:
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
            
        # Get all results from CSV
        all_results = service.get_latest_ping_results_from_csv()
        
        # Calculate summary statistics
        total_devices = len(all_results)
        online_devices = sum(1 for r in all_results if r.get('ping_success') == 'True')
        offline_devices = total_devices - online_devices
        
        # Group by device status for detailed breakdown
        status_breakdown = {
            'online': online_devices,
            'offline': offline_devices,
            'total': total_devices
        }
        
        # Get recent results (assuming CSV is updated regularly)
        summary = {
            'status_breakdown': status_breakdown,
            'last_updated': all_results[0].get('timestamp') if all_results else None,
            'devices': all_results
        }
        
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_bp.route('/ping/service/status', methods=['GET'])
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

@ping_bp.route('/ping/service/start', methods=['POST'])
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

@ping_bp.route('/ping/service/stop', methods=['POST'])
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

@ping_bp.route('/ping/test/<string:ip_address>', methods=['POST'])
def test_ping_device():
    """
    Test ping to a specific IP address
    """
    try:
        config = Config()
        service = get_multi_ping_service(config)
        
        if not service:
            return jsonify({
                'success': False,
                'error': 'Ping service not available'
            }), 500
        
        ip_address = request.view_args['ip_address']
        
        # Create a mock device object for testing
        from app.models.inventaris import Inventaris
        mock_device = Inventaris()
        mock_device.id = 0
        mock_device.ip = ip_address
        mock_device.hostname = f"test-{ip_address}"
        mock_device.merk = "Test"
        mock_device.os = "Unknown"
        mock_device.kondisi = "baik"
        mock_device.id_lokasi = 0
        
        result_dict = service.ping_single_device(mock_device)
        result = {
            'success': result_dict['ping_success'],
            'response_time_ms': result_dict['response_time_ms'],
            'error_message': result_dict['error_message']
        }
        
        return jsonify({
            'success': True,
            'ip_address': ip_address,
            'ping_result': result,
            'service_type': 'Multi-Ping'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Health check endpoint
@ping_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'success': True,
        'status': 'healthy',
        'service': 'ping-monitoring-api'
    })

@ping_bp.route('/ping/csv/files', methods=['GET'])
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

@ping_bp.route('/ping/database/monitoring', methods=['GET'])
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

@ping_bp.route('/ping/database/reload', methods=['POST'])
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

@ping_bp.route('/ping/csv/rebuild', methods=['POST'])
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

@ping_bp.route('/ping/summary/offline', methods=['GET'])
def get_offline_summary():
    """
    Get a summary of offline devices.
    Provides total, online, and offline counts, and a list of offline devices.
    """
    try:
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503

        # Get all results from the most recent CSV data
        all_results = service.get_latest_ping_results_from_csv()

        if not all_results:
            return jsonify({
                'success': True,
                'data': {
                    'total_devices': 0,
                    'online_devices': 0,
                    'offline_devices': 0,
                    'offline_device_list': []
                },
                'message': 'No ping data available yet.'
            })

        # Calculate summary statistics
        total_devices = len(all_results)
        offline_device_list = [
            device for device in all_results if device.get('ping_success') == 'False'
        ]
        offline_devices_count = len(offline_device_list)
        online_devices_count = total_devices - offline_devices_count

        summary = {
            'total_devices': total_devices,
            'online_devices': online_devices_count,
            'offline_devices': offline_devices_count,
            'offline_device_list': offline_device_list
        }

        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500