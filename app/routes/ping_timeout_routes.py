from flask import Blueprint, jsonify, request
from app.utils.multi_ping_service import get_multi_ping_service
from datetime import datetime
from flask_cors import cross_origin

ping_timeout_bp = Blueprint('ping_timeout', __name__)

@ping_timeout_bp.route('/ping/timeout/summary', methods=['GET'])
@cross_origin()
def get_timeout_summary():
    """
    Get timeout tracking summary
    """
    try:
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
        
        summary = service.get_timeout_summary()
        
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_timeout_bp.route('/ping/timeout/devices', methods=['GET'])
@cross_origin()
def get_timeout_devices():
    """
    Get devices with consecutive timeouts
    Query parameters:
    - min_consecutive: minimum consecutive timeouts (default: 1)
    """
    try:
        min_consecutive = request.args.get('min_consecutive', 1, type=int)
        
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
        
        timeout_devices = service.get_timeout_devices(min_consecutive)
        
        return jsonify({
            'success': True,
            'data': timeout_devices,
            'count': len(timeout_devices),
            'min_consecutive_filter': min_consecutive
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_timeout_bp.route('/ping/timeout/critical', methods=['GET'])
@cross_origin()
def get_critical_timeouts():
    """
    Get devices with critical timeout counts
    Query parameters:
    - threshold: critical timeout threshold (default: from config)
    """
    try:
        threshold = request.args.get('threshold', type=int)
        
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
        
        critical_devices = service.get_critical_timeouts(threshold)
        
        return jsonify({
            'success': True,
            'data': critical_devices,
            'count': len(critical_devices),
            'threshold': threshold or getattr(service.config, 'TIMEOUT_CRITICAL_THRESHOLD', 5)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_timeout_bp.route('/ping/timeout/report', methods=['GET'])
@cross_origin()
def get_timeout_report():
    """
    Get comprehensive timeout tracking report
    """
    try:
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
        
        if not service.timeout_tracker:
            return jsonify({
                'success': False,
                'error': 'Timeout tracking is disabled'
            }), 503
        
        report = service.timeout_tracker.export_timeout_report()
        
        return jsonify({
            'success': True,
            'data': report
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_timeout_bp.route('/ping/timeout/reset', methods=['POST'])
@cross_origin()
def reset_timeout_tracking():
    """
    Reset timeout tracking (clear CSV)
    """
    try:
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
        
        if not service.timeout_tracker:
            return jsonify({
                'success': False,
                'error': 'Timeout tracking is disabled'
            }), 503
        
        service.timeout_tracker.cleanup_timeout_csv()
        
        return jsonify({
            'success': True,
            'message': 'Timeout tracking reset successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_timeout_bp.route('/ping/timeout/whatsapp/summary', methods=['GET'])
def get_whatsapp_timeout_summary():
    """
    Get WhatsApp timeout alert summary
    """
    try:
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
        
        if not service.timeout_tracker:
            return jsonify({
                'success': False,
                'error': 'Timeout tracking is disabled'
            }), 503
        
        summary = service.timeout_tracker.get_whatsapp_alert_summary()
        
        return jsonify({
            'success': True,
            'data': summary
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ping_timeout_bp.route('/ping/timeout/whatsapp/test', methods=['POST'])
def test_whatsapp_timeout_alert():
    """
    Test WhatsApp timeout alert for a specific IP
    Query parameters:
    - ip_address: IP address to test alert for
    """
    try:
        ip_address = request.args.get('ip_address')
        if not ip_address:
            return jsonify({
                'success': False,
                'error': 'Missing ip_address parameter'
            }), 400
        
        service = get_multi_ping_service()
        if not service:
            return jsonify({
                'success': False,
                'error': 'Multi-ping service not available'
            }), 503
        
        if not service.timeout_tracker:
            return jsonify({
                'success': False,
                'error': 'Timeout tracking is disabled'
            }), 503
        
        # Create test device data
        test_device_data = {
            'ip_address': ip_address,
            'hostname': f'TEST-{ip_address}',
            'device_id': '999',
            'merk': 'Test Device',
            'os': 'Test OS',
            'kondisi': 'baik',
            'consecutive_timeouts': '20',
            'first_timeout': datetime.now().isoformat(),
            'last_timeout': datetime.now().isoformat()
        }
        
        # Send test alert
        result = service.timeout_tracker._send_whatsapp_timeout_alert(test_device_data)
        
        return jsonify({
            'success': result,
            'message': 'Test WhatsApp timeout alert sent successfully' if result else 'Failed to send test alert',
            'test_data': test_device_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
