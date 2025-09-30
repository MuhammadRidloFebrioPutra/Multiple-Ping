from flask import Blueprint, jsonify, request
from app.utils.multi_ping_service import get_multi_ping_service
from config import Config
from flask_cors import cross_origin

ping_basic_bp = Blueprint('ping_basic', __name__)

@ping_basic_bp.route('/ping/latest', methods=['GET'])
@cross_origin()
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

@ping_basic_bp.route('/ping/device/<int:device_id>', methods=['GET'])
@cross_origin()
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

@ping_basic_bp.route('/ping/statistics', methods=['GET'])
@cross_origin()
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

@ping_basic_bp.route('/ping/status', methods=['GET'])
@cross_origin()
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

@ping_basic_bp.route('/ping/summary/offline', methods=['GET'])
@cross_origin()
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

@ping_basic_bp.route('/ping/test/<string:ip_address>', methods=['POST'])
@cross_origin()
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
@ping_basic_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'success': True,
        'status': 'healthy',
        'service': 'ping-monitoring-api'
    })
